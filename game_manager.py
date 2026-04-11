# ============================================================
# game_manager.py — Gerenciador principal do jogo
# ============================================================

import json
import os
import random
import time

from app_paths import get_legacy_save_path, get_save_path
from slave import Escravo
from constants import (
    RESOURCES, RESOURCE_ORDER, MINE_UPGRADES, UPGRADE_ORDER,
    MINE_DEPTHS, RANDOM_EVENTS, ACHIEVEMENTS,
    PRESTIGE_GOLD_REQ, PRESTIGE_BONUS_STEP,
    MINING_INTERVAL, BREEDING_INTERVAL, GROWTH_TIME,
    AUTOSAVE_INTERVAL, EVENT_INTERVAL, SHOP_REFRESH_TIME,
    GREEN, RED, YELLOW, ORANGE, CYAN, GOLD, GRAY, PURPLE, WHITE,
)


class GameManager:
    """
    Gerencia todo o estado do jogo: escravos, recursos, upgrades,
    eventos, reprodução, conquistas, save/load e prestígio.
    """

    SAVE_FILE = get_save_path()
    LEGACY_SAVE_FILE = get_legacy_save_path()

    def __init__(self):
        self._init_state()

    # ==============================================================
    # INICIALIZAÇÃO / RESET
    # ==============================================================

    def _init_state(self):
        """Inicializa (ou reseta) todo o estado do jogo."""

        # Economia (suficiente para comprar o primeiro escravo)
        self.ouro = 250.0

        # Escravos
        self.escravos: list[Escravo] = []

        # Inventário de recursos
        self.inventario = {r: 0 for r in RESOURCE_ORDER}

        # Mina
        self.nivel_mina = 0
        self.upgrades   = {k: 0 for k in UPGRADE_ORDER}

        # Loja
        self.loja: list[Escravo] = []
        self.custo_refresco  = 50
        self._ultimo_refresco = 0.0

        # Pares de reprodução [(id_homem, id_mulher), ...]
        self.pares: list[tuple] = []

        # Timers (tempo real)
        self._t_autosave = time.time()
        self._t_evento   = time.time()

        # Timer de breeding (tempo de jogo)
        self._t_breed = 0.0

        # Velocidade / pausa
        self.velocidade = 1
        self.pausado    = False

        # Tempo de jogo total (segundos, afetado pela velocidade)
        self.tempo_jogo = 0.0

        # Notificação de evento modal
        self.notificacao: dict | None = None

        # Mercado negro
        self.mercado_negro       = False
        self.mercado_negro_timer = 0.0

        # Log de eventos (lista de {"msg":str, "cor":tuple})
        self.log: list[dict] = []

        # Estatísticas permanentes
        self.stats = {
            "escravos_total":  0,
            "mortos_total":    0,
            "filhos_nascidos": 0,
            "ouro_total":      0.0,
            "recursos_enc":    set(),     # set de nomes de recursos encontrados
            "rec_qtd":         {r: 0 for r in RESOURCE_ORDER},
            "max_simult":      0,
        }

        # Conquistas desbloqueadas
        self.conquistas: set = set()

        # Prestígio
        self.prestigios      = 0
        self.almas_eternas   = 0
        self.bonus_prestigio = 1.0

        # Flag de primeiro jogo (mostra tutorial)
        self.primeiro_jogo = True

        self._gerar_loja(forcar=True)

    # ==============================================================
    # PROPRIEDADES COMPUTADAS
    # ==============================================================

    @property
    def escravos_vivos(self):
        return [e for e in self.escravos if e.vivo and not e.eh_bebe]

    @property
    def bebes(self):
        return [e for e in self.escravos if e.vivo and e.eh_bebe]

    @property
    def intervalo_efetivo(self):
        """Intervalo de mineração ajustado pela ventilação."""
        bv = MINE_UPGRADES["ventilacao"]["niveis"][self.upgrades["ventilacao"]]["bonus_vel"]
        return MINING_INTERVAL / bv

    @property
    def mult_raridade(self):
        depth = MINE_DEPTHS[self.nivel_mina]["mult_raridade"]
        ilum  = MINE_UPGRADES["iluminacao"]["niveis"][self.upgrades["iluminacao"]]["bonus_sorte"]
        return depth * ilum * self.bonus_prestigio

    @property
    def mult_recursos(self):
        ferr = MINE_UPGRADES["ferramentas"]["niveis"][self.upgrades["ferramentas"]]["bonus_recursos"]
        return ferr * self.bonus_prestigio

    @property
    def mult_sorte(self):
        return MINE_UPGRADES["iluminacao"]["niveis"][self.upgrades["iluminacao"]]["bonus_sorte"]

    @property
    def desgaste_mult(self):
        """Alimentação reduz desgaste (vida_bonus > 1 → desgaste < 1)."""
        bv = MINE_UPGRADES["alimentacao"]["niveis"][self.upgrades["alimentacao"]]["bonus_vida"]
        return 1.0 / bv

    @property
    def risco_morte(self):
        base = MINE_DEPTHS[self.nivel_mina]["risco_morte"]
        red  = MINE_UPGRADES["seguranca"]["niveis"][self.upgrades["seguranca"]]["red_morte"]
        return max(0.001, base * (1 - red))

    @property
    def lealdade_media(self):
        vivos = self.escravos_vivos
        if not vivos:
            return 50
        return sum(e.lealdade for e in vivos) / len(vivos)

    @property
    def valor_inventario(self):
        return sum(RESOURCES[r]["valor"] * q for r, q in self.inventario.items())

    # ==============================================================
    # UPDATE PRINCIPAL
    # ==============================================================

    def update(self, delta: float, agora_real: float):
        """
        Chamado a cada frame pelo loop principal.
        delta = delta_real * velocidade (já multiplicado)
        agora_real = time.time() (para autosave e eventos)
        """
        self.tempo_jogo += delta

        # Mercado negro timer
        if self.mercado_negro:
            self.mercado_negro_timer -= delta
            if self.mercado_negro_timer <= 0:
                self.mercado_negro = False
                self.log_add("O mercado negro fechou.", ORANGE)

        # Atualiza escravos
        for escravo in list(self.escravos):
            if not escravo.vivo:
                continue

            morreu = escravo.update(delta, self.desgaste_mult)
            if morreu:
                self._on_morte(escravo, escravo.causa_morte or "Exaustão")
                continue

            if not escravo.eh_bebe and escravo.pode_minerar(self.tempo_jogo, self.intervalo_efetivo):
                self._ciclo_mineracao(escravo)
                # Risco de acidente
                if random.random() < self.risco_morte:
                    self._on_morte(escravo, "Acidente na mina")

        # Remove escravos mortos
        self.escravos = [e for e in self.escravos if e.vivo]

        # Breeding
        self._t_breed += delta
        if self._t_breed >= BREEDING_INTERVAL:
            self._t_breed = 0.0
            self._update_breeding()

        # Eventos aleatórios (tempo real)
        if agora_real - self._t_evento >= EVENT_INTERVAL:
            self._t_evento = agora_real
            self._tentar_evento()

        # Autosave (tempo real)
        if agora_real - self._t_autosave >= AUTOSAVE_INTERVAL:
            self._t_autosave = agora_real
            self.save()
            self.log_add("[SISTEMA] Progresso salvo automaticamente.", GRAY)

        # Atualiza estatísticas
        n = len(self.escravos_vivos)
        if n > self.stats["max_simult"]:
            self.stats["max_simult"] = n

        # Verifica conquistas
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

        # Loga apenas recursos raros (p < 0.10) ou 10% dos comuns
        raro = RESOURCES[recurso]["raridade"] < 0.10
        if raro or random.random() < 0.10:
            cor = RESOURCES[recurso]["cor"]
            self.log_add(f"{escravo.nome} encontrou {qtd}x {recurso}! (+{valor}g)", cor)

    def acelerar_mineracao(self):
        """Faz todos os escravos minerarem imediatamente. Custo: 5g por escravo."""
        vivos = self.escravos_vivos
        custo = max(5, len(vivos) * 5)
        if self.ouro < custo:
            return False, f"Precisa de {custo}g"
        self.ouro -= custo
        for e in vivos:
            e.ultimo_ciclo = 0  # força ciclo no próximo update
        self.log_add(f"Mineração acelerada! Custo: {custo}g", YELLOW)
        return True, "Acelerado!"

    # ==============================================================
    # MORTE
    # ==============================================================

    def _on_morte(self, escravo: Escravo, causa: str):
        escravo.vivo        = False
        escravo.causa_morte = causa
        self.stats["mortos_total"] += 1
        # Remove dos pares
        self.pares = [(m, f) for m, f in self.pares
                      if m != escravo.id and f != escravo.id]
        if escravo.par_id:
            par = self.get_escravo(escravo.par_id)
            if par:
                par.par_id = None
        self.log_add(f"[MORTE] {escravo.nome} faleceu. Causa: {causa}", RED)

    # ==============================================================
    # REPRODUÇÃO (BREEDING)
    # ==============================================================

    def _update_breeding(self):
        for homem_id, mulher_id in list(self.pares):
            homem  = self.get_escravo(homem_id)
            mulher = self.get_escravo(mulher_id)
            if not homem or not mulher or not homem.vivo or not mulher.vivo:
                self.pares = [(m, f) for m, f in self.pares
                              if m != homem_id and f != mulher_id]
                continue

            fert_med = (homem.fertilidade + mulher.fertilidade) / 2
            bons_leal = ((homem.lealdade + mulher.lealdade) / 2) / 100 * 0.2
            chance    = (fert_med / 100) * 0.35 + bons_leal

            if random.random() < chance:
                self._gerar_filho(homem, mulher)

    def _gerar_filho(self, pai: Escravo, mae: Escravo):
        filho              = Escravo(pai=pai, mae=mae)
        filho.eh_bebe      = True
        filho.tempo_crescimento = GROWTH_TIME
        filho.minerando    = False
        filho.vida         = filho.vida_max
        self.escravos.append(filho)
        self.stats["filhos_nascidos"] += 1
        self.stats["escravos_total"]  += 1
        gen_str = "menino" if filho.genero == "M" else "menina"
        self.log_add(
            f"[NASCIMENTO] {pai.nome} × {mae.nome} → {filho.nome} ({gen_str})", GREEN
        )

    def adicionar_par(self, hid, fid):
        homem  = self.get_escravo(hid)
        mulher = self.get_escravo(fid)
        if not homem or not mulher:
            return False, "Escravo não encontrado."
        if homem.genero != "M" or mulher.genero != "F":
            return False, "Precisa de um homem e uma mulher."
        if homem.par_id or mulher.par_id:
            return False, "Um deles já tem parceiro."
        self.pares.append((hid, fid))
        homem.par_id  = fid
        mulher.par_id = hid
        self.log_add(f"Par formado: {homem.nome} + {mulher.nome}", CYAN)
        return True, "Par formado!"

    def remover_par(self, hid):
        homem = self.get_escravo(hid)
        if homem and homem.par_id:
            par = self.get_escravo(homem.par_id)
            if par:
                par.par_id = None
            homem.par_id = None
        self.pares = [(m, f) for m, f in self.pares if m != hid]

    # ==============================================================
    # COMPRA / VENDA
    # ==============================================================

    def comprar_escravo(self, escravo: Escravo):
        preco = escravo.calcular_preco()
        if self.ouro < preco:
            return False, f"Precisa de {preco}g"
        self.ouro -= preco
        escravo.ultimo_ciclo = 0  # Começa a minerar logo
        self.escravos.append(escravo)
        if escravo in self.loja:
            self.loja.remove(escravo)
        self.stats["escravos_total"] += 1
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

    def vender_recurso(self, recurso, qtd=None):
        disp = self.inventario.get(recurso, 0)
        if disp <= 0:
            return 0
        if qtd is None:
            qtd = disp
        qtd   = min(qtd, disp)
        val   = RESOURCES[recurso]["valor"]
        if self.mercado_negro:
            val = int(val * 1.5)
        total = val * qtd
        self.ouro += total
        self.stats["ouro_total"] += total
        self.inventario[recurso] -= qtd
        return total

    def vender_tudo(self):
        total = sum(self.vender_recurso(r) for r in RESOURCE_ORDER)
        if total:
            self.log_add(f"Vendeu tudo por {total}g.", YELLOW)
        return total

    # ==============================================================
    # UPGRADES
    # ==============================================================

    def comprar_upgrade(self, tipo):
        lvl    = self.upgrades[tipo]
        niveis = MINE_UPGRADES[tipo]["niveis"]
        if lvl >= len(niveis) - 1:
            return False, "Nível máximo!"
        custo = niveis[lvl + 1]["custo"]
        if self.ouro < custo:
            return False, f"Precisa de {custo}g"
        self.ouro -= custo
        self.upgrades[tipo] += 1
        nome = MINE_UPGRADES[tipo]["nome"]
        self.log_add(f"'{nome}' nível {self.upgrades[tipo]}!", CYAN)
        return True, "Upgrade comprado!"

    def proximo_upgrade_info(self, tipo):
        """Retorna (custo, nome_nivel, pode_comprar) do próximo nível."""
        lvl    = self.upgrades[tipo]
        niveis = MINE_UPGRADES[tipo]["niveis"]
        if lvl >= len(niveis) - 1:
            return None, "Máximo", False
        prox  = niveis[lvl + 1]
        pode  = self.ouro >= prox["custo"]
        return prox["custo"], prox["nome"], pode

    def aprofundar_mina(self):
        if self.nivel_mina >= len(MINE_DEPTHS) - 1:
            return False, "Profundidade máxima!"
        custo = MINE_DEPTHS[self.nivel_mina + 1]["custo"]
        if self.ouro < custo:
            return False, f"Precisa de {custo}g"
        self.ouro -= custo
        self.nivel_mina += 1
        nome = MINE_DEPTHS[self.nivel_mina]["nome"]
        self.log_add(f"Mina aprofundada: {nome}!", GOLD)
        return True, "Mina aprofundada!"

    # ==============================================================
    # LOJA
    # ==============================================================

    def _gerar_loja(self, forcar=False):
        agora = time.time()
        if not forcar and agora - self._ultimo_refresco < SHOP_REFRESH_TIME:
            return
        self._ultimo_refresco = agora
        n = random.randint(3, 6)
        self.loja = []
        for _ in range(n):
            lend = random.random() < 0.04
            e    = Escravo(lendario=lend)
            e.ultimo_ciclo = -999
            self.loja.append(e)

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
                seg_red = MINE_UPGRADES["seguranca"]["niveis"][self.upgrades["seguranca"]]["red_rebel"]
                lack    = max(0, 50 - self.lealdade_media)
                chance  = (0.02 + lack * 0.002) * (1 - seg_red)
            elif ev["id"] == "fuga":
                chance  = 0.05 + max(0, 50 - self.lealdade_media) * 0.001

            if random.random() < chance:
                self._disparar_evento(ev["id"])
                break

    def _disparar_evento(self, eid: str):
        handlers = {
            "rebelliao":       self._ev_rebelliao,
            "caverna_secreta": self._ev_caverna,
            "fuga":            self._ev_fuga,
            "doacao":          self._ev_doacao,
            "epidemia":        self._ev_epidemia,
            "mineral_lend":    self._ev_mineral,
            "acidente":        self._ev_acidente,
            "mercado_negro":   self._ev_mercado,
        }
        if eid in handlers:
            handlers[eid]()

    def _ev_rebelliao(self):
        vivos = self.escravos_vivos
        if not vivos:
            return
        n      = max(1, len(vivos) // 5)
        mortos = random.sample(vivos, min(n, len(vivos)))
        for e in mortos:
            self._on_morte(e, "Rebelião")
        perda = min(self.ouro * 0.2, 200)
        self.ouro -= perda
        self.log_add(f"[REBELIÃO] {len(mortos)} escravo(s) mortos. -{perda:.0f}g.", RED)
        self.notificacao = {"titulo": "Rebelião!", "msg": f"{len(mortos)} escravo(s) se revoltaram!", "cor": RED}

    def _ev_caverna(self):
        for r in ["Ouro", "Esmeralda", "Diamante"]:
            q = random.randint(5, 20)
            self.inventario[r] += q
            self.stats["rec_qtd"][r] += q
            self.stats["recursos_enc"].add(r)
        self.log_add("[CAVERNA] Uma caverna secreta foi encontrada! Recursos incríveis!", GOLD)
        self.notificacao = {"titulo": "Caverna Secreta!", "msg": "Ouro, Esmeralda e Diamante encontrados!", "cor": GOLD}

    def _ev_fuga(self):
        vivos = self.escravos_vivos
        if not vivos:
            return
        fugitivo = min(vivos, key=lambda e: e.lealdade)
        self._on_morte(fugitivo, "Fuga")
        self.log_add(f"[FUGA] {fugitivo.nome} escapou!", ORANGE)
        self.notificacao = {"titulo": "Escravo Fugiu!", "msg": f"{fugitivo.nome} aproveitou um descuido e fugiu.", "cor": ORANGE}

    def _ev_doacao(self):
        novo = Escravo()
        novo.ultimo_ciclo = 0
        self.escravos.append(novo)
        self.stats["escravos_total"] += 1
        self.log_add(f"[DOAÇÃO] {novo.nome} foi doado a você!", GREEN)
        self.notificacao = {"titulo": "Doação!", "msg": f"{novo.nome} foi entregue como pagamento de dívida.", "cor": GREEN}

    def _ev_epidemia(self):
        for e in self.escravos_vivos:
            dano = random.randint(20, 50)
            e.vida = max(1, e.vida - dano)
        self.log_add("[EPIDEMIA] Uma doença varreu a mina! Todos perderam saúde.", PURPLE)
        self.notificacao = {"titulo": "Epidemia!", "msg": "Todos os escravos perderam saúde.", "cor": PURPLE}

    def _ev_mineral(self):
        q = random.randint(1, 3)
        self.inventario["Adamantita"] += q
        self.stats["rec_qtd"]["Adamantita"] += q
        self.stats["recursos_enc"].add("Adamantita")
        self.log_add(f"[LENDÁRIO] Veia de Adamantita! +{q}!", PURPLE)
        self.notificacao = {"titulo": "Veia Lendária!", "msg": f"+{q} Adamantita encontrada!", "cor": PURPLE}

    def _ev_acidente(self):
        vivos = self.escravos_vivos
        if not vivos:
            return
        n = max(1, len(vivos) // 10)
        mortos = random.sample(vivos, min(n, len(vivos)))
        for e in mortos:
            self._on_morte(e, "Acidente na mina")
        self.log_add(f"[ACIDENTE] Desabamento! {len(mortos)} morto(s).", RED)
        self.notificacao = {"titulo": "Acidente!", "msg": f"Desabamento matou {len(mortos)} escravo(s).", "cor": RED}

    def _ev_mercado(self):
        self.mercado_negro       = True
        self.mercado_negro_timer = 60.0
        self.log_add("[MERCADO] Mercado negro ativo por 60s! Preços +50%.", CYAN)
        self.notificacao = {"titulo": "Mercado Negro!", "msg": "Preços +50% por 60 segundos.", "cor": CYAN}

    # ==============================================================
    # PRESTÍGIO
    # ==============================================================

    def pode_prestigiar(self):
        return self.stats["ouro_total"] >= PRESTIGE_GOLD_REQ

    def fazer_prestigio(self):
        if not self.pode_prestigiar():
            return False, "Ouro total insuficiente para prestígio."
        self.prestigios    += 1
        self.almas_eternas += 1 + self.prestigios
        self.bonus_prestigio = 1.0 + self.prestigios * PRESTIGE_BONUS_STEP

        # Salva dados persistentes
        stats_bkp    = dict(self.stats)
        stats_bkp["recursos_enc"] = set(self.stats["recursos_enc"])
        conq_bkp     = set(self.conquistas)
        prest_bkp    = self.prestigios
        almas_bkp    = self.almas_eternas
        bonus_bkp    = self.bonus_prestigio

        self._init_state()

        self.stats           = stats_bkp
        self.conquistas      = conq_bkp
        self.prestigios      = prest_bkp
        self.almas_eternas   = almas_bkp
        self.bonus_prestigio = bonus_bkp
        self.ouro            = 100 + self.almas_eternas * 20
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
                self.log_add(f"[CONQUISTA] '{ach['nome']}' desbloqueada!", GOLD)

    # ==============================================================
    # HELPERS
    # ==============================================================

    def get_escravo(self, eid) -> Escravo | None:
        for e in self.escravos:
            if e.id == eid:
                return e
        return None

    def log_add(self, msg: str, cor=WHITE):
        self.log.insert(0, {"msg": msg, "cor": cor})
        if len(self.log) > 120:
            self.log = self.log[:120]

    # ==============================================================
    # SAVE / LOAD
    # ==============================================================

    def save(self):
        try:
            save_path = get_save_path()
            data = {
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
                "primeiro_jogo": False,
                "id_counter": Escravo._id_counter,
            }
            with save_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as ex:
            print(f"Erro ao salvar: {ex}")
            return False

    def load(self):
        save_path = get_save_path()
        legacy_path = get_legacy_save_path()

        load_path = save_path if save_path.exists() else legacy_path
        if not os.path.exists(load_path):
            return False
        try:
            with open(load_path, "r", encoding="utf-8") as f:
                d = json.load(f)

            self.ouro            = d.get("ouro", 100.0)
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

            # Estatísticas
            stats_raw = d.get("stats", {})
            self.stats = {k: 0 for k in self.stats}
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

            self._gerar_loja(forcar=True)
            self.log_add("Jogo carregado com sucesso!", GREEN)
            return True
        except Exception as ex:
            print(f"Erro ao carregar: {ex}")
            self.log_add(f"Erro ao carregar: {ex}", RED)
            return False
