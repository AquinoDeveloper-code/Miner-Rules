from __future__ import annotations
# ============================================================
# slave.py — Classe Escravo
# ============================================================

import random
import uuid
from src.contexts.shared.constants import (
    RESOURCES, RESOURCE_ORDER, ATTR_RARITIES,
    BASE_SLAVE_PRICE, MALE_NAMES, FEMALE_NAMES,
    RARITY_COLORS,
    SLOTS, ITEMS,
    SLAVE_AGING_RATE, MAX_AGE,
    STAMINA_DRAIN_BASE, STAMINA_REGEN_RATE,
)


class Escravo:
    """
    Representa um escravo trabalhando na mina.

    Atributos base (1-100):
        forca       → quantidade de recursos por ciclo
        velocidade  → usada pelo sistema de ventilação (bônus extra futuro)
        resistencia → resistência ao desgaste físico e dreno de stamina
        fertilidade → chance de gerar filhos
        sorte       → favorece recursos mais raros
        lealdade    → reduz rebelião e fuga

    Novos sistemas:
        stamina     → barra 0-100%; drena ao minerar, regenera com tempo/comida
        idade       → float que aumenta com SLAVE_AGING_RATE; penaliza performance
        equipamentos→ dict slot → item_id ou None
        maldicoes   → dict slot → segundos restantes de maldição
        doente      → bool; reduz regen, acelera aging, risco de morte
        qualidade_comida → "basica" ou "qualidade"
        sem_comida  → flag setada pelo GameManager quando não há ouro para comida
        aposentado  → bool; aposentados são removidos da mina mas continuam existindo
    """

    _id_counter = 0  # Contador global de IDs; atualizado no from_dict

    # ------------------------------------------------------------------
    # Criação
    # ------------------------------------------------------------------

    def __init__(self, genero=None, pai=None, mae=None, lendario=False, comum=False):
        Escravo._id_counter += 1
        self.id  = Escravo._id_counter
        self.uid = str(uuid.uuid4())[:8]

        # Gênero
        self.genero = genero if genero in ("M", "F") else random.choice(("M", "F"))

        # Nome
        pool = MALE_NAMES if self.genero == "M" else FEMALE_NAMES
        self.nome = random.choice(pool) + f"#{self.id}"

        # Idade como float (avança com o tempo de jogo)
        self.idade = float(random.randint(16, 45))

        # Atributos
        if pai and mae:
            self._herdar(pai, mae)
        elif comum:
            self._gerar_comum()
        elif lendario:
            self._gerar_lendario()
        else:
            self._gerar_aleatorio()

        # Vida (mantida para compatibilidade; stamina é o novo sistema principal)
        self.vida_max = self._calc_vida_max()
        self.vida     = self.vida_max
        self.vivo     = True

        # Stamina (0-100%)
        self.stamina = 100.0

        # Equipamentos e maldições
        self.equipamentos = {slot: None for slot in SLOTS}
        self.maldicoes    = {slot: 0.0  for slot in SLOTS}

        # Doença
        self.doente       = False
        self.doenca_timer = 0.0

        # Alimentação
        self.qualidade_comida = "basica"
        self.sem_comida       = False

        # Status adicionais
        self.em_repouso       = False
        self.efeito_aura      = False
        self.aura_timer       = 0.0
        self.cor_aura         = (255, 255, 255)

        # Aposentadoria
        self.aposentado = False

        # Estado de crescimento (bebê)
        self.eh_bebe           = False
        self.tempo_crescimento = 0.0   # segundos de jogo restantes para crescer

        # Trabalho
        self.minerando          = True
        self.ultimo_ciclo       = -999.0   # tempo_jogo da última mineração
        self.tempo_na_mina      = 0.0      # segundos de jogo acumulados

        # Estatísticas individuais
        self.rec_encontrados = {r: 0 for r in RESOURCE_ORDER}
        self.valor_total     = 0

        # Reprodução
        self.par_id              = None   # ID do parceiro atual
        self.ultimo_filho        = -999.0 # tempo_jogo do último filho
        self.breed_cooldown      = 0.0    # cooldown pós-reprodução (2 anos = 100s)
        self.par_honeymoon       = 0.0    # tempo de lua de mel (9 meses = 37.5s)

        # Causa da morte (para log)
        self.causa_morte = None

        # Animação — frame de picareta (0-59), posição dentro do painel da mina
        self.anim_frame = random.randint(0, 59)
        self.anim_x     = 0
        self.anim_y     = 0

    # ------------------------------------------------------------------
    # Geração de atributos
    # ------------------------------------------------------------------

    @staticmethod
    def _rolar():
        """Rola um atributo com distribuição ponderada (maioria comum)."""
        r = random.random()
        if   r < 0.01: return random.randint(95, 100)  # 1 % lendário
        elif r < 0.08: return random.randint(80,  94)  # 7 % épico
        elif r < 0.25: return random.randint(60,  79)  # 17% raro
        elif r < 0.55: return random.randint(40,  59)  # 30% incomum
        else:          return random.randint(1,   39)  # 45% comum

    def _gerar_aleatorio(self):
        self.forca      = self._rolar()
        self.velocidade = self._rolar()
        self.resistencia= self._rolar()
        self.fertilidade= self._rolar()
        self.sorte      = self._rolar()
        self.lealdade   = self._rolar()

    def _gerar_comum(self):
        for attr in ("forca", "velocidade", "resistencia", "fertilidade", "sorte", "lealdade"):
            setattr(self, attr, random.randint(1, 39))

    def _gerar_lendario(self):
        for attr in ("forca","velocidade","resistencia","fertilidade","sorte","lealdade"):
            setattr(self, attr, random.randint(85, 100))

    def _herdar(self, pai, mae):
        """Média dos pais ± mutação; chance de 5% de mutação positiva."""
        def _h(a, b):
            media = (a + b) / 2
            mut   = random.randint(-10, 10)
            return max(1, min(100, int(media + mut)))

        self.forca       = _h(pai.forca,       mae.forca)
        self.velocidade  = _h(pai.velocidade,  mae.velocidade)
        self.resistencia = _h(pai.resistencia, mae.resistencia)
        self.fertilidade = _h(pai.fertilidade, mae.fertilidade)
        self.sorte       = _h(pai.sorte,       mae.sorte)
        self.lealdade    = _h(pai.lealdade,    mae.lealdade)

        # Mutação positiva rara (5%)
        if random.random() < 0.05:
            attr  = random.choice(["forca","velocidade","resistencia","fertilidade","sorte","lealdade"])
            bonus = random.randint(10, 25)
            setattr(self, attr, min(100, getattr(self, attr) + bonus))

    # ------------------------------------------------------------------
    # Propriedades calculadas
    # ------------------------------------------------------------------

    def _calc_vida_max(self):
        """Resistência e juventude aumentam a vida máxima."""
        base = 100 + self.resistencia * 2
        if self.idade > 35:
            base -= (self.idade - 35) * 3
        return max(50, base)

    def calcular_preco(self, mercado_negro=False, bonus_nivel_mina=0):
        """Preço de venda/compra baseado nos atributos."""
        soma = (
            self.forca       * 1.2 +
            self.velocidade  * 1.0 +
            self.resistencia * 0.8 +
            self.fertilidade * 0.6 +
            self.sorte       * 0.9 +
            self.lealdade    * 0.5
        ) / 6

        # Multiplicador de raridade
        for _, vmin, vmax, mult in ATTR_RARITIES:
            if vmin <= soma <= vmax:
                raridade_mult = mult
                break
        else:
            raridade_mult = 0.7

        # Multiplicador de idade
        if   self.idade < 20: idade_mult = 0.8
        elif self.idade < 30: idade_mult = 1.2
        elif self.idade < 40: idade_mult = 1.0
        else:                 idade_mult = 0.7

        # Penalidade de saúde (stamina)
        stam_mult = 0.5 + (self.stamina / 100) * 0.5

        qualidade_mult = max(0.30, soma / 55.0)
        preco = BASE_SLAVE_PRICE * qualidade_mult * raridade_mult * idade_mult * stam_mult
        preco *= 1.0 + max(0, bonus_nivel_mina) * 0.10
        if mercado_negro:
            preco *= 1.5
        preco = int(preco)
        return max(10, preco)

    def raridade_attr(self, valor):
        """Retorna o nome da raridade de um valor de atributo."""
        for nome, vmin, vmax, _ in ATTR_RARITIES:
            if vmin <= valor <= vmax:
                return nome
        return "comum"

    def raridade_geral(self):
        """Raridade geral baseada na média dos atributos."""
        media = (self.forca + self.velocidade + self.resistencia +
                 self.fertilidade + self.sorte + self.lealdade) / 6
        return self.raridade_attr(int(media))

    def cor_raridade(self):
        return RARITY_COLORS.get(self.raridade_geral(), (200, 200, 200))

    # ------------------------------------------------------------------
    # Sistema de idade e performance
    # ------------------------------------------------------------------

    def mult_idade(self):
        """
        Multiplicador de performance baseado na idade.
        Jovens são medianos; 20-35 é o pico; acima de 35 começa a degradar.
        """
        idade = self.idade
        if   idade < 16:  return 0.6
        elif idade < 20:  return 0.8
        elif idade < 35:  return 1.0
        elif idade < 45:  return 0.85
        elif idade < 55:  return 0.70
        elif idade < 65:  return 0.55
        else:             return 0.40

    # ------------------------------------------------------------------
    # Sistema de equipamentos
    # ------------------------------------------------------------------

    def status_humor(self) -> str:
        if self.doente:
            return "Doente"
        if self.sem_comida:
            return "Faminto"
        if self.tem_maldicao_ativa():
            return "Amaldiçoado"
        if self.stamina < 20:
            return "Muito Cansado"
        if self.stamina < 50:
            return "Cansado"
        if self.par_honeymoon > 0:
            return "Muito Feliz"
        if self.qualidade_comida == "qualidade":
            return "Satisfeito"
        return "Normal"

    def _item_em_slot(self, slot):
        """Retorna o dict ITEMS do item equipado no slot, ou None."""
        item_id = self.equipamentos.get(slot)
        if item_id and item_id in ITEMS:
            return ITEMS[item_id]
        return None

    def bonus_equip(self, attr: str) -> int:
        """Soma dos bônus de todos os equipamentos para um atributo base."""
        total = 0
        for slot in SLOTS:
            item = self._item_em_slot(slot)
            if item:
                total += item["bonus"].get(attr, 0)
        return total

    def bonus_mineracao_equip(self) -> float:
        """Multiplicador de mineração da picareta equipada."""
        item = self._item_em_slot("picareta")
        if item:
            return item["bonus"].get("mineracao_mult", 1.0)
        return 1.0

    def bonus_raridade_equip(self) -> float:
        """Multiplicador de raridade da picareta equipada."""
        item = self._item_em_slot("picareta")
        if item:
            return item["bonus"].get("raridade_mult", 1.0)
        return 1.0

    def tem_maldicao_ativa(self) -> bool:
        """True se qualquer slot tiver maldição com timer > 0."""
        return any(t > 0.0 for t in self.maldicoes.values())

    # ------------------------------------------------------------------
    # Atributos efetivos (base + equipamento + idade)
    # ------------------------------------------------------------------

    def _aplica_status_mult(self, base: int) -> int:
        humor = self.status_humor()
        mult = 1.0
        if humor in ("Doente", "Faminto", "Amaldiçoado"):
            mult = 0.8
        elif humor == "Muito Cansado":
            mult = 0.85
        elif humor == "Muito Feliz":
            mult = 1.2
        elif humor == "Satisfeito":
            mult = 1.1
            
        val = int(base * mult)
        return val if val > 0 else 1

    def forca_efetiva(self) -> int:
        val = max(1, int((self.forca + self.bonus_equip("forca")) * self.mult_idade()))
        return self._aplica_status_mult(val)

    def velocidade_efetiva(self) -> int:
        val = max(1, int((self.velocidade + self.bonus_equip("velocidade")) * self.mult_idade()))
        return self._aplica_status_mult(val)

    def resistencia_efetiva(self) -> int:
        val = max(1, int((self.resistencia + self.bonus_equip("resistencia")) * self.mult_idade()))
        return self._aplica_status_mult(val)

    def fertilidade_efetiva(self) -> int:
        val = max(1, int((self.fertilidade + self.bonus_equip("fertilidade")) * self.mult_idade()))
        return self._aplica_status_mult(int(val * 1.3) if self.par_honeymoon > 0 else val)

    def sorte_efetiva(self) -> int:
        val = max(1, int((self.sorte + self.bonus_equip("sorte")) * self.mult_idade()))
        return self._aplica_status_mult(val)

    def lealdade_efetiva(self) -> int:
        val = max(1, int((self.lealdade + self.bonus_equip("lealdade")) * self.mult_idade()))
        return self._aplica_status_mult(val)

    # ------------------------------------------------------------------
    # Sistema de stamina
    # ------------------------------------------------------------------

    def stamina_drain_mult(self) -> float:
        """Quanto mais resistente, menos stamina drena por ciclo."""
        return max(0.3, 1.0 - (self.resistencia_efetiva() / 200.0))

    def stamina_regen_rate(self) -> float:
        """
        Taxa de regen de stamina por segundo de jogo.
        Base + bônus de resistência + bônus de comida + penalidade de doença.
        """
        base = STAMINA_REGEN_RATE
        # Resistência contribui positivamente
        base += self.resistencia_efetiva() * 0.002
        # Comida boa acelera regen
        if self.qualidade_comida == "qualidade":
            base *= 1.6
        elif self.sem_comida:
            base *= 0.3
        # Doença reduz regen
        if self.doente:
            base *= 0.4
        return max(0.02, base)

    def eficiencia_stamina(self) -> float:
        """
        Eficiência de trabalho baseada na stamina atual.
        Abaixo de 30% começa a penalizar severamente.
        """
        if self.stamina >= 60:
            return 1.0
        elif self.stamina >= 30:
            return 0.7
        elif self.stamina >= 10:
            return 0.45
        else:
            return 0.20

    # ------------------------------------------------------------------
    # Update por frame
    # ------------------------------------------------------------------

    def update(self, delta, desgaste_mult=1.0):
        """
        Chamado a cada frame com delta de tempo de jogo.
        desgaste_mult: parâmetro mantido para compatibilidade (alimentação).
        Retorna True se o escravo morreu neste frame.
        """
        if not self.vivo:
            return False

        # Bebê — só cresce
        if self.eh_bebe:
            self.tempo_crescimento -= delta
            if self.tempo_crescimento <= 0:
                self.eh_bebe   = False
                self.minerando = True
            return False

        # Acumula tempo na mina
        if not self.em_repouso:
            self.tempo_na_mina += delta

        # Aura
        if self.efeito_aura:
            self.aura_timer -= delta
            if self.aura_timer <= 0:
                self.efeito_aura = False
                
        # Cooldowns familiares
        if self.breed_cooldown > 0:
            self.breed_cooldown -= delta
        if self.par_honeymoon > 0:
            self.par_honeymoon -= delta

        # Envelhecimento
        taxa_aging = SLAVE_AGING_RATE
        if self.doente:
            taxa_aging *= 1.5
        if self.sem_comida:
            taxa_aging *= 1.3
        self.idade += taxa_aging * delta

        # Morte por velhice
        if self.idade >= MAX_AGE:
            self.vivo        = False
            self.causa_morte = self.causa_morte or "Velhice"
            return True

        # Regen de stamina
        self.stamina = min(100.0, self.stamina + self.stamina_regen_rate() * delta)
        
        # Volta ao trabalho automaticamente se estiver 100%
        if self.em_repouso and self.stamina >= 100.0:
            self.em_repouso = False

        # Timers de maldição (decrementam)
        for slot in SLOTS:
            if self.maldicoes[slot] > 0:
                self.maldicoes[slot] = max(0.0, self.maldicoes[slot] - delta)

        # Timer de doença
        if self.doente:
            self.doenca_timer -= delta
            # Morte por doença grave (stamina zerada + doente prolongado)
            if self.doenca_timer <= 0 and self.stamina < 5:
                self.vivo        = False
                self.causa_morte = "Doença"
                return True

        # Animação
        self.anim_frame = (self.anim_frame + delta * 12) % 60
        return False

    # ------------------------------------------------------------------
    # Mineração
    # ------------------------------------------------------------------

    def pode_minerar(self, tempo_jogo, intervalo):
        """True se já passou o intervalo desde o último ciclo e não está em repouso."""
        return (self.vivo and self.minerando and not self.eh_bebe and
                not self.aposentado and not self.em_repouso and
                (tempo_jogo - self.ultimo_ciclo) >= intervalo)

    def executar_mineracao(self, tempo_jogo, mult_raridade=1.0,
                           mult_recursos=1.0, mult_sorte=1.0):
        """
        Executa um ciclo de mineração.
        Aplica penalidade de stamina, idade e bônus de equipamento.
        Retorna (recurso_nome, quantidade, valor_total).
        """
        self.ultimo_ciclo = tempo_jogo

        # Drena stamina
        dreno = STAMINA_DRAIN_BASE * self.stamina_drain_mult()
        self.stamina = max(0.0, self.stamina - dreno)
        
        if self.stamina <= 0:
            self.stamina = 0.0
            self.em_repouso = True

        # Eficiência combinada: stamina + idade
        efic = self.eficiencia_stamina() * self.mult_idade()

        # Quantidade base (força efetiva + equipamento picareta)
        forca_ef = self.forca_efetiva()
        qtd_base = 1 + forca_ef // 30
        qtd_raw  = random.randint(qtd_base, qtd_base + 2)
        qtd_raw  = int(qtd_raw * mult_recursos * self.bonus_mineracao_equip())
        qtd      = max(1, int(qtd_raw * efic))

        # Escolha de recurso com bônus de picareta e sorte efetiva
        sorte_ef     = (self.sorte_efetiva() / 100) * mult_sorte
        mult_rar_tot = mult_raridade * self.bonus_raridade_equip()
        recurso      = self._escolher_recurso(sorte_ef, mult_rar_tot)

        # Registra
        self.rec_encontrados[recurso] = self.rec_encontrados.get(recurso, 0) + qtd
        valor = RESOURCES[recurso]["valor"] * qtd
        self.valor_total += valor

        return recurso, qtd, valor

    def _escolher_recurso(self, sorte_ef, mult_raridade):
        """Sorte aumenta probabilidade de recursos raros."""
        probs = []
        for nome in RESOURCE_ORDER:
            p = RESOURCES[nome]["raridade"]
            if p < 0.10:   # raro
                p = p * (1 + sorte_ef * 2) * mult_raridade
            elif p > 0.30: # comum
                p = p * max(0.3, 1 - sorte_ef * 0.5)
            else:
                p = p * mult_raridade
            probs.append(max(0.001, p))

        total = sum(probs)
        probs = [x / total for x in probs]

        r = random.random()
        acc = 0.0
        for i, nome in enumerate(RESOURCE_ORDER):
            acc += probs[i]
            if r <= acc:
                return nome
        return RESOURCE_ORDER[0]

    # ------------------------------------------------------------------
    # Serialização
    # ------------------------------------------------------------------

    def to_dict(self):
        return {
            "id": self.id, "uid": self.uid,
            "nome": self.nome, "genero": self.genero, "idade": self.idade,
            "forca": self.forca, "velocidade": self.velocidade,
            "resistencia": self.resistencia, "fertilidade": self.fertilidade,
            "sorte": self.sorte, "lealdade": self.lealdade,
            "vida": self.vida, "vida_max": self.vida_max, "vivo": self.vivo,
            "stamina": self.stamina,
            "equipamentos": self.equipamentos,
            "maldicoes": self.maldicoes,
            "doente": self.doente,
            "doenca_timer": self.doenca_timer,
            "qualidade_comida": self.qualidade_comida,
            "sem_comida": self.sem_comida,
            "aposentado": self.aposentado,
            "em_repouso": self.em_repouso,
            "efeito_aura": self.efeito_aura,
            "aura_timer": self.aura_timer,
            "cor_aura": self.cor_aura,
            "breed_cooldown": self.breed_cooldown,
            "par_honeymoon": self.par_honeymoon,
            "eh_bebe": self.eh_bebe, "tempo_crescimento": self.tempo_crescimento,
            "minerando": self.minerando, "ultimo_ciclo": self.ultimo_ciclo,
            "tempo_na_mina": self.tempo_na_mina,
            "rec_encontrados": self.rec_encontrados, "valor_total": self.valor_total,
            "par_id": self.par_id, "ultimo_filho": self.ultimo_filho,
            "causa_morte": self.causa_morte,
            "anim_frame": self.anim_frame, "anim_x": self.anim_x, "anim_y": self.anim_y,
        }

    @classmethod
    def from_dict(cls, d):
        e = cls.__new__(cls)
        e.id = d["id"]; e.uid = d["uid"]
        e.nome = d["nome"]; e.genero = d["genero"]; e.idade = float(d.get("idade", 25))
        e.forca = d["forca"]; e.velocidade = d["velocidade"]
        e.resistencia = d["resistencia"]; e.fertilidade = d["fertilidade"]
        e.sorte = d["sorte"]; e.lealdade = d["lealdade"]
        e.vida = d["vida"]; e.vida_max = d["vida_max"]; e.vivo = d["vivo"]
        # Novos campos com fallback para saves antigos
        e.stamina          = d.get("stamina", 100.0)
        e.equipamentos     = d.get("equipamentos", {slot: None for slot in SLOTS})
        e.maldicoes        = d.get("maldicoes",    {slot: 0.0  for slot in SLOTS})
        # Garante que todos os slots existem (compatibilidade)
        for slot in SLOTS:
            if slot not in e.equipamentos:
                e.equipamentos[slot] = None
            if slot not in e.maldicoes:
                e.maldicoes[slot] = 0.0
        e.doente           = d.get("doente", False)
        e.doenca_timer     = d.get("doenca_timer", 0.0)
        e.qualidade_comida = d.get("qualidade_comida", "basica")
        e.sem_comida       = d.get("sem_comida", False)
        e.aposentado       = d.get("aposentado", False)
        e.em_repouso       = d.get("em_repouso", False)
        e.efeito_aura      = d.get("efeito_aura", False)
        e.aura_timer       = d.get("aura_timer", 0.0)
        e.cor_aura         = tuple(d.get("cor_aura", (255, 255, 255)))
        e.breed_cooldown   = d.get("breed_cooldown", 0.0)
        e.par_honeymoon    = d.get("par_honeymoon", 0.0)
        e.eh_bebe = d["eh_bebe"]; e.tempo_crescimento = d["tempo_crescimento"]
        e.minerando = d["minerando"]; e.ultimo_ciclo = d.get("ultimo_ciclo", -999)
        e.tempo_na_mina = d.get("tempo_na_mina", 0)
        e.rec_encontrados = d.get("rec_encontrados", {r: 0 for r in RESOURCE_ORDER})
        e.valor_total = d.get("valor_total", 0)
        e.par_id = d.get("par_id"); e.ultimo_filho = d.get("ultimo_filho", -999)
        e.causa_morte = d.get("causa_morte")
        e.anim_frame = d.get("anim_frame", 0)
        e.anim_x = d.get("anim_x", 0); e.anim_y = d.get("anim_y", 0)
        if e.id >= Escravo._id_counter:
            Escravo._id_counter = e.id + 1
        return e
