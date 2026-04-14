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
from src.contexts.gameplay.domain.guard import Delivery, Guarda
from src.contexts.gameplay.domain.manager import Gerente
from src.contexts.gameplay.infrastructure.postgres_storage import PostgresStorage
from src.contexts.gameplay.infrastructure.db_worker import DBWorker
from src.contexts.shared.constants import (
    RESOURCES, RESOURCE_ORDER, MINE_UPGRADES, UPGRADE_ORDER,
    MINE_DEPTHS, RANDOM_EVENTS, ACHIEVEMENTS,
    PRESTIGE_BONUS_STEP,
    GREEN, RED, YELLOW, ORANGE, CYAN, GOLD, GRAY, PURPLE, WHITE,
    SLOTS, ITEMS, ITEM_DROP_CHANCES,
    RETIREMENT_AGE, MAX_AGE,
    DELIVERY_BASE_TIME, DELIVERY_MIN_TIME, DELIVERY_ATTACK_RATE, DELIVERY_ATTACKS,
    MAX_GUARDAS, GUARD_SLOTS, GUARD_TIERS, GUARD_ITEMS,
    VENDOR_APPEAR_CHANCE, VENDOR_TIMER, VENDOR_ITEMS_COUNT, VENDOR_QUALITY_WEIGHTS,
    MANAGER_TIERS, MANAGER_AUTONOMIA, MAX_GERENTES, MAX_RECOMENDACOES,
)


class GameManager:
    """
    Gerencia todo o estado do jogo: escravos, recursos, upgrades,
    eventos, reprodução, conquistas, save/load e prestígio.
    Novos sistemas: alimentação, doença, equipamentos, aposentadoria.
    """

    SAVE_FILE = get_save_path()

    def __init__(self):
        self.storage = PostgresStorage()
        self.worker  = DBWorker(self.storage)
        self.player_id = None
        self.username = None
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

        # Inventário de itens (lista de dicionários para expiração)
        self.inventario_itens: list[dict] = [] 

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
        
        # Recomendação importante pendente (Pop-up do Gerente)
        self.rec_importante_pendente: dict | None = None

        # Mercado negro
        self.mercado_negro       = False
        self.mercado_negro_timer = 0.0

        # Log de eventos (lista de {"msg":str, "cor":tuple})
        self.log: list[dict] = []
        
        # Histórico timeline de eventos marcantes
        self.historico: list[tuple[float, str]] = []

        # Central de Notificações (Novo sistema de histórico persistente)
        self.notificacoes_history: list[dict] = []
        self._notif_id_counter = 0
        
        # Loja de Itens Equips/Consumiveis
        self.loja_itens: list[dict] = []
        self.loja_itens_timer = 0.0

        # Sistema de Guardas
        self.guardas: list[Guarda] = []
        self.inventario_guard_itens: list[dict] = []
        self.loja_guard_itens: list[dict] = []
        self.loja_guard_itens_timer = 0.0

        # Sistema de Entrega (Cofre)
        self.entregas: list[Delivery] = []
        self._last_agora_real: float = time.time()

        # Vendedor Ambulante
        self.vendedor_atual: dict | None = None

        # Sistema de Gerentes
        self.gerentes: list[Gerente] = []
        self.fila_recomendacoes: list[dict] = []
        self._t_gerentes: dict[int, float] = {}
        self.mortalidade_history: list[dict] = []

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

        self._sanitizar_inventario()

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
        maior_risco_base = max(depth["risco_morte"] for depth in MINE_DEPTHS)
        severidade_mina = min(1.0, self.risco_morte / max(0.0001, maior_risco_base))

        risco_minimo = 0.001 + severidade_mina * 0.009
        risco_maximo = 0.12 + severidade_mina * 0.58
        return min(0.70, max(risco_minimo, risco_minimo + (risco_maximo - risco_minimo) * progresso_idade))

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

        # Delta real (independente da velocidade)
        delta_real = agora_real - self._last_agora_real
        self._last_agora_real = agora_real
        delta_real = max(0.0, min(delta_real, 5.0))   # clamp anti-spike

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

        # Verificação de expiração de itens (2 minutos = 120s)
        self._verificar_expiracao_itens()

        # Loja de Itens (reseta a cada 5 min de jogo)
        self.loja_itens_timer += delta
        if self.loja_itens_timer >= 300.0:
            self.loja_itens_timer = 0.0
            self._gerar_loja_itens()

        # Loja de Itens de Guardas (5 min de jogo)
        self.loja_guard_itens_timer += delta
        if self.loja_guard_itens_timer >= 300.0:
            self.loja_guard_itens_timer = 0.0
            self._gerar_loja_guard_itens()

        # Sistema de Entrega (tempo real)
        if not self.pausado:
            self._update_deliveries(delta_real)

        # Vendedor (tempo real)
        if self.vendedor_atual:
            self.vendedor_atual["timer"] -= delta_real
            if self.vendedor_atual["timer"] <= 0 or not self.vendedor_atual["itens"]:
                if self.vendedor_atual["itens"]:
                    self.log_add("[VENDEDOR] O vendedor foi embora.", GRAY)
                self.vendedor_atual = None

        # Gerentes (tempo de jogo)
        if self.gerentes:
            self._update_gerentes(delta)

        # Autosave (tempo real)
        if agora_real - self._t_autosave >= self.rules["autosave_interval"]:
            self._t_autosave = agora_real
            self.save_async() # <--- Agora assíncrono
            self.log_add("[SISTEMA] Sincronização em nuvem iniciada...", GRAY)

        # Atualiza estatísticas
        n = len(self.escravos_vivos)
        if n > self.stats["max_simult"]:
            self.stats["max_simult"] = n

        # Verifica conquistas
        self._verificar_conquistas()

    # ==============================================================
    # MINERAÇÃO
    # ==============================================================

    def _calcular_delivery_time(self, escravo: Escravo) -> float:
        """Tempo de entrega em segundos reais: máx 15s, reduz com vel e nível da mina."""
        vel_bonus   = (escravo.velocidade_efetiva() / 100) * 8.0
        nivel_bonus = self.nivel_mina * 0.5
        return max(DELIVERY_MIN_TIME, DELIVERY_BASE_TIME - vel_bonus - nivel_bonus)

    def _calcular_ataque_chance(self) -> float:
        """Chance de ataque por check, reduzida por guardas e segurança."""
        base = DELIVERY_ATTACK_RATE
        seg_lvl = self.upgrades.get("seguranca", 0)
        seg_red = MINE_UPGRADES["seguranca"]["niveis"][seg_lvl]["red_morte"]
        base *= (1.0 - seg_red * 0.5)
        total_agi = sum(g.agilidade_efetiva() for g in self.guardas if g.ativo)
        guard_red = min(0.60, total_agi / 400.0)
        base *= (1.0 - guard_red)
        return max(0.005, base)

    def _calcular_recuperacao(self, tipo_ataque: str) -> float:
        """Chance de recuperar itens após ataque, aumentada pelos guardas."""
        base        = DELIVERY_ATTACKS[tipo_ataque]["recuperar"]
        total_forca = sum(g.forca_efetiva() for g in self.guardas if g.ativo)
        bonus       = min(0.35, total_forca / 300.0)
        return min(0.97, base + bonus)

    def _verificar_expiracao_itens(self):
        """Remove itens do inventário comum que passaram de 120s."""
        remanescentes = []
        removidos = 0
        now = self.tempo_jogo
        
        for it in self.inventario_itens:
            # Sanitização on-the-fly para evitar crash se vier string
            if isinstance(it, str):
                it = {"id": it, "added_at": now}
                
            if now - it.get("added_at", 0) <= 120.0:
                remanescentes.append(it)
            else:
                removidos += 1
        
        if removidos > 0:
            self.inventario_itens = remanescentes
            self.log_add(f"[SISTEMA] {removidos} item(ns) expiraram e foram descartados.", GRAY)

    def _sanitizar_inventario(self):
        """Garante que todos os itens nos inventários (servos e guardas) sejam dicionários."""
        now = self.tempo_jogo
        
        # 1. Inventário de servos
        new_inv = []
        for it in self.inventario_itens:
            if isinstance(it, str):
                new_inv.append({"id": it, "added_at": now})
            elif isinstance(it, dict) and "id" in it:
                if "added_at" not in it: it["added_at"] = now
                new_inv.append(it)
        self.inventario_itens = new_inv

        # 2. Inventário de guardas
        new_guard_inv = []
        for it in self.inventario_guard_itens:
            if isinstance(it, str):
                new_guard_inv.append({"id": it, "added_at": now})
            elif isinstance(it, dict) and "id" in it:
                if "added_at" not in it: it["added_at"] = now
                new_guard_inv.append(it)
        self.inventario_guard_itens = new_guard_inv

    def _update_deliveries(self, delta_real: float):
        """Atualiza entregas em trânsito. Chamado com delta de tempo real."""
        for delivery in list(self.entregas):
            if delivery.status != "transito":
                continue

            delivery.timer      -= delta_real
            delivery._atk_check -= delta_real

            # Verificação de ataque
            if delivery._atk_check <= 0:
                delivery._atk_check = 5.0
                if random.random() < self._calcular_ataque_chance():
                    # Sorteia tipo de ataque
                    tipos  = list(DELIVERY_ATTACKS.keys())
                    pesos  = [DELIVERY_ATTACKS[t]["chance"] for t in tipos]
                    total  = sum(pesos)
                    r      = random.random() * total
                    acc    = 0.0
                    tipo   = tipos[0]
                    for t, p in zip(tipos, pesos):
                        acc += p
                        if r <= acc:
                            tipo = t
                            break

                    ataque      = DELIVERY_ATTACKS[tipo]
                    chance_rec  = self._calcular_recuperacao(tipo)
                    recuperado  = random.random() < chance_rec

                    if recuperado:
                        self.log_add(
                            f"[ENTREGA] {delivery.escravo_nome} foi atacado por "
                            f"{ataque['nome']}! Guardas recuperaram a carga.", GREEN
                        )
                    else:
                        delivery.status     = "perdido"
                        delivery.ataque_nome = ataque["nome"]
                        delivery.ataque_cor  = ataque["cor"]
                        self.log_add(
                            f"[ENTREGA] {delivery.qtd}x {delivery.recurso} de "
                            f"{delivery.escravo_nome} ROUBADO por {ataque['nome']}!", RED
                        )
                        continue

            # Entrega concluída
            if delivery.timer <= 0 and delivery.status == "transito":
                delivery.status = "entregue"
                self.inventario[delivery.recurso] = (
                    self.inventario.get(delivery.recurso, 0) + delivery.qtd
                )
                self.stats["rec_qtd"][delivery.recurso] = (
                    self.stats["rec_qtd"].get(delivery.recurso, 0) + delivery.qtd
                )
                self.stats["recursos_enc"].add(delivery.recurso)

        # Mantém apenas transito + últimas 15 concluídas (para exibição)
        em_transito  = [d for d in self.entregas if d.status == "transito"]
        concluidas   = [d for d in self.entregas if d.status != "transito"][-15:]
        self.entregas = em_transito + concluidas

    def _ciclo_mineracao(self, escravo: Escravo):
        recurso, qtd, valor = escravo.executar_mineracao(
            self.tempo_jogo, self.mult_raridade, self.mult_recursos, self.mult_sorte
        )
        # Registra no stats imediatamente (para conquistas/display)
        self.stats["recursos_enc"].add(recurso)

        # Cria entrega em vez de adicionar ao inventário diretamente
        t_entrega = self._calcular_delivery_time(escravo)
        delivery  = Delivery(recurso, qtd, valor, escravo.nome, t_entrega)
        self.entregas.append(delivery)

        # Loga apenas recursos raros (p < 0.10) ou 10% dos comuns
        raro = RESOURCES[recurso]["raridade"] < 0.10
        if raro or random.random() < 0.10:
            cor = RESOURCES[recurso]["cor"]
            self.log_add(
                f"{escravo.nome} extraiu {qtd}x {recurso}! "
                f"(cofre em {t_entrega:.0f}s)", cor
            )

        # Verificação de drop de item
        for item_id, chance in ITEM_DROP_CHANCES.items():
            sorte_bonus = escravo.sorte_efetiva() / 1000
            if random.random() < chance + sorte_bonus:
                self.inventario_itens.append({"id": item_id, "added_at": self.tempo_jogo})
                idata = ITEMS[item_id]
                raridade = idata.get("raridade", "comum")
                # Só gera notificação relevante (Toast/Histórico) se for Raro ou superior
                urg = 2 if raridade in ["raro", "epico", "lendario"] else 1
                tp = "rare_item" if urg == 2 else "item"
                
                self.log_add(f"[ITEM] {escravo.nome} encontrou: {idata['nome']}!", PURPLE, tipo=tp, urgencia=urg)
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
                self.log_add(f"[DOENÇA] {escravo.nome} ficou doente!", RED, tipo="disease", urgencia=2)

    # ==============================================================
    # SISTEMA DE EQUIPAMENTOS
    # ==============================================================

    def equipar_item(self, escravo_id: int, item_id: str) -> tuple[bool, str]:
        """Move item do inventário do jogador para o slot do escravo."""
        item_data = next((it for it in self.inventario_itens if it["id"] == item_id), None)
        if not item_data:
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
            # Devolve ao inventário resetando o timer
            self.inventario_itens.append({"id": item_atual, "added_at": self.tempo_jogo})

        # Equipa
        escravo.equipamentos[slot] = item_id
        self.inventario_itens.remove(item_data)

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
        self.inventario_itens.append({"id": item_id, "added_at": self.tempo_jogo})
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
                
            for it_data in list(self.inventario_itens):
                iid = it_data["id"]
                if iid in ITEMS and ITEMS[iid]["slot"] == slot and not ITEMS[iid].get("consumivel"):
                    item_rank = ranks.get(ITEMS[iid].get("raridade", "comum"), 0)
                    if item_rank > best_rank:
                        best_rank = item_rank
                        best_item_id = iid
                        best_it_data = it_data
                        
            if best_item_id:
                if curr_id:
                    self.inventario_itens.append({"id": curr_id, "added_at": self.tempo_jogo})
                self.inventario_itens.remove(best_it_data)
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
        item_data = ITEMS[item_id]
        if not item_data.get("consumivel", False):
            return False, "Este item não é consumível."

        escravo = self.get_escravo(escravo_id)
        if not escravo:
            escravo = self._get_aposentado(escravo_id)
        if not escravo:
            return False, "Servo não encontrado."

        # Busca no inventário estruturado
        it_obj = next((it for it in self.inventario_itens if it["id"] == item_id), None)
        if not it_obj:
             return False, "Item não encontrado no inventário."

        efeito = item_data.get("efeito_consumivel")
        self.inventario_itens.remove(it_obj)

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
                self.inventario_itens.append({"id": item_id, "added_at": self.tempo_jogo})
                escravo.equipamentos[slot] = None
        
        self.mortalidade_history.append({
            "t": self.tempo_jogo, 
            "causa": causa,
            "nome": escravo.nome,
            "idade": escravo.idade
        })
        self.log_add(f"[MORTE] {escravo.nome} faleceu. Causa: {causa}", RED, tipo="death", urgencia=3)
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
            f"[NASCIMENTO] Nasceu {filho.nome}! Filho(a) de {mae.nome} e {pai.nome}",
            GREEN, tipo="birth", urgencia=2
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
                self.inventario_itens.append({"id": item_id, "added_at": self.tempo_jogo})
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
        self.inventario_itens.append({"id": item_id, "added_at": self.tempo_jogo})
        self.log_add(f"Comprado {ITEMS[item_id]['nome']} por {preco}g!", GOLD)
        
        return True, "Comprado com sucesso!"

    # ==============================================================
    # EVENTOS ALEATÓRIOS
    # ==============================================================

    def _tentar_evento(self):
        if not self.escravos_vivos or self.notificacao:
            return
        # Tenta aparecer vendedor
        self._tentar_vendedor()
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
        self.log_add(f"[REBELIÃO] {len(mortos)} servo(s) mortos. -{perda:.0f}g.", RED, tipo="event", urgencia=3)
        self.notificacao = {"titulo": "Rebelião!", "msg": f"{len(mortos)} servo(s) se revoltaram!", "cor": RED}

    def _ev_caverna(self):
        for r in ["Ouro", "Esmeralda", "Diamante"]:
            q = random.randint(5, 20)
            self.inventario[r] += q
            self.stats["rec_qtd"][r] += q
            self.stats["recursos_enc"].add(r)
        self.log_add("[CAVERNA] Uma caverna secreta foi encontrada! Recursos incríveis!", GOLD, tipo="event", urgencia=2)
        self.notificacao = {"titulo": "Caverna Secreta!", "msg": "Ouro, Esmeralda e Diamante encontrados!", "cor": GOLD}

    def _ev_fuga(self):
        vivos = self.escravos_vivos
        if not vivos:
            return
        fugitivo = min(vivos, key=lambda e: e.lealdade)
        self._on_morte(fugitivo, "Fuga")
        self.log_add(f"[FUGA] {fugitivo.nome} escapou!", ORANGE, tipo="event", urgencia=2)
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
        self.log_add("[EPIDEMIA] Uma doença varreu a mina! Todos adoeceram.", PURPLE, tipo="event", urgencia=3)
        self.notificacao = {"titulo": "Epidemia!", "msg": "Todos os servos ficaram doentes.", "cor": PURPLE}

    def _ev_mineral(self):
        q = random.randint(1, 3)
        self.inventario["Adamantita"] += q
        self.stats["rec_qtd"]["Adamantita"] += q
        self.stats["recursos_enc"].add("Adamantita")
        self.log_add(f"[LENDÁRIO] Veia de Adamantita! +{q}!", PURPLE, tipo="rare_item", urgencia=2)
        self.notificacao = {"titulo": "Veia Lendária!", "msg": f"+{q} Adamantita encontrada!", "cor": PURPLE}

    def _ev_acidente(self):
        vivos = self.escravos_vivos
        if not vivos:
            return
        n = max(1, len(vivos) // 10)
        mortos = random.sample(vivos, min(n, len(vivos)))
        for e in mortos:
            self._on_morte(e, "Acidente na mina")
        self.log_add(f"[ACIDENTE] Desabamento! {len(mortos)} morto(s).", RED, tipo="event", urgencia=3)
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
    # SISTEMA DE GERENTES
    # ==============================================================

    def contratar_gerente(self, tipo: str) -> tuple[bool, str]:
        tier = next((t for t in MANAGER_TIERS if t["tipo"] == tipo), None)
        if not tier:
            return False, "Tipo inválido."
        if len(self.gerentes) >= MAX_GERENTES:
            return False, f"Máximo de {MAX_GERENTES} gerentes."
        if self.ouro < tier["preco"]:
            return False, f"Precisa de {tier['preco']:,}g"
        self.ouro -= tier["preco"]
        g = Gerente(tipo=tipo)
        self.gerentes.append(g)
        self._t_gerentes[g.id] = g.check_interval
        self.log_add(f"[GERENTE] {g.nome} ({tier['nome']}) contratado!", GOLD)
        return True, "Gerente contratado!"

    def demitir_gerente(self, gerente_id: int) -> tuple[bool, str]:
        g = self.get_gerente(gerente_id)
        if not g:
            return False, "Gerente não encontrado."
        self.gerentes.remove(g)
        self._t_gerentes.pop(g.id, None)
        # Remove recomendações deste gerente da fila
        self.fila_recomendacoes = [
            r for r in self.fila_recomendacoes
            if r.get("gerente_id") != gerente_id
        ]
        self.log_add(f"[GERENTE] {g.nome} foi demitido.", ORANGE)
        return True, "Gerente demitido."

    def get_gerente(self, gerente_id: int) -> Gerente | None:
        for g in self.gerentes:
            if g.id == gerente_id:
                return g
        return None

    def set_autonomia_gerente(self, gerente_id: int, autonomia: str) -> tuple[bool, str]:
        g = self.get_gerente(gerente_id)
        if not g:
            return False, "Gerente não encontrado."
        if autonomia not in MANAGER_AUTONOMIA:
            return False, "Modo inválido."
        g.autonomia = autonomia
        self.log_add(f"[GERENTE] {g.nome} → modo {autonomia}.", CYAN)
        return True, "Modo alterado."

    def toggle_cfg_gerente(self, gerente_id: int, cfg_key: str) -> tuple[bool, str]:
        """Alterna um flag booleano de configuração do gerente."""
        g = self.get_gerente(gerente_id)
        if not g or not hasattr(g, cfg_key):
            return False, "Configuração inválida."
        setattr(g, cfg_key, not getattr(g, cfg_key))
        return True, "Configuração alterada."

    def _snapshot_estado(self) -> dict:
        """Cria snapshot do estado do jogo para os gerentes analisarem."""
        return {
            "ouro":               self.ouro,
            "escravos":           self.escravos_vivos,
            "loja":               self.loja,
            "guardas":            self.guardas,
            "nivel_mina":         self.nivel_mina,
            "mercado_negro":      self.mercado_negro,
            "inventario_itens":   self.inventario_itens,
            "inventario_guard":   self.inventario_guard_itens,
            "n_pares":            len(self.pares),
            "capacidade":         self.capacidade_servos,
        }

    def _update_gerentes(self, delta: float):
        """Tick de cada gerente; quando o timer bate, executa análise."""
        estado = None  # lazy — só computa uma vez se necessário
        for g in self.gerentes:
            t = self._t_gerentes.get(g.id, g.check_interval)
            t -= delta
            self._t_gerentes[g.id] = t
            if t > 0:
                continue

            # Reinicia timer
            self._t_gerentes[g.id] = g.check_interval

            # Snapshot lazy
            if estado is None:
                estado = self._snapshot_estado()

            recs = g.analisar(estado)
            if not recs:
                continue

            for rec in recs:
                rec["gerente_id"]   = g.id
                rec["gerente_nome"] = g.nome

                if g.autonomia in ("automatico", "semi", "recomendacao"):
                    # Se for menos relevante (Urgência 1 ou 2), o gerente executa sozinho
                    # em qualquer modo que permita recomendações, pois são "atividades triviais"
                    if rec["urgencia"] < 3:
                        executado = self._executar_acao_rec(rec)
                        if executado:
                            g.acoes_realizadas += 1
                            self.log_add(
                                f"[GERENTE] {g.nome} (auto): {rec['msg']}", 
                                rec.get("cor", GOLD), tipo="manager", urgencia=1
                            )
                        continue

                # Se chegamos aqui, é Urgência 3 (ou modo não tratou auto)
                if g.autonomia == "automatico":
                    executado = self._executar_acao_rec(rec)
                    if executado:
                        g.acoes_realizadas += 1
                        self.log_add(f"[GERENTE] {g.nome}: {rec['msg']}", rec.get("cor", GOLD), tipo="manager", urgencia=2)

                elif g.autonomia == "semi":
                    # Urgência 3+ em modo semi é auto? Sim, o usuário quer que as menores sejam auto,
                    # e em semi o que é urgente (3) era auto antes. Mantemos consistência.
                    executado = self._executar_acao_rec(rec)
                    if executado:
                        g.acoes_realizadas += 1
                        self.log_add(f"[GERENTE] {g.nome}: {rec['msg']}", rec.get("cor", GOLD), tipo="manager", urgencia=3)

                else:  # recomendacao
                    self._enfileirar_rec(rec)
                    if rec["urgencia"] >= 3:
                        self.rec_importante_pendente = rec

    def _enfileirar_rec(self, rec: dict):
        """Adiciona recomendação à fila, evitando duplicatas do mesmo tipo."""
        tipos_na_fila = {r["tipo"] for r in self.fila_recomendacoes}
        if rec["tipo"] not in tipos_na_fila:
            self.fila_recomendacoes.append(rec)
            # Mantém o máximo
            if len(self.fila_recomendacoes) > MAX_RECOMENDACOES:
                # Remove a mais antiga e de menor urgência
                self.fila_recomendacoes.sort(key=lambda r: r.get("urgencia", 1))
                self.fila_recomendacoes.pop(0)

    def _executar_acao_rec(self, rec: dict) -> bool:
        """Executa a ação indicada na recomendação. Retorna True se executou."""
        tipo  = rec.get("acao_tipo")
        param = rec.get("acao_param")
        if not tipo:
            return False
        try:
            if tipo == "vender_escravo":
                e = self.get_escravo(param)
                if e:
                    self.vender_escravo(e)
                    return True
            elif tipo == "aposentar_escravo":
                ok, _ = self.aposentar_escravo(param)
                return ok
            elif tipo == "curar_escravo":
                eid, iid = param
                ok, _ = self.usar_item_especial(eid, iid)
                return ok
            elif tipo == "usar_item_especial":
                eid, iid = param
                ok, _ = self.usar_item_especial(eid, iid)
                return ok
            elif tipo == "comprar_oferta_loja":
                ok, _ = self.comprar_oferta_loja(param)
                return ok
            elif tipo == "auto_equipar_todos":
                ok, _ = self.auto_equipar_melhores_todos()
                return ok
            elif tipo == "descanso_geral":
                for e in self.escravos_vivos:
                    if e.stamina < 20:
                        e.em_repouso = True
                return True
            elif tipo == "comprar_guarda":
                ok, _ = self.comprar_guarda(param)
                return ok
            elif tipo == "vender_tudo":
                total = self.vender_tudo()
                return total > 0
        except Exception:
            pass
        return False

    def executar_recomendacao(self, idx: int) -> tuple[bool, str]:
        """Chamado quando o jogador clica em 'Executar' em uma recomendação."""
        if idx >= len(self.fila_recomendacoes):
            return False, "Recomendação não encontrada."
        rec = self.fila_recomendacoes[idx]
        executado = self._executar_acao_rec(rec)
        if executado:
            g = self.get_gerente(rec.get("gerente_id", -1))
            if g:
                g.acoes_realizadas += 1
            self.fila_recomendacoes.pop(idx)
            return True, "Ação executada!"
        self.fila_recomendacoes.pop(idx)
        return False, "Não foi possível executar."

    def ignorar_recomendacao(self, idx: int):
        if 0 <= idx < len(self.fila_recomendacoes):
            self.fila_recomendacoes.pop(idx)

    # ==============================================================
    # VENDEDOR AMBULANTE
    # ==============================================================

    def _tentar_vendedor(self):
        """Tenta fazer um vendedor aparecer durante o evento."""
        if self.vendedor_atual:
            return
        if random.random() < VENDOR_APPEAR_CHANCE:
            self._gerar_vendedor()

    def _gerar_vendedor(self):
        """Gera um vendedor com 3 itens. Qualidade depende do sorteio."""
        qualidades = list(VENDOR_QUALITY_WEIGHTS.keys())
        pesos      = [VENDOR_QUALITY_WEIGHTS[q] for q in qualidades]
        total      = sum(pesos)
        r = random.random() * total
        acc = 0.0
        qualidade = qualidades[0]
        for q, p in zip(qualidades, pesos):
            acc += p
            if r <= acc:
                qualidade = q
                break

        filtro = {
            "barato":  (["comum", "incomum"], False, 0.60),
            "raro":    (["raro", "épico"],    False, 1.50),
            "ruim":    (["comum"],            False, 0.25),
            "maldito": (["épico","lendário"], True,  0.80),
        }
        rars_aceitas, apenas_maldito, mult_preco = filtro[qualidade]

        candidatos: list[tuple[str, dict, str]] = []
        for iid, data in ITEMS.items():
            if apenas_maldito and not data.get("maldito"):
                continue
            if data.get("raridade") in rars_aceitas:
                candidatos.append((iid, data, "slave"))
        for iid, data in GUARD_ITEMS.items():
            if data.get("raridade") in rars_aceitas:
                candidatos.append((iid, data, "guard"))

        if not candidatos:
            candidatos = [(iid, data, "slave") for iid, data in ITEMS.items()]

        random.shuffle(candidatos)
        itens_com_preco = []
        for iid, data, tipo in candidatos[:VENDOR_ITEMS_COUNT]:
            preco_base = data.get("preco", 50)
            if data.get("raridade") == "comum":    preco_base = max(preco_base, 80)
            elif data.get("raridade") == "incomum":preco_base = max(preco_base, 200)
            elif data.get("raridade") == "raro":   preco_base = max(preco_base, 600)
            elif data.get("raridade") == "épico":  preco_base = max(preco_base, 1500)
            elif data.get("raridade") == "lendário":preco_base = max(preco_base, 4000)
            itens_com_preco.append({
                "id":    iid,
                "preco": max(10, int(preco_base * mult_preco)),
                "tipo":  tipo,
                "nome":  data.get("nome", iid),
                "raridade": data.get("raridade", "comum"),
            })

        self.vendedor_atual = {
            "qualidade": qualidade,
            "itens":     itens_com_preco,
            "timer":     VENDOR_TIMER,
        }
        desc = {
            "barato": "Mercador de Bugigangas",
            "raro":   "Comerciante Raro",
            "ruim":   "Mascate Duvidoso",
            "maldito":"Vendedor das Sombras",
        }
        self.log_add(f"[VENDEDOR] {desc[qualidade]} apareceu! {VENDOR_TIMER:.0f}s.", GOLD)

    def comprar_item_vendedor(self, item_id: str, preco: int) -> tuple[bool, str]:
        if not self.vendedor_atual:
            return False, "Nenhum vendedor disponível."
        if self.ouro < preco:
            return False, f"Precisa de {preco}g"
        found = next(
            (it for it in self.vendedor_atual["itens"]
             if it["id"] == item_id and it["preco"] == preco),
            None,
        )
        if not found:
            return False, "Item não disponível."
        self.ouro -= preco
        self.vendedor_atual["itens"].remove(found)
        if found["tipo"] == "guard":
            self.inventario_guard_itens.append(item_id)
        else:
            self.inventario_itens.append({"id": item_id, "added_at": self.tempo_jogo})
        nome = found.get("nome", item_id)
        self.log_add(f"[VENDEDOR] Comprou '{nome}' por {preco}g!", GOLD)
        return True, "Comprado!"

    # ==============================================================
    # SISTEMA DE GUARDAS
    # ==============================================================

    def comprar_guarda(self, tipo: str) -> tuple[bool, str]:
        tier = next((t for t in GUARD_TIERS if t["tipo"] == tipo), None)
        if not tier:
            return False, "Tipo inválido."
        if len(self.guardas) >= MAX_GUARDAS:
            return False, f"Máximo de {MAX_GUARDAS} guardas."
        if self.ouro < tier["preco"]:
            return False, f"Precisa de {tier['preco']}g"
        self.ouro -= tier["preco"]
        g = Guarda(tipo=tipo)
        self.guardas.append(g)
        self.log_add(f"[GUARDA] {g.nome} ({tier['nome']}) contratado!", CYAN)
        return True, "Guarda contratado!"

    def demitir_guarda(self, guarda_id: int) -> tuple[bool, str]:
        g = self.get_guarda(guarda_id)
        if not g:
            return False, "Guarda não encontrado."
        for slot in GUARD_SLOTS:
            iid = g.equipamentos.get(slot)
            if iid:
                self.inventario_guard_itens.append(iid)
        self.guardas.remove(g)
        self.log_add(f"[GUARDA] {g.nome} foi dispensado.", ORANGE)
        return True, "Guarda dispensado."

    def equipar_item_guarda(self, guarda_id: int, item_id: str) -> tuple[bool, str]:
        # Busca o item no inventário de guardas (id string)
        it_obj = next((it for it in self.inventario_guard_itens if it["id"] == item_id), None)
        if not it_obj:
            return False, "Item não no inventário de guardas."
        
        if item_id not in GUARD_ITEMS:
            return False, "Item inválido para guardas."
        g = self.get_guarda(guarda_id)
        if not g:
            return False, "Guarda não encontrado."
            
        slot     = GUARD_ITEMS[item_id]["slot"]
        atual    = g.equipamentos.get(slot)
        if atual:
            self.inventario_guard_itens.append({"id": atual, "added_at": self.tempo_jogo})
        
        self.inventario_guard_itens.remove(it_obj)
        g.equipamentos[slot] = item_id
        nome = GUARD_ITEMS[item_id]["nome"]
        self.log_add(f"[GUARDA] {g.nome} equipou '{nome}'.", CYAN)
        return True, "Item equipado!"

    def desequipar_item_guarda(self, guarda_id: int, slot: str) -> tuple[bool, str]:
        g = self.get_guarda(guarda_id)
        if not g:
            return False, "Guarda não encontrado."
        iid = g.equipamentos.get(slot)
        if not iid:
            return False, "Slot vazio."
        g.equipamentos[slot] = None
        self.inventario_guard_itens.append(iid)
        nome = GUARD_ITEMS.get(iid, {}).get("nome", iid)
        self.log_add(f"[GUARDA] {g.nome} desequipou '{nome}'.", GRAY)
        return True, "Item removido!"

    def get_guarda(self, guarda_id: int) -> Guarda | None:
        for g in self.guardas:
            if g.id == guarda_id:
                return g
        return None

    def _gerar_loja_guard_itens(self):
        self.loja_guard_itens.clear()
        opcoes = list(GUARD_ITEMS.keys())
        random.shuffle(opcoes)
        for iid in opcoes[:5]:
            data = GUARD_ITEMS[iid]
            self.loja_guard_itens.append({
                "id":    iid,
                "preco": data["preco"] * 2,
            })
        self.log_add("[GUARDAS] Nova loja de equipamentos disponível!", CYAN)

    def comprar_item_guarda_loja(self, item_id: str, preco: int) -> tuple[bool, str]:
        if self.ouro < preco:
            return False, f"Precisa de {preco}g"
        found = next(
            (i for i, it in enumerate(self.loja_guard_itens)
             if it["id"] == item_id and it["preco"] == preco),
            None,
        )
        if found is None:
            return False, "Item não disponível."
        self.ouro -= preco
        self.loja_guard_itens.pop(found)
        self.inventario_guard_itens.append(item_id)
        nome = GUARD_ITEMS.get(item_id, {}).get("nome", item_id)
        self.log_add(f"Comprou '{nome}' para guardas por {preco}g!", GOLD)
        return True, "Comprado!"

    def auto_equipar_guarda(self, guarda_id: int) -> tuple[bool, str]:
        """Equipa os melhores itens disponíveis no inventário de guardas."""
        g = self.get_guarda(guarda_id)
        if not g:
            return False, "Guarda não encontrado."
        ranks = {"comum": 0, "incomum": 1, "raro": 2, "épico": 3, "lendário": 4}
        equipou = False
        for slot in GUARD_SLOTS:
            best_obj, best_rank = None, -1
            curr_id = g.equipamentos.get(slot)
            if curr_id and curr_id in GUARD_ITEMS:
                best_rank = ranks.get(GUARD_ITEMS[curr_id].get("raridade", "comum"), -1)
            
            for it_obj in list(self.inventario_guard_itens):
                iid = it_obj["id"] if isinstance(it_obj, dict) else it_obj
                if iid in GUARD_ITEMS and GUARD_ITEMS[iid]["slot"] == slot:
                    r = ranks.get(GUARD_ITEMS[iid].get("raridade", "comum"), 0)
                    if r > best_rank:
                        best_rank = r
                        best_obj  = it_obj
            
            if best_obj:
                if curr_id:
                    self.inventario_guard_itens.append({"id": curr_id, "added_at": self.tempo_jogo})
                self.inventario_guard_itens.remove(best_obj)
                g.equipamentos[slot] = best_obj["id"] if isinstance(best_obj, dict) else best_obj
                equipou = True
        if equipou:
            self.log_add(f"[GUARDA] {g.nome} equipado automaticamente!", GREEN)
            return True, "Equipado!"
        return False, "Nenhum item melhor encontrado."

    # Calcula o bônus coletivo de todos os guardas ativos
    def guardas_ataque_reducao(self) -> float:
        total_agi = sum(g.agilidade_efetiva() for g in self.guardas if g.ativo)
        return min(0.60, total_agi / 400.0)

    def guardas_recuperacao_bonus(self) -> float:
        total_forca = sum(g.forca_efetiva() for g in self.guardas if g.ativo)
        return min(0.35, total_forca / 300.0)

    def guardas_poder_total(self) -> int:
        return sum(g.poder_total() for g in self.guardas if g.ativo)

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
        inv_itens_bkp       = list(self.inventario_itens)
        guardas_bkp         = list(self.guardas)
        inv_guard_bkp       = list(self.inventario_guard_itens)
        gerentes_bkp        = list(self.gerentes)
        t_gerentes_bkp      = dict(self._t_gerentes)

        self._init_state()

        self.stats           = stats_bkp
        self.conquistas      = conq_bkp
        self.prestigios      = prest_bkp
        self.almas_eternas   = almas_bkp
        self.bonus_prestigio = bonus_bkp
        self.ouro            = 100 + self.almas_eternas * 20
        self.primeiro_jogo   = False
        self.inventario_itens        = inv_itens_bkp   # mantém itens entre prestígios
        self.guardas                 = guardas_bkp
        self.inventario_guard_itens  = inv_guard_bkp
        self.gerentes                = gerentes_bkp    # mantém gerentes entre prestígios
        self._t_gerentes             = t_gerentes_bkp

        self.log_add(f"[PRESTÍGIO #{self.prestigios}] Bônus global: {self.bonus_prestigio:.1f}x!", GOLD)
        return True, f"Prestígio #{self.prestigios} realizado!"

    def reset_progress(self):
        if self.player_id:
            self.storage.clear_game_state(self.player_id)
        
        self.rules = load_rules()
        Escravo._id_counter = 0
        self._init_state()
        self.log_add("[SISTEMA] Progresso resetado (Nuvem limpa).", ORANGE)
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

    def log_add(self, msg: str, cor=WHITE, tipo="info", urgencia=1):
        # 1. Sistema de log antigo (legado para compatibilidade visual imediata)
        self.log.insert(0, {"msg": msg, "cor": cor})
        if len(self.log) > 120:
            self.log = self.log[:120]

        # 2. Novo sistema de notificações estruturadas
        self._notif_id_counter += 1
        notif = {
            "id": self._notif_id_counter,
            "tipo": tipo,
            "msg": msg,
            "cor": cor,
            "tempo": self.tempo_jogo,
            "urgencia": urgencia,
            "lida": False
        }

        # FILTRO DE RELEVÂNCIA: Só entra no histórico/toasts se for importante
        relevante = (urgencia >= 2) or (tipo in ["death", "birth", "manager", "rare_item", "prestige", "event"])
        if relevante:
            self.notificacoes_history.insert(0, notif)
            if len(self.notificacoes_history) > 100:
                self.notificacoes_history = self.notificacoes_history[:100]

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
            "tempo_jogo": self.tempo_jogo,
            "notificacoes_history": self.notificacoes_history,
            "notif_id_counter": self._notif_id_counter,
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
            # Guardas
            "guardas": [g.to_dict() for g in self.guardas],
            "inventario_guard_itens": self.inventario_guard_itens,
            # Entregas em trânsito
            "entregas": [d.to_dict() for d in self.entregas if d.status == "transito"],
            # Gerentes
            "gerentes": [g.to_dict() for g in self.gerentes],
            "fila_recomendacoes": self.fila_recomendacoes,
            "t_gerentes": {str(k): v for k, v in self._t_gerentes.items()},
            "mortalidade_history": self.mortalidade_history,
            "inventario_itens": self.inventario_itens,
            "notificacoes_history": self.notificacoes_history,
            "notif_id_counter": self._notif_id_counter,
            "loja_itens_timer": self.loja_itens_timer,
            "loja_guard_itens_timer": self.loja_guard_itens_timer,
        }

    def _apply_loaded_state(self, d):
        self.ouro             = d.get("ouro", 100.0)
        self.tempo_jogo       = d.get("tempo_jogo", 0.0)
        self.notificacoes_history = d.get("notificacoes_history", [])
        self._notif_id_counter = d.get("notif_id_counter", 0)
        self.inventario       = d.get("inventario", {r: 0 for r in RESOURCE_ORDER})
        self.inventario_itens = d.get("inventario_itens", [])
        self.mortalidade_history = d.get("mortalidade_history", [])
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

        # Guardas
        self.guardas = [Guarda.from_dict(gd) for gd in d.get("guardas", [])]
        self.inventario_guard_itens = d.get("inventario_guard_itens", [])
        # Entregas salvas: entrega itens diretamente ao inventário (jogo fechado = entregue)
        for ed in d.get("entregas", []):
            try:
                deliv = Delivery.from_dict(ed)
                if deliv.status == "transito":
                    # completa imediatamente
                    self.inventario[deliv.recurso] = (
                        self.inventario.get(deliv.recurso, 0) + deliv.qtd
                    )
                    self.stats["rec_qtd"][deliv.recurso] = (
                        self.stats["rec_qtd"].get(deliv.recurso, 0) + deliv.qtd
                    )
                    self.stats["recursos_enc"].add(deliv.recurso)
            except Exception:
                continue
        self.entregas = []
        self._last_agora_real = time.time()

        # Gerentes
        self.gerentes = [Gerente.from_dict(gd) for gd in d.get("gerentes", [])]
        self.fila_recomendacoes = d.get("fila_recomendacoes", [])
        self._t_gerentes = {
            int(k): v for k, v in d.get("t_gerentes", {}).items()
        }
        # Garante timers para gerentes sem entrada
        for g in self.gerentes:
            if g.id not in self._t_gerentes:
                self._t_gerentes[g.id] = g.check_interval
        
        # Garante consistência de dados após carregar TUDO (especialmente itens de guarda)
        self._sanitizar_inventario()

    def save(self):
        """Versão bloqueante para salvamentos críticos (ex: ao fechar o jogo)."""
        try:
            if not self.player_id:
                return False
            return self.storage.save_game_state(
                self.player_id,
                self._serialize_state(),
                self.stats.get("ouro_total", 0.0),
                self.tempo_jogo
            )
        except Exception as ex:
            print(f"Erro ao salvar: {ex}")
            return False

    def save_async(self):
        """Versão assíncrona para não travar o FPS durante o jogo."""
        try:
            if not self.player_id:
                return False
            
            # Snapshots instantâneos para evitar inconsistências durante o upload
            state_data = self._serialize_state()
            money = float(self.stats.get("ouro_total", 0.0))
            time_played = float(self.tempo_jogo)
            
            self.worker.add_task("save", (self.player_id, state_data, money, time_played))
            return True
        except Exception as ex:
            print(f"Erro ao agendar save: {ex}")
            return False

    def load(self):
        try:
            if not self.player_id:
                return False
            data = self.storage.load_game_state(self.player_id)
            if data is None:
                for legacy_path in iter_legacy_save_paths():
                    if not legacy_path.exists():
                        continue
                    with legacy_path.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                    # Já faz o upload do save antigo pra nuvem
                    if data:
                        self._apply_loaded_state(data)
                        self.save()
                    break

            if data is None:
                return False

            self._apply_loaded_state(data)
            self.log_add("Jogo carregado com sucesso da nuvem!", GREEN)
            return True
        except Exception as ex:
            print(f"Erro ao carregar: {ex}")
            self.log_add(f"Erro ao carregar: {ex}", RED)
            return False
