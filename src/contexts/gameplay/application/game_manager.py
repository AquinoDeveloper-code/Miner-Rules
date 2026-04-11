from __future__ import annotations
# ============================================================
# game_manager.py — Gerenciador principal do jogo
# ============================================================

import json
import random
import time

from src.contexts.configuration.application.game_rules import load_rules
from src.contexts.configuration.infrastructure.app_paths import (
    delete_save_files,
    get_save_path,
    iter_legacy_save_paths,
)
from src.contexts.gameplay.domain.slave import Escravo
from src.contexts.gameplay.infrastructure.sqlite_storage import SQLiteStorage
from src.contexts.shared.constants import (
    RESOURCES, RESOURCE_ORDER, MINE_UPGRADES, UPGRADE_ORDER,
    MINE_DEPTHS, RANDOM_EVENTS, ACHIEVEMENTS,
    PRESTIGE_BONUS_STEP,
    GREEN, RED, YELLOW, ORANGE, CYAN, GOLD, GRAY, PURPLE, WHITE,
    SLOTS, ITEMS, ITEM_DROP_CHANCES,
    RETIREMENT_AGE, MAX_AGE,
)


class GameManager:
    """
    Gerencia todo o estado do jogo: escravos, recursos, upgrades,
    eventos, reprodução, conquistas, save/load e prestígio.
    Novos sistemas: alimentação, doença, equipamentos, aposentadoria.
    """

    SAVE_FILE = get_save_path()

    def __init__(self):
        self.storage = SQLiteStorage(get_save_path())
        self.rules = load_rules()
        self._init_state()

    # ==============================================================
    # INICIALIZAÇÃO / RESET
    # ==============================================================

    def _init_state(self):
        """Inicializa (ou reseta) todo o estado do jogo."""

        # Economia (suficiente para comprar o primeiro escravo)
        self.ouro = float(self.rules["initial_gold"])

        # Escravos
        self.escravos: list[Escravo] = []

        # Aposentados (fora da mina, mas existindo para referência/breeding)
        self.aposentados: list[Escravo] = []

        # Inventário de recursos
        self.inventario = {r: 0 for r in RESOURCE_ORDER}

        # Inventário de itens (lista de item_ids)
        self.inventario_itens: list[str] = []

        # Mina
        self.nivel_mina = 0
        self.upgrades   = {k: 0 for k in UPGRADE_ORDER}

        # Loja
        self.loja: list[dict] = []
        self.custo_refresco  = int(self.rules["shop_refresh_base_cost"])
        self._shop_offer_id = 1

        # Personalização de layout do jogador
        self.ui_config = self._default_ui_config()

        # Pares de reprodução [(id_homem, id_mulher), ...]
        self.pares: list[tuple] = []

        # Timers (tempo real)
        self._t_autosave = time.time()
        self._t_evento   = time.time()

        # Timer de breeding (tempo de jogo)
        self._t_breed = 0.0

        # Timers de comida e doença (tempo de jogo)
        self._t_comida = 0.0
        self._t_doenca = 0.0

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
        
        # Histórico timeline de eventos marcantes
        self.historico: list[tuple[float, str]] = []
        
        # Loja de Itens Equips/Consumiveis
        self.loja_itens: list[dict] = []
        self.loja_itens_timer = 0.0

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

        self._criar_servo_inicial()
        self._gerar_loja(forcar=True)

    @property
    def ano_atual(self) -> int:
        return int(self.tempo_jogo / 50.0) + 1

    @property
    def mes_atual(self) -> int:
        return int((self.tempo_jogo % 50.0) / 4.16) + 1

    def _default_ui_config(self):
        return {
            "ui_scale": 1.00,
            "sidebar_factor": 1.00,
            "mine_factor": 1.00,
            "center_factor": 1.00,
            "right_factor": 1.00,
            "bottom_factor": 1.00,
        }

    def _criar_servo_inicial(self):
        servo = Escravo(comum=True)
        servo.ultimo_ciclo = 0.0
        self.escravos.append(servo)
        self.stats["escravos_total"] = 1
        self.stats["max_simult"] = 1

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
    def servos_na_mina(self):
        return len([e for e in self.escravos if e.vivo])

    @property
    def capacidade_servos(self):
        return (self.nivel_mina + 1) * 10

    @property
    def intervalo_efetivo(self):
        """Intervalo de mineração ajustado pela ventilação."""
        bv = MINE_UPGRADES["ventilacao"]["niveis"][self.upgrades["ventilacao"]]["bonus_vel"]
        return self.rules["mining_interval"] / bv

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
        """Alimentação reduz desgaste (vida_bonus > 1 → desgaste < 1). Mantido para compatibilidade."""
        bv = MINE_UPGRADES["alimentacao"]["niveis"][self.upgrades["alimentacao"]]["bonus_vida"]
        return 1.0 / bv

    @property
    def risco_morte(self):
        base = MINE_DEPTHS[self.nivel_mina]["risco_morte"]
        red  = MINE_UPGRADES["seguranca"]["niveis"][self.upgrades["seguranca"]]["red_morte"]
        return max(0.001, base * (1 - red))

    def risco_morte_mineracao(self, escravo: Escravo):
        """
        A mina define o risco base, mas a idade define o quanto aquele
        servo está vulnerável. O mais novo fica com uma fração pequena
        do risco; o mais velho pode chegar a 70% no pior cenário.
        """
        idade_min = 16.0
        faixa_idade = max(1.0, float(MAX_AGE) - idade_min)
        progresso_idade = max(0.0, min(1.0, (escravo.idade - idade_min) / faixa_idade))

        fator_idade = 0.10 + progresso_idade * 3.40
        return min(0.70, max(0.001, self.risco_morte * fator_idade))

    @property
    def lealdade_media(self):
        vivos = self.escravos_vivos
        if not vivos:
            return 50
        return sum(e.lealdade for e in vivos) / len(vivos)

    @property
    def valor_inventario(self):
        return sum(RESOURCES[r]["valor"] * q for r, q in self.inventario.items())

    def pode_adicionar_servo(self, quantidade=1):
        return self.servos_na_mina + quantidade <= self.capacidade_servos

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

        self._update_loja(agora_real)

        # Atualiza escravos
        for escravo in list(self.escravos):
            if not escravo.vivo:
                continue

            morreu = escravo.update(delta, self.desgaste_mult)
            if morreu:
                self._on_morte(escravo, escravo.causa_morte or "Velhice")
                continue

            if not escravo.eh_bebe and escravo.pode_minerar(self.tempo_jogo, self.intervalo_efetivo):
                self._ciclo_mineracao(escravo)
                # Risco de acidente
                if random.random() < self.risco_morte_mineracao(escravo):
                    self._on_morte(escravo, "Acidente na mina")

        # Remove escravos mortos
        self.escravos = [e for e in self.escravos if e.vivo]

        # Breeding
        self._t_breed += delta
        if self._t_breed >= self.rules["breeding_interval"]:
            self._t_breed = 0.0
            self._update_breeding()

        # Comida (a cada FOOD_CHECK_INTERVAL segundos de jogo)
        self._t_comida += delta
        if self._t_comida >= self.rules["food_check_interval"]:
            self._t_comida = 0.0
            self._cobrar_comida()

        # Verificação de doenças (a cada 60s de jogo)
        self._t_doenca += delta
        if self._t_doenca >= 60.0:
            self._t_doenca = 0.0
            self._verificar_doencas()

        # Eventos aleatórios (tempo real)
        if agora_real - self._t_evento >= self.rules["event_interval"]:
            self._t_evento = agora_real
            self._tentar_evento()

        # Loja de Itens (reseta a cada 5 min de jogo)
        self.loja_itens_timer += delta
        if self.loja_itens_timer >= 300.0:
            self.loja_itens_timer = 0.0
            self._gerar_loja_itens()

        # Autosave (tempo real)
        if agora_real - self._t_autosave >= self.rules["autosave_interval"]:
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

        # Verificação de drop de item
        for item_id, chance in ITEM_DROP_CHANCES.items():
            sorte_bonus = escravo.sorte_efetiva() / 1000
            if random.random() < chance + sorte_bonus:
                self.inventario_itens.append(item_id)
                self.log_add(f"[ITEM] {escravo.nome} encontrou: {ITEMS[item_id]['nome']}!", PURPLE)
                break  # apenas um item por ciclo

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
    # SISTEMA DE ALIMENTAÇÃO
    # ==============================================================

    def _cobrar_comida(self):
        """
        Cobra o custo de alimentação de cada escravo vivo.
        Se não houver ouro suficiente, seta sem_comida=True no escravo.
        """
        todos = self.escravos_vivos + self.bebes
        for escravo in todos:
            custo = (
                self.rules["food_cost_quality"]
                if escravo.qualidade_comida == "qualidade"
                else self.rules["food_cost_basic"]
            )
            if self.ouro >= custo:
                self.ouro -= custo
                escravo.sem_comida = False
            else:
                escravo.sem_comida = True
                self.log_add(f"[FOME] {escravo.nome} nao foi alimentado!", ORANGE)

    # ==============================================================
    # SISTEMA DE DOENÇA
    # ==============================================================

    def _verificar_doencas(self):
        """
        Para cada escravo vivo, calcula a chance de contrair doença
        baseada na idade, qualidade da comida e stamina.
        """
        todos = self.escravos_vivos
        for escravo in todos:
            if escravo.doente:
                continue  # já está doente
            chance = self.rules["disease_base_chance"]
            # Idosos são mais suscetíveis
            if escravo.idade > 40:
                chance *= 2.0
            # Fome aumenta risco
            if escravo.sem_comida:
                chance *= 3.0
            # Stamina baixa aumenta risco
            if escravo.stamina < 30:
                chance *= 2.0
            # Comida de qualidade reduz risco
            if escravo.qualidade_comida == "qualidade":
                chance *= 0.4

            if random.random() < chance:
                escravo.doente       = True
                escravo.doenca_timer = self.rules["disease_duration"]
                self.log_add(f"[DOENÇA] {escravo.nome} ficou doente!", RED)

    # ==============================================================
    # SISTEMA DE EQUIPAMENTOS
    # ==============================================================

    def equipar_item(self, escravo_id: int, item_id: str) -> tuple[bool, str]:
        """Move item do inventário do jogador para o slot do escravo."""
        if item_id not in self.inventario_itens:
            return False, "Item não está no inventário."
        if item_id not in ITEMS:
            return False, "Item desconhecido."

        escravo = self.get_escravo(escravo_id)
        if not escravo:
            # Tenta nos aposentados
            escravo = self._get_aposentado(escravo_id)
        if not escravo:
            return False, "Servo não encontrado."

        slot = ITEMS[item_id]["slot"]

        # Se há item no slot, desequipa primeiro (se não for maldito)
        item_atual = escravo.equipamentos.get(slot)
        if item_atual:
            if escravo.maldicoes.get(slot, 0) > 0:
                return False, "Slot com maldição ativa! Não pode trocar."
            # Devolve ao inventário
            self.inventario_itens.append(item_atual)

        # Equipa
        self.inventario_itens.remove(item_id)
        escravo.equipamentos[slot] = item_id

        # Se item maldito, inicia timer de maldição
        item_data = ITEMS[item_id]
        if item_data.get("maldito", False):
            escravo.maldicoes[slot] = item_data.get("duracao_maldicao", 300.0)
            self.log_add(f"[MALDIÇÃO] {escravo.nome} equipou '{item_data['nome']}' MALDITO!", PURPLE)
        else:
            self.log_add(f"{escravo.nome} equipou '{item_data['nome']}'.", CYAN)

        return True, "Item equipado!"

    def desequipar_item(self, escravo_id: int, slot: str) -> tuple[bool, str]:
        """Move item do slot do escravo de volta ao inventário do jogador."""
        escravo = self.get_escravo(escravo_id)
        if not escravo:
            escravo = self._get_aposentado(escravo_id)
        if not escravo:
            return False, "Servo não encontrado."

        item_id = escravo.equipamentos.get(slot)
        if not item_id:
            return False, "Slot vazio."

        # Verifica maldição
        if escravo.maldicoes.get(slot, 0) > 0:
            return False, f"Item maldito! Aguarde {escravo.maldicoes[slot]:.0f}s ou use uma Reza."

        # Desequipa
        escravo.equipamentos[slot] = None
        self.inventario_itens.append(item_id)
        nome_item = ITEMS[item_id]["nome"] if item_id in ITEMS else item_id
        self.log_add(f"{escravo.nome} desequipou '{nome_item}'.", GRAY)
        return True, "Item removido!"

    def auto_equipar_melhores(self, escravo_id: int):
        escravo = self.get_escravo_qualquer(escravo_id)
        if not escravo: return False, "Servo não encontrado."
        return self._executar_auto_equip(escravo)

    def auto_equipar_melhores_todos(self):
        """Atribui os melhores equipamentos para todos os escravos vivos."""
        vivos = self.escravos
        if not vivos: return False, "Nenhum servo na mina."
        
        algum_equipado = False
        for e in vivos:
            sucesso, _ = self._executar_auto_equip(e, silent=True)
            if sucesso: algum_equipado = True
            
        if algum_equipado:
            self.log_add("Melhores equipamentos distribuídos para todos os servos!", GREEN)
            self._verificar_conquistas()
            return True, "Equipamentos otimizados em toda a mina!"
        return False, "Nenhum servo tinha itens melhores para equipar."

    def _executar_auto_equip(self, escravo: Escravo, silent=False):
        ranks = {"comum": 0, "incomum": 1, "raro": 2, "épico": 3, "lendário": 4}
        equipou_algo = False
        
        for slot in SLOTS:
            if escravo.maldicoes.get(slot, 0) > 0:
                continue
                
            best_item_id = None
            best_rank = -1
            
            curr_id = escravo.equipamentos.get(slot)
            if curr_id and curr_id in ITEMS:
                best_rank = ranks.get(ITEMS[curr_id].get("raridade", "comum"), -1)
                
            for iid in list(self.inventario_itens):
                if iid in ITEMS and ITEMS[iid]["slot"] == slot and not ITEMS[iid].get("consumivel"):
                    item_rank = ranks.get(ITEMS[iid].get("raridade", "comum"), 0)
                    if item_rank > best_rank:
                        best_rank = item_rank
                        best_item_id = iid
                        
            if best_item_id:
                if curr_id:
                    self.inventario_itens.append(curr_id)
                self.inventario_itens.remove(best_item_id)
                escravo.equipamentos[slot] = best_item_id
                equipou_algo = True
                
        if equipou_algo and not silent:
            self.log_add(f"Equipamentos automáticos atribuídos para {escravo.nome}!", GREEN)
            self._verificar_conquistas()
            return True, "Melhores itens equipados!"
        return equipou_algo, "Processado."

    def usar_item_especial(self, escravo_id: int, item_id: str) -> tuple[bool, str]:
        """
        Usa um item consumível do inventário na situação do escravo.
        Efeitos: 'quebrar_maldicao' ou 'curar_tudo'.
        """
        if item_id not in self.inventario_itens:
            return False, "Item não encontrado no inventário."
        if item_id not in ITEMS:
            return False, "Item desconhecido."

        item_data = ITEMS[item_id]
        if not item_data.get("consumivel", False):
            return False, "Este item não é consumível."

        escravo = self.get_escravo(escravo_id)
        if not escravo:
            escravo = self._get_aposentado(escravo_id)
        if not escravo:
            return False, "Servo não encontrado."

        efeito = item_data.get("efeito_consumivel")
        self.inventario_itens.remove(item_id)

        escravo.efeito_aura = True
        escravo.aura_timer  = 15.0
        escravo.cor_aura    = item_data.get("cor_visual", (0, 255, 0))

        if efeito == "quebrar_maldicao":
            # Remove todas as maldições do escravo
            for slot in SLOTS:
                escravo.maldicoes[slot] = 0.0
            self.log_add(f"[REZA] Maldições de {escravo.nome} foram quebradas!", CYAN)
            return True, "Maldições quebradas!"

        elif efeito == "curar_tudo":
            # Cura doença e restaura stamina
            escravo.doente       = False
            escravo.doenca_timer = 0.0
            escravo.stamina      = 100.0
            self.log_add(f"[CURA] {escravo.nome} foi curado!", GREEN)
            return True, "Servo curado!"

        return False, "Efeito desconhecido."

    # ==============================================================
    # APOSENTADORIA
    # ==============================================================

    def aposentar_escravo(self, escravo_id: int) -> tuple[bool, str]:
        """
        Aposenta um escravo: remove da lista de mineradores mas mantém
        para fins de referência (par, estatísticas).
        """
        escravo = self.get_escravo(escravo_id)
        if not escravo:
            return False, "Servo não encontrado."
        if escravo.idade < RETIREMENT_AGE:
            return False, f"Aposentadoria disponível a partir de {RETIREMENT_AGE} anos."
        if escravo.aposentado:
            return False, "Já aposentado."

        escravo.aposentado = True
        escravo.minerando  = False
        # Remove de pares ativos
        self.remover_par(escravo.id)

        # Move para lista de aposentados
        if escravo in self.escravos:
            self.escravos.remove(escravo)
        self.aposentados.append(escravo)

        self.log_add(f"[APOSENTADO] {escravo.nome} foi aposentado.", YELLOW)
        self.historico.append((self.tempo_jogo, f"APOSENTADO: {escravo.nome}"))
        return True, "Servo aposentado!"

    def _get_aposentado(self, escravo_id: int):
        for e in self.aposentados:
            if e.id == escravo_id:
                return e
        return None

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
        # Devolve equipamentos ao inventário
        for slot in SLOTS:
            item_id = escravo.equipamentos.get(slot)
            if item_id:
                self.inventario_itens.append(item_id)
                escravo.equipamentos[slot] = None
        self.log_add(f"[MORTE] {escravo.nome} faleceu. Causa: {causa}", RED)
        self.historico.append((self.tempo_jogo, f"MORTO: {escravo.nome} ({causa})"))

    # ==============================================================
    # REPRODUÇÃO (BREEDING)
    # ==============================================================

    def _update_breeding(self):
        if not self.pode_adicionar_servo():
            return

        for homem_id, mulher_id in list(self.pares):
            homem  = self.get_escravo(homem_id)
            mulher = self.get_escravo(mulher_id)
            if not homem or not mulher or not homem.vivo or not mulher.vivo:
                self.pares = [(m, f) for m, f in self.pares
                              if m != homem_id and f != mulher_id]
                continue

            if homem.breed_cooldown > 0 or mulher.breed_cooldown > 0:
                continue

            fert_med = (homem.fertilidade_efetiva() + mulher.fertilidade_efetiva()) / 2
            bons_leal = ((homem.lealdade_efetiva() + mulher.lealdade_efetiva()) / 2) / 100 * 0.2
            chance    = (fert_med / 100) * 0.35 + bons_leal

            if random.random() < chance:
                self._gerar_filho(homem, mulher)

    def _gerar_filho(self, pai: Escravo, mae: Escravo):
        if not self.pode_adicionar_servo():
            return False

        filho              = Escravo(pai=pai, mae=mae)
        filho.eh_bebe      = True
        filho.tempo_crescimento = self.rules["growth_time"]
        filho.minerando    = False
        filho.vida         = filho.vida_max
        self.escravos.append(filho)
        self.stats["filhos_nascidos"] += 1
        self.stats["escravos_total"]  += 1
        gen_str = "menino" if filho.genero == "M" else "menina"
        
        pai.breed_cooldown = 100.0 # 2 anos
        mae.breed_cooldown = 100.0
        
        self.log_add(
            f"[NASCIMENTO] {pai.nome} × {mae.nome} → {filho.nome} ({gen_str})", GREEN
        )
        self.historico.append((self.tempo_jogo, f"NASCIMENTO: {filho.nome} de {pai.nome} e {mae.nome}"))
        return True

    def adicionar_par(self, hid, fid):
        homem  = self.get_escravo(hid)
        mulher = self.get_escravo(fid)
        if not homem or not mulher:
            return False, "Servo não encontrado."
        if homem.genero != "M" or mulher.genero != "F":
            return False, "Precisa de um homem e uma mulher."
        if homem.par_id or mulher.par_id:
            return False, "Um deles já tem parceiro."
        self.pares.append((hid, fid))
        homem.par_id  = fid
        mulher.par_id = hid
        
        # Honeymoon bonus - 9 meses (37.5s)
        homem.par_honeymoon = 37.5
        mulher.par_honeymoon = 37.5
        
        self.log_add(f"Par formado: {homem.nome} + {mulher.nome} (Lua de Mel iniciada!)", CYAN)
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
        if not self.pode_adicionar_servo():
            return False, f"Capacidade maxima atingida: {self.capacidade_servos} servos."
        preco = escravo.calcular_preco(bonus_nivel_mina=self.nivel_mina)
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

    def comprar_oferta_loja(self, offer_id: int):
        oferta = self.get_oferta_loja(offer_id)
        if not oferta:
            return False, "Oferta não encontrada."

        ok, msg = self.comprar_escravo(oferta["servo"])
        if not ok:
            return False, msg

        self.loja = [item for item in self.loja if item["id"] != offer_id]
        return True, "Comprado!"

    def vender_escravo(self, escravo: Escravo):
        preco = escravo.calcular_preco(
            mercado_negro=self.mercado_negro,
            bonus_nivel_mina=self.nivel_mina,
        )
        self.remover_par(escravo.id)
        # Devolve equipamentos ao inventário antes de vender
        for slot in SLOTS:
            item_id = escravo.equipamentos.get(slot)
            if item_id:
                self.inventario_itens.append(item_id)
                escravo.equipamentos[slot] = None
        self.ouro += preco
        self.stats["ouro_total"] += preco
        if escravo in self.escravos:
            self.escravos.remove(escravo)
        if escravo in self.aposentados:
            self.aposentados.remove(escravo)
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

    def _nova_oferta_loja(self, agora=None, duration=None):
        agora = time.time() if agora is None else agora
        duration = float(duration or self.rules["shop_refresh_time"])
        lend = random.random() < 0.04
        servo = Escravo(lendario=lend)
        servo.ultimo_ciclo = -999

        oferta = {
            "id": self._shop_offer_id,
            "servo": servo,
            "created_at": agora,
            "duration": duration,
            "expires_at": agora + duration,
        }
        self._shop_offer_id += 1
        return oferta

    def _gerar_loja(self, forcar=False, quantidade=None):
        agora = time.time()
        alvo = quantidade if quantidade is not None else random.randint(3, 6)
        if not forcar and len(self.loja) >= alvo:
            return

        faltantes = max(0, alvo - len(self.loja))
        if forcar and quantidade is None and not self.loja:
            faltantes = random.randint(4, 6)

        for _ in range(faltantes):
            self.loja.append(self._nova_oferta_loja(agora=agora))

    def _gerar_loja_itens(self):
        self.loja_itens.clear()
        opcoes = list(ITEMS.keys())
        qtd = random.randint(3, 5)
        random.shuffle(opcoes)
        
        for iid in opcoes[:qtd]:
            data = ITEMS[iid]
            # preço custom * 2
            preco_base = 50 
            if "raridade" in data:
                if data["raridade"] == "incomum": preco_base = 150
                elif data["raridade"] == "raro": preco_base = 400
                elif data["raridade"] == "épico": preco_base = 1200
                elif data["raridade"] == "lendário": preco_base = 3500
            
            self.loja_itens.append({
                "id": iid,
                "preco": preco_base * 2
            })
        self.log_add("[LOJA] Novos itens especiais chegaram ao mercador (Reseta em 5min).", GOLD)

    def _update_loja(self, agora_real):
        if not self.loja:
            self._gerar_loja(forcar=True)
            return

        renovadas = 0
        for idx, oferta in enumerate(list(self.loja)):
            if agora_real >= oferta["expires_at"]:
                self.loja[idx] = self._nova_oferta_loja(agora=agora_real)
                renovadas += 1

        if renovadas:
            self.log_add(f"[LOJA] {renovadas} oferta(s) foram renovadas.", GRAY)

    def _acelerar_ofertas_antigas(self):
        if not self.loja:
            return

        agora = time.time()
        ordenadas = sorted(self.loja, key=lambda item: item["created_at"])
        total = max(1, len(ordenadas) - 1)

        for rank, oferta in enumerate(ordenadas):
            restante = max(5.0, oferta["expires_at"] - agora)
            fator = max(0.18, 0.60 - (rank / max(1, total)) * 0.35)
            oferta["expires_at"] = agora + max(8.0, restante * fator)

    def refresca_loja(self):
        if self.ouro < self.custo_refresco:
            return False, f"Precisa de {self.custo_refresco}g"
        self.ouro -= self.custo_refresco
        self._acelerar_ofertas_antigas()
        quantidade = random.randint(2, 4)
        self._gerar_loja(forcar=True, quantidade=len(self.loja) + quantidade)
        self.custo_refresco = int(self.custo_refresco * 1.5)
        return True, "Loja atualizada!"

    def tempo_restante_oferta(self, offer_id: int) -> float:
        oferta = self.get_oferta_loja(offer_id)
        if not oferta:
            return 0.0
        return max(0.0, oferta["expires_at"] - time.time())

    def comprar_item_loja(self, item_id: str, preco: int):
        if self.ouro < preco:
            return False, f"Precisa de {preco}g"
        
        # Encontra o item na loja
        idx_found = -1
        for i, shop_item in enumerate(self.loja_itens):
            if shop_item["id"] == item_id and shop_item["preco"] == preco:
                idx_found = i
                break
                
        if idx_found == -1:
            return False, "Item não disponível na loja atual."
            
        self.ouro -= preco
        self.loja_itens.pop(idx_found)
        self.inventario_itens.append(item_id)
        self.log_add(f"Comprado {ITEMS[item_id]['nome']} por {preco}g!", GOLD)
        
        return True, "Comprado com sucesso!"

    # ==============================================================
    # EVENTOS ALEATÓRIOS
    # ==============================================================

    def _tentar_evento(self):
        if not self.escravos_vivos or self.notificacao:
            return
        for ev in random.sample(RANDOM_EVENTS, len(RANDOM_EVENTS)):
            chance = self.rules["event_chances"].get(ev["id"], ev["chance"])
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
        self.log_add(f"[REBELIÃO] {len(mortos)} servo(s) mortos. -{perda:.0f}g.", RED)
        self.notificacao = {"titulo": "Rebelião!", "msg": f"{len(mortos)} servo(s) se revoltaram!", "cor": RED}

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
        self.notificacao = {"titulo": "Servo Fugiu!", "msg": f"{fugitivo.nome} aproveitou um descuido e fugiu.", "cor": ORANGE}

    def _ev_doacao(self):
        if not self.pode_adicionar_servo():
            self.log_add("[DOAÇÃO] Sem espaco para receber outro servo.", ORANGE)
            self.notificacao = {"titulo": "Doação!", "msg": "Sem espaco na mina para receber outro servo.", "cor": ORANGE}
            return

        novo = Escravo()
        novo.ultimo_ciclo = 0
        self.escravos.append(novo)
        self.stats["escravos_total"] += 1
        self.log_add(f"[DOAÇÃO] {novo.nome} foi doado a você!", GREEN)
        self.notificacao = {"titulo": "Doação!", "msg": f"{novo.nome} foi entregue como pagamento de dívida.", "cor": GREEN}

    def _ev_epidemia(self):
        # Na nova mecânica, epidemia causa doença em todos
        for e in self.escravos_vivos:
            e.doente       = True
            e.doenca_timer = self.rules["disease_duration"] * 0.5  # duração reduzida por evento
            # Também drena stamina
            dano_stam = random.randint(20, 50)
            e.stamina = max(1.0, e.stamina - dano_stam)
        self.log_add("[EPIDEMIA] Uma doença varreu a mina! Todos adoeceram.", PURPLE)
        self.notificacao = {"titulo": "Epidemia!", "msg": "Todos os servos ficaram doentes.", "cor": PURPLE}

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
        self.notificacao = {"titulo": "Acidente!", "msg": f"Desabamento matou {len(mortos)} servo(s).", "cor": RED}

    def _ev_mercado(self):
        self.mercado_negro       = True
        self.mercado_negro_timer = self.rules["black_market_duration"]
        duracao = self.mercado_negro_timer
        self.log_add(f"[MERCADO] Mercado negro ativo por {duracao:.0f}s! Preços +50%.", CYAN)
        self.notificacao = {
            "titulo": "Mercado Negro!",
            "msg": f"Preços +50% por {duracao:.0f} segundos.",
            "cor": CYAN,
        }

    # ==============================================================
    # PRESTÍGIO
    # ==============================================================

    def pode_prestigiar(self):
        return self.stats["ouro_total"] >= self.rules["prestige_gold_req"]

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
        inv_itens_bkp = list(self.inventario_itens)

        self._init_state()

        self.stats           = stats_bkp
        self.conquistas      = conq_bkp
        self.prestigios      = prest_bkp
        self.almas_eternas   = almas_bkp
        self.bonus_prestigio = bonus_bkp
        self.ouro            = 100 + self.almas_eternas * 20
        self.primeiro_jogo   = False
        self.inventario_itens = inv_itens_bkp  # mantém itens entre prestígios

        self.log_add(f"[PRESTÍGIO #{self.prestigios}] Bônus global: {self.bonus_prestigio:.1f}x!", GOLD)
        return True, f"Prestígio #{self.prestigios} realizado!"

    def reset_progress(self):
        delete_save_files()
        self.storage.close()
        self.storage = SQLiteStorage(get_save_path())
        self.rules = load_rules()
        Escravo._id_counter = 0
        self._init_state()
        self.log_add("[SISTEMA] Progresso resetado.", ORANGE)
        self.save()
        return True, "Progresso resetado."

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

    def get_escravo_qualquer(self, eid) -> Escravo | None:
        """Busca em escravos e aposentados."""
        e = self.get_escravo(eid)
        if e:
            return e
        return self._get_aposentado(eid)

    def get_oferta_loja(self, offer_id: int) -> dict | None:
        for oferta in self.loja:
            if oferta["id"] == offer_id:
                return oferta
        return None

    def adjust_ui_config(self, key: str, delta: float):
        if key not in self.ui_config:
            return False

        limites = {
            "ui_scale": (0.85, 1.50),
            "sidebar_factor": (0.70, 1.60),
            "mine_factor": (0.75, 1.60),
            "center_factor": (0.75, 1.70),
            "right_factor": (0.70, 1.60),
            "bottom_factor": (0.75, 1.60),
        }
        atual = self.ui_config[key]
        minimo, maximo = limites[key]
        novo = max(minimo, min(maximo, round(atual + delta, 2)))
        self.ui_config[key] = novo
        return True

    def reset_ui_config(self):
        self.ui_config = self._default_ui_config()

    def log_add(self, msg: str, cor=WHITE):
        self.log.insert(0, {"msg": msg, "cor": cor})
        if len(self.log) > 120:
            self.log = self.log[:120]

    def close(self):
        self.storage.close()

    # ==============================================================
    # SAVE / LOAD
    # ==============================================================

    def _serialize_state(self):
        agora = time.time()
        return {
            "version": "2.0",
            "ouro": self.ouro,
            "inventario": self.inventario,
            "inventario_itens": self.inventario_itens,
            "nivel_mina": self.nivel_mina,
            "upgrades": self.upgrades,
            "loja": [
                {
                    "id": oferta["id"],
                    "servo": oferta["servo"].to_dict(),
                    "ttl_remaining": max(0.0, oferta["expires_at"] - agora),
                    "duration": oferta["duration"],
                    "age_elapsed": max(0.0, agora - oferta["created_at"]),
                }
                for oferta in self.loja
            ],
            "shop_offer_id": self._shop_offer_id,
            "ui_config": self.ui_config,
            "escravos": [e.to_dict() for e in self.escravos if e.vivo],
            "aposentados": [e.to_dict() for e in self.aposentados],
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

    def _apply_loaded_state(self, d):
        self.ouro            = d.get("ouro", 100.0)
        self.inventario      = d.get("inventario", {r: 0 for r in RESOURCE_ORDER})
        self.inventario_itens = d.get("inventario_itens", [])
        self.nivel_mina      = d.get("nivel_mina", 0)
        self.upgrades        = d.get("upgrades", {k: 0 for k in UPGRADE_ORDER})
        self.prestigios      = d.get("prestigios", 0)
        self.almas_eternas   = d.get("almas_eternas", 0)
        self.bonus_prestigio = d.get("bonus_prestigio", 1.0)
        self.tempo_jogo      = d.get("tempo_jogo", 0.0)
        self.velocidade      = d.get("velocidade", 1)
        self.custo_refresco  = d.get("custo_refresco", 50)
        self.primeiro_jogo   = d.get("primeiro_jogo", True)
        self.ui_config       = self._default_ui_config()
        self.ui_config.update(d.get("ui_config", {}))

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
        self.aposentados = [Escravo.from_dict(ed) for ed in d.get("aposentados", [])]
        self.pares = [tuple(p) for p in d.get("pares", [])]
        agora = time.time()
        self.loja = []
        for oferta in d.get("loja", []):
            try:
                ttl_remaining = max(0.0, float(oferta.get("ttl_remaining", self.rules["shop_refresh_time"])))
                duration = float(oferta.get("duration", self.rules["shop_refresh_time"]))
                age_elapsed = max(0.0, float(oferta.get("age_elapsed", 0.0)))
                self.loja.append({
                    "id": int(oferta.get("id", self._shop_offer_id)),
                    "servo": Escravo.from_dict(oferta["servo"]),
                    "duration": duration,
                    "created_at": agora - age_elapsed,
                    "expires_at": agora + ttl_remaining,
                })
            except Exception:
                continue

        self._shop_offer_id = int(d.get("shop_offer_id", self._shop_offer_id))
        if self.loja:
            self._shop_offer_id = max(self._shop_offer_id, max(oferta["id"] for oferta in self.loja) + 1)
        else:
            self._gerar_loja(forcar=True)

    def save(self):
        try:
            return self.storage.save_game_state(self._serialize_state())
        except Exception as ex:
            print(f"Erro ao salvar: {ex}")
            return False

    def load(self):
        try:
            data = self.storage.load_game_state()
            if data is None:
                for legacy_path in iter_legacy_save_paths():
                    if not legacy_path.exists():
                        continue
                    with legacy_path.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                    self.storage.save_game_state(data, action="legacy_import")
                    break

            if data is None:
                return False

            self._apply_loaded_state(data)
            self.log_add("Jogo carregado com sucesso!", GREEN)
            return True
        except Exception as ex:
            print(f"Erro ao carregar: {ex}")
            self.log_add(f"Erro ao carregar: {ex}", RED)
            return False
