# ============================================================
# src/core/game_manager.py — Gerenciador central do jogo
# ============================================================

import json
import os
import random
import time
from datetime import datetime

from src.core.slave import Escravo
from src.core.constants import (
    RESOURCES, RESOURCE_ORDER, MINE_UPGRADES, UPGRADE_ORDER,
    MINE_DEPTHS, RANDOM_EVENTS, ACHIEVEMENTS,
    PRESTIGE_GOLD_REQ, PRESTIGE_BONUS_STEP,
    MINING_INTERVAL, BREEDING_INTERVAL, GROWTH_TIME,
    AUTOSAVE_INTERVAL, EVENT_INTERVAL, SHOP_REFRESH_TIME,
    GREEN, RED, YELLOW, ORANGE, CYAN, GOLD, GRAY, PURPLE, WHITE,
)
from src.db.database import Database


class GameManager:
    """
    Coordena toda a lógica do jogo:
    escravos, mineração, breeding, upgrades, eventos,
    prestígio, conquistas e persistência via SQLite.
    """

    def __init__(self, db_path: str = "data/eternal_mine.db"):
        # Banco de dados (persiste entre prestígios)
        self.db = Database(db_path)

        # Batch de mineração: flushed no save
        self._mining_batch: list[tuple] = []

        # Sessão atual
        self._sessao_id    = -1
        self._sessao_inicio = time.time()

        self._init_state()

    # ==============================================================
    # INICIALIZAÇÃO / RESET
    # ==============================================================

    def _init_state(self):
        """Zera o estado volátil (resetado no prestígio)."""
        self.ouro = 250.0

        self.escravos: list[Escravo] = []
        self.inventario = {r: 0 for r in RESOURCE_ORDER}

        self.nivel_mina = 0
        self.upgrades   = {k: 0 for k in UPGRADE_ORDER}

        self.loja: list[Escravo] = []
        self.custo_refresco  = 50
        self._ultimo_refresco = 0.0

        self.pares: list[tuple] = []

        # Timers (tempo real)
        self._t_autosave = time.time()
        self._t_evento   = time.time()

        # Timer de breeding (tempo de jogo)
        self._t_breed = 0.0

        self.velocidade = 1
        self.pausado    = False
        self.tempo_jogo = 0.0

        # Evento/notificação modal
        self.notificacao: dict | None = None

        # Mercado negro
        self.mercado_negro       = False
        self.mercado_negro_timer = 0.0

        # Log em memória: [{"msg", "cor", "ts"}]
        self.log: list[dict] = []

        # Estatísticas acumuladas (persistem no prestígio)
        self.stats = {
            "escravos_total":  0,
            "mortos_total":    0,
            "filhos_nascidos": 0,
            "ouro_total":      0.0,
            "recursos_enc":    set(),
            "rec_qtd":         {r: 0 for r in RESOURCE_ORDER},
            "max_simult":      0,
            "tempo_total_jogo": 0.0,
        }

        self.conquistas: set = set()

        self.prestigios      = 0
        self.almas_eternas   = 0
        self.bonus_prestigio = 1.0

        self.primeiro_jogo = True

        self._gerar_loja(forcar=True)

    # ==============================================================
    # PROPRIEDADES
    # ==============================================================

    @property
    def escravos_vivos(self) -> list[Escravo]:
        return [e for e in self.escravos if e.vivo and not e.eh_bebe]

    @property
    def bebes(self) -> list[Escravo]:
        return [e for e in self.escravos if e.vivo and e.eh_bebe]

    @property
    def run_numero(self) -> int:
        return self.prestigios + 1

    @property
    def intervalo_efetivo(self) -> float:
        bv = MINE_UPGRADES["ventilacao"]["niveis"][self.upgrades["ventilacao"]]["bonus_vel"]
        return MINING_INTERVAL / bv

    @property
    def mult_raridade(self) -> float:
        d = MINE_DEPTHS[self.nivel_mina]["mult_raridade"]
        i = MINE_UPGRADES["iluminacao"]["niveis"][self.upgrades["iluminacao"]]["bonus_sorte"]
        return d * i * self.bonus_prestigio

    @property
    def mult_recursos(self) -> float:
        f = MINE_UPGRADES["ferramentas"]["niveis"][self.upgrades["ferramentas"]]["bonus_recursos"]
        return f * self.bonus_prestigio

    @property
    def mult_sorte(self) -> float:
        return MINE_UPGRADES["iluminacao"]["niveis"][self.upgrades["iluminacao"]]["bonus_sorte"]

    @property
    def desgaste_mult(self) -> float:
        bv = MINE_UPGRADES["alimentacao"]["niveis"][self.upgrades["alimentacao"]]["bonus_vida"]
        return 1.0 / bv

    @property
    def risco_morte(self) -> float:
        base = MINE_DEPTHS[self.nivel_mina]["risco_morte"]
        red  = MINE_UPGRADES["seguranca"]["niveis"][self.upgrades["seguranca"]]["red_morte"]
        return max(0.001, base * (1 - red))

    @property
    def lealdade_media(self) -> float:
        vivos = self.escravos_vivos
        return sum(e.lealdade for e in vivos) / len(vivos) if vivos else 50.0

    @property
    def valor_inventario(self) -> int:
        return sum(RESOURCES[r]["valor"] * q for r, q in self.inventario.items())

    # ==============================================================
    # UPDATE PRINCIPAL
    # ==============================================================

    def update(self, delta: float, agora_real: float):
        self.tempo_jogo += delta
        self.stats["tempo_total_jogo"] += delta

        if self.mercado_negro:
            self.mercado_negro_timer -= delta
            if self.mercado_negro_timer <= 0:
                self.mercado_negro = False
                self.log_add("O mercado negro fechou.", ORANGE)

        for escravo in list(self.escravos):
            if not escravo.vivo:
                continue
            morreu = escravo.update(delta, self.desgaste_mult)
            if morreu:
                self._on_morte(escravo, escravo.causa_morte or "Exaustão")
                continue
            if not escravo.eh_bebe and escravo.pode_minerar(self.tempo_jogo, self.intervalo_efetivo):
                self._ciclo_mineracao(escravo)
                if random.random() < self.risco_morte:
                    self._on_morte(escravo, "Acidente na mina")

        self.escravos = [e for e in self.escravos if e.vivo]

        # Breeding
        self._t_breed += delta
        if self._t_breed >= BREEDING_INTERVAL:
            self._t_breed = 0.0
            self._update_breeding()

        # Eventos (tempo real)
        if agora_real - self._t_evento >= EVENT_INTERVAL:
            self._t_evento = agora_real
            self._tentar_evento()

        # Autosave (tempo real)
        if agora_real - self._t_autosave >= AUTOSAVE_INTERVAL:
            self._t_autosave = agora_real
            self.save()
            self.log_add("[SISTEMA] Progresso salvo automaticamente.", GRAY)

        n = len(self.escravos_vivos)
        if n > self.stats["max_simult"]:
            self.stats["max_simult"] = n

        self._verificar_conquistas()

    # ==============================================================
    # MINERAÇÃO
    # ==============================================================

    def _ciclo_mineracao(self, escravo: Escravo):
        recurso, qtd, valor = escravo.executar_mineracao(
            self.tempo_jogo, self.mult_raridade, self.mult_recursos, self.mult_sorte
        )
        self.inventario[recurso] = self.inventario.get(recurso, 0) + qtd
        self.stats["recursos_enc"].add(recurso)
        self.stats["rec_qtd"][recurso] = self.stats["rec_qtd"].get(recurso, 0) + qtd

        # Batch para o banco de dados
        self._mining_batch.append((escravo.id, escravo.nome, recurso, qtd, valor))

        raro = RESOURCES[recurso]["raridade"] < 0.10
        if raro or random.random() < 0.10:
            self.log_add(f"{escravo.nome} encontrou {qtd}x {recurso}! (+{valor}g)",
                         RESOURCES[recurso]["cor"])

    def acelerar_mineracao(self):
        vivos = self.escravos_vivos
        custo = max(5, len(vivos) * 5)
        if self.ouro < custo:
            return False, f"Precisa de {custo}g"
        self.ouro -= custo
        for e in vivos:
            e.ultimo_ciclo = 0
        self.log_add(f"Mineração acelerada! Custo: {custo}g", YELLOW)
        return True, "Acelerado!"

    # ==============================================================
    # MORTE
    # ==============================================================

    def _on_morte(self, escravo: Escravo, causa: str):
        escravo.vivo        = False
        escravo.causa_morte = causa
        self.stats["mortos_total"] += 1
        self.pares = [(m, f) for m, f in self.pares
                      if m != escravo.id and f != escravo.id]
        if escravo.par_id:
            par = self.get_escravo(escravo.par_id)
            if par:
                par.par_id = None
        self.db.registrar_morte(escravo, self.run_numero)
        self.log_add(f"[MORTE] {escravo.nome} faleceu. Causa: {causa}", RED)

    # ==============================================================
    # BREEDING
    # ==============================================================

    def _update_breeding(self):
        for hid, fid in list(self.pares):
            hm = self.get_escravo(hid)
            fm = self.get_escravo(fid)
            if not hm or not fm or not hm.vivo or not fm.vivo:
                self.pares = [(m, f) for m, f in self.pares
                              if m != hid and f != fid]
                continue
            fert = (hm.fertilidade + fm.fertilidade) / 2
            bl   = ((hm.lealdade + fm.lealdade) / 2) / 100 * 0.2
            if random.random() < (fert / 100) * 0.35 + bl:
                self._gerar_filho(hm, fm)

    def _gerar_filho(self, pai: Escravo, mae: Escravo):
        filho              = Escravo(pai=pai, mae=mae)
        filho.eh_bebe      = True
        filho.tempo_crescimento = GROWTH_TIME
        filho.minerando    = False
        filho.vida         = filho.vida_max
        self.escravos.append(filho)
        self.stats["filhos_nascidos"] += 1
        self.stats["escravos_total"]  += 1
        self.db.registrar_escravo(filho, self.run_numero, "nascido",
                                   pai_id=pai.id, mae_id=mae.id)
        gen = "menino" if filho.genero == "M" else "menina"
        self.log_add(f"[NASCIMENTO] {pai.nome} × {mae.nome} → {filho.nome} ({gen})", GREEN)

    def adicionar_par(self, hid: int, fid: int):
        hm = self.get_escravo(hid)
        fm = self.get_escravo(fid)
        if not hm or not fm:
            return False, "Escravo não encontrado."
        if hm.genero != "M" or fm.genero != "F":
            return False, "Precisa de um homem e uma mulher."
        if hm.par_id or fm.par_id:
            return False, "Um deles já tem parceiro."
        self.pares.append((hid, fid))
        hm.par_id = fid
        fm.par_id = hid
        self.log_add(f"Par formado: {hm.nome} + {fm.nome}", CYAN)
        return True, "Par formado!"

    def remover_par(self, hid: int):
        hm = self.get_escravo(hid)
        if hm and hm.par_id:
            fm = self.get_escravo(hm.par_id)
            if fm:
                fm.par_id = None
            hm.par_id = None
        self.pares = [(m, f) for m, f in self.pares if m != hid]

    # ==============================================================
    # COMPRA / VENDA
    # ==============================================================

    def comprar_escravo(self, escravo: Escravo):
        preco = escravo.calcular_preco()
        if self.ouro < preco:
            return False, f"Precisa de {preco}g"
        self.ouro -= preco
        escravo.ultimo_ciclo = 0
        self.escravos.append(escravo)
        if escravo in self.loja:
            self.loja.remove(escravo)
        self.stats["escravos_total"] += 1
        self.db.registrar_escravo(escravo, self.run_numero, "comprado")
        self.log_add(f"Comprou {escravo.nome} por {preco}g.", YELLOW)
        return True, "Comprado!"

    def vender_escravo(self, escravo: Escravo):
        preco = escravo.calcular_preco(mercado_negro=self.mercado_negro)
        self.remover_par(escravo.id)
        self.ouro += preco
        self.stats["ouro_total"] += preco
        if escravo in self.escravos:
            self.escravos.remove(escravo)
        self.log_add(f"Vendeu {escravo.nome} por {preco}g.", YELLOW)
        return preco

    def vender_recurso(self, recurso: str, qtd: int | None = None) -> int:
        disp = self.inventario.get(recurso, 0)
        if disp <= 0:
            return 0
        qtd   = min(qtd or disp, disp)
        val   = RESOURCES[recurso]["valor"]
        if self.mercado_negro:
            val = int(val * 1.5)
        total = val * qtd
        self.ouro += total
        self.stats["ouro_total"] += total
        self.inventario[recurso] -= qtd
        return total

    def vender_tudo(self) -> int:
        total = sum(self.vender_recurso(r) for r in RESOURCE_ORDER)
        if total:
            self.log_add(f"Vendeu tudo por {total}g.", YELLOW)
        return total

    # ==============================================================
    # UPGRADES E MINA
    # ==============================================================

    def comprar_upgrade(self, tipo: str):
        lvl    = self.upgrades[tipo]
        niveis = MINE_UPGRADES[tipo]["niveis"]
        if lvl >= len(niveis) - 1:
            return False, "Nível máximo!"
        custo = niveis[lvl + 1]["custo"]
        if self.ouro < custo:
            return False, f"Precisa de {custo}g"
        self.ouro -= custo
        self.upgrades[tipo] += 1
        self.log_add(f"'{MINE_UPGRADES[tipo]['nome']}' nível {self.upgrades[tipo]}!", CYAN)
        return True, "Upgrade comprado!"

    def proximo_upgrade_info(self, tipo: str):
        lvl    = self.upgrades[tipo]
        niveis = MINE_UPGRADES[tipo]["niveis"]
        if lvl >= len(niveis) - 1:
            return None, "Máximo", False
        prox = niveis[lvl + 1]
        return prox["custo"], prox["nome"], self.ouro >= prox["custo"]

    def aprofundar_mina(self):
        if self.nivel_mina >= len(MINE_DEPTHS) - 1:
            return False, "Profundidade máxima!"
        custo = MINE_DEPTHS[self.nivel_mina + 1]["custo"]
        if self.ouro < custo:
            return False, f"Precisa de {custo}g"
        self.ouro -= custo
        self.nivel_mina += 1
        self.log_add(f"Mina aprofundada: {MINE_DEPTHS[self.nivel_mina]['nome']}!", GOLD)
        return True, "Mina aprofundada!"

    # ==============================================================
    # LOJA
    # ==============================================================

    def _gerar_loja(self, forcar: bool = False):
        agora = time.time()
        if not forcar and agora - self._ultimo_refresco < SHOP_REFRESH_TIME:
            return
        self._ultimo_refresco = agora
        self.loja = [Escravo(lendario=random.random() < 0.04)
                     for _ in range(random.randint(3, 6))]
        for e in self.loja:
            e.ultimo_ciclo = -999

    def refresca_loja(self):
        if self.ouro < self.custo_refresco:
            return False, f"Precisa de {self.custo_refresco}g"
        self.ouro -= self.custo_refresco
        self._gerar_loja(forcar=True)
        self.custo_refresco = int(self.custo_refresco * 1.5)
        return True, "Loja atualizada!"

    # ==============================================================
    # EVENTOS ALEATÓRIOS
    # ==============================================================

    def _tentar_evento(self):
        if not self.escravos_vivos or self.notificacao:
            return
        for ev in random.sample(RANDOM_EVENTS, len(RANDOM_EVENTS)):
            chance = ev["chance"]
            if ev["id"] == "rebelliao":
                seg = MINE_UPGRADES["seguranca"]["niveis"][self.upgrades["seguranca"]]["red_rebel"]
                chance = (0.02 + max(0, 50 - self.lealdade_media) * 0.002) * (1 - seg)
            elif ev["id"] == "fuga":
                chance = 0.05 + max(0, 50 - self.lealdade_media) * 0.001
            if random.random() < chance:
                self._disparar_evento(ev["id"])
                break

    def _disparar_evento(self, eid: str):
        handler = {
            "rebelliao":       self._ev_rebelliao,
            "caverna_secreta": self._ev_caverna,
            "fuga":            self._ev_fuga,
            "doacao":          self._ev_doacao,
            "epidemia":        self._ev_epidemia,
            "mineral_lend":    self._ev_mineral,
            "acidente":        self._ev_acidente,
            "mercado_negro":   self._ev_mercado,
        }.get(eid)
        if handler:
            handler()

    def _ev_rebelliao(self):
        vivos = self.escravos_vivos
        if not vivos: return
        n = max(1, len(vivos) // 5)
        mortos = random.sample(vivos, min(n, len(vivos)))
        for e in mortos: self._on_morte(e, "Rebelião")
        perda = min(self.ouro * 0.2, 200)
        self.ouro -= perda
        msg = f"[REBELIÃO] {len(mortos)} mortos. -{perda:.0f}g."
        self.log_add(msg, RED)
        self.db.log_evento("rebelliao", msg, self.run_numero)
        self.notificacao = {"titulo": "Rebelião!", "msg": f"{len(mortos)} escravos se revoltaram!", "cor": RED}

    def _ev_caverna(self):
        for r in ["Ouro", "Esmeralda", "Diamante"]:
            q = random.randint(5, 20)
            self.inventario[r] += q
            self.stats["rec_qtd"][r] += q
            self.stats["recursos_enc"].add(r)
        msg = "[CAVERNA] Caverna secreta! Riquezas encontradas!"
        self.log_add(msg, GOLD)
        self.db.log_evento("caverna_secreta", msg, self.run_numero)
        self.notificacao = {"titulo": "Caverna Secreta!", "msg": "Ouro, Esmeralda e Diamante encontrados!", "cor": GOLD}

    def _ev_fuga(self):
        vivos = self.escravos_vivos
        if not vivos: return
        fugitivo = min(vivos, key=lambda e: e.lealdade)
        self._on_morte(fugitivo, "Fuga")
        msg = f"[FUGA] {fugitivo.nome} escapou!"
        self.log_add(msg, ORANGE)
        self.db.log_evento("fuga", msg, self.run_numero)
        self.notificacao = {"titulo": "Fuga!", "msg": f"{fugitivo.nome} aproveitou um descuido.", "cor": ORANGE}

    def _ev_doacao(self):
        novo = Escravo()
        novo.ultimo_ciclo = 0
        self.escravos.append(novo)
        self.stats["escravos_total"] += 1
        self.db.registrar_escravo(novo, self.run_numero, "doado")
        msg = f"[DOAÇÃO] {novo.nome} foi doado a você!"
        self.log_add(msg, GREEN)
        self.db.log_evento("doacao", msg, self.run_numero)
        self.notificacao = {"titulo": "Doação!", "msg": f"{novo.nome} entregue como pagamento.", "cor": GREEN}

    def _ev_epidemia(self):
        for e in self.escravos_vivos:
            e.vida = max(1, e.vida - random.randint(20, 50))
        msg = "[EPIDEMIA] Doença na mina! Todos perderam saúde."
        self.log_add(msg, PURPLE)
        self.db.log_evento("epidemia", msg, self.run_numero)
        self.notificacao = {"titulo": "Epidemia!", "msg": "Todos os escravos perderam saúde.", "cor": PURPLE}

    def _ev_mineral(self):
        q = random.randint(1, 3)
        self.inventario["Adamantita"] += q
        self.stats["rec_qtd"]["Adamantita"] += q
        self.stats["recursos_enc"].add("Adamantita")
        msg = f"[LENDÁRIO] Veia de Adamantita! +{q}!"
        self.log_add(msg, PURPLE)
        self.db.log_evento("mineral_lend", msg, self.run_numero)
        self.notificacao = {"titulo": "Veia Lendária!", "msg": f"+{q} Adamantita encontrada!", "cor": PURPLE}

    def _ev_acidente(self):
        vivos = self.escravos_vivos
        if not vivos: return
        n = max(1, len(vivos) // 10)
        mortos = random.sample(vivos, min(n, len(vivos)))
        for e in mortos: self._on_morte(e, "Acidente na mina")
        msg = f"[ACIDENTE] Desabamento! {len(mortos)} morto(s)."
        self.log_add(msg, RED)
        self.db.log_evento("acidente", msg, self.run_numero)
        self.notificacao = {"titulo": "Acidente!", "msg": f"Desabamento matou {len(mortos)} escravo(s).", "cor": RED}

    def _ev_mercado(self):
        self.mercado_negro       = True
        self.mercado_negro_timer = 60.0
        msg = "[MERCADO] Mercado negro ativo por 60s! +50%."
        self.log_add(msg, CYAN)
        self.db.log_evento("mercado_negro", msg, self.run_numero)
        self.notificacao = {"titulo": "Mercado Negro!", "msg": "Preços +50% por 60 segundos.", "cor": CYAN}

    # ==============================================================
    # PRESTÍGIO
    # ==============================================================

    def pode_prestigiar(self) -> bool:
        return self.stats["ouro_total"] >= PRESTIGE_GOLD_REQ

    def fazer_prestigio(self):
        if not self.pode_prestigiar():
            return False, "Ouro total insuficiente."
        self.db.registrar_prestigio(
            self.run_numero, self.stats,
            1 + self.prestigios, 1.0 + (self.prestigios + 1) * PRESTIGE_BONUS_STEP
        )
        self.prestigios    += 1
        self.almas_eternas += 1 + self.prestigios
        self.bonus_prestigio = 1.0 + self.prestigios * PRESTIGE_BONUS_STEP

        # Preserva dados permanentes
        stats_bkp = {k: (set(v) if isinstance(v, set) else v)
                     for k, v in self.stats.items()}
        conq_bkp  = set(self.conquistas)
        prest_bkp = self.prestigios
        almas_bkp = self.almas_eternas
        bonus_bkp = self.bonus_prestigio

        self._init_state()

        self.stats           = stats_bkp
        self.conquistas      = conq_bkp
        self.prestigios      = prest_bkp
        self.almas_eternas   = almas_bkp
        self.bonus_prestigio = bonus_bkp
        self.ouro            = 250 + self.almas_eternas * 20
        self.primeiro_jogo   = False

        self.log_add(f"[PRESTÍGIO #{self.prestigios}] Bônus global: {self.bonus_prestigio:.1f}x!", GOLD)
        return True, f"Prestígio #{self.prestigios} realizado!"

    # ==============================================================
    # CONQUISTAS
    # ==============================================================

    def _verificar_conquistas(self):
        for ach in ACHIEVEMENTS:
            if ach["id"] in self.conquistas:
                continue
            tipo, val = ach["cond"]
            ok = False
            if   tipo == "escravos_total": ok = self.stats["escravos_total"]  >= val
            elif tipo == "escravos_vivos": ok = len(self.escravos_vivos)       >= val
            elif tipo == "recurso":        ok = val in self.stats["recursos_enc"]
            elif tipo == "ouro":           ok = self.ouro                      >= val
            elif tipo == "mortos":         ok = self.stats["mortos_total"]     >= val
            elif tipo == "filhos":         ok = self.stats["filhos_nascidos"]  >= val
            elif tipo == "prestigios":     ok = self.prestigios                >= val
            elif tipo == "tempo_sobrev":
                ok = any(e.tempo_na_mina >= val for e in self.escravos_vivos)
            if ok:
                self.conquistas.add(ach["id"])
                self.db.registrar_conquista(ach["id"], ach["nome"], ach["desc"], self.run_numero)
                self.log_add(f"[CONQUISTA] '{ach['nome']}' desbloqueada!", GOLD)

    # ==============================================================
    # LOG
    # ==============================================================

    def log_add(self, msg: str, cor=WHITE):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log.insert(0, {"msg": msg, "cor": cor, "ts": ts})
        if len(self.log) > 300:
            self.log = self.log[:300]

    # ==============================================================
    # HELPERS
    # ==============================================================

    def get_escravo(self, eid: int) -> Escravo | None:
        for e in self.escravos:
            if e.id == eid:
                return e
        return None

    # ==============================================================
    # SAVE / LOAD
    # ==============================================================

    def _to_save_dict(self) -> dict:
        return {
            "version": "1.1",
            "ouro": self.ouro,
            "inventario": self.inventario,
            "nivel_mina": self.nivel_mina,
            "upgrades": self.upgrades,
            "escravos": [e.to_dict() for e in self.escravos if e.vivo],
            "pares": list(self.pares),
            "stats": {
                k: list(v) if isinstance(v, set) else v
                for k, v in self.stats.items()
            },
            "conquistas": list(self.conquistas),
            "prestigios": self.prestigios,
            "almas_eternas": self.almas_eternas,
            "bonus_prestigio": self.bonus_prestigio,
            "tempo_jogo": self.tempo_jogo,
            "velocidade": self.velocidade,
            "custo_refresco": self.custo_refresco,
            "primeiro_jogo": self.primeiro_jogo,
            "id_counter": Escravo._id_counter,
            "log": self.log[:50],   # Salva as 50 últimas mensagens do log
        }

    def save(self) -> bool:
        # Flush do batch de mineração para o banco
        self.db.flush_mineracao(self._mining_batch, self.run_numero)
        self._mining_batch.clear()
        return self.db.save_state(self._to_save_dict())

    def load(self) -> bool:
        # Migração: tenta importar save JSON legado
        self._migrate_json()

        d = self.db.load_state()
        if not d:
            return False
        try:
            self.ouro            = d.get("ouro", 250.0)
            self.inventario      = d.get("inventario", {r: 0 for r in RESOURCE_ORDER})
            self.nivel_mina      = d.get("nivel_mina", 0)
            self.upgrades        = d.get("upgrades", {k: 0 for k in UPGRADE_ORDER})
            self.prestigios      = d.get("prestigios", 0)
            self.almas_eternas   = d.get("almas_eternas", 0)
            self.bonus_prestigio = d.get("bonus_prestigio", 1.0)
            self.tempo_jogo      = d.get("tempo_jogo", 0.0)
            self.velocidade      = d.get("velocidade", 1)
            self.custo_refresco  = d.get("custo_refresco", 50)
            self.primeiro_jogo   = d.get("primeiro_jogo", True)

            stats_raw = d.get("stats", {})
            for k, v in stats_raw.items():
                if k == "recursos_enc":
                    self.stats[k] = set(v) if isinstance(v, list) else set()
                elif k == "rec_qtd":
                    self.stats[k] = {r: v.get(r, 0) for r in RESOURCE_ORDER}
                else:
                    self.stats[k] = v

            self.conquistas = set(d.get("conquistas", []))

            Escravo._id_counter = d.get("id_counter", 0)
            self.escravos = [Escravo.from_dict(ed) for ed in d.get("escravos", [])]
            self.pares    = [tuple(p) for p in d.get("pares", [])]

            # Restaura log salvo
            saved_log = d.get("log", [])
            self.log  = saved_log if saved_log else self.log

            self._gerar_loja(forcar=True)

            # Inicia sessão no banco
            self._sessao_id     = self.db.iniciar_sessao(self.run_numero, self.ouro)
            self._sessao_inicio = time.time()

            self.log_add("Jogo carregado com sucesso!", GREEN)
            return True
        except Exception as exc:
            print(f"Erro ao carregar: {exc}")
            self.log_add(f"Erro ao carregar: {exc}", RED)
            return False

    def _migrate_json(self):
        """Importa save JSON legado para o banco de dados e o renomeia."""
        legacy = "save_eternal_mine.json"
        if not os.path.exists(legacy):
            return
        try:
            with open(legacy, encoding="utf-8") as f:
                data = json.load(f)
            self.db.save_state(data)
            os.rename(legacy, legacy + ".migrated")
            print(f"[MIGRAÇÃO] {legacy} importado para o banco de dados.")
        except Exception as exc:
            print(f"[MIGRAÇÃO] Falhou: {exc}")

    def close(self):
        """Chamado ao encerrar o jogo."""
        tempo = time.time() - self._sessao_inicio
        self.db.encerrar_sessao(self._sessao_id, tempo, self.ouro)
        self.save()
        self.db.close()
