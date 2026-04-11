# ============================================================
# slave.py — Classe Escravo
# ============================================================

import random
import uuid
from constants import (
    RESOURCES, RESOURCE_ORDER, ATTR_RARITIES,
    BASE_SLAVE_PRICE, MALE_NAMES, FEMALE_NAMES,
    RARITY_COLORS,
)


class Escravo:
    """
    Representa um escravo trabalhando na mina.

    Atributos base (1-100):
        forca       → quantidade de recursos por ciclo
        velocidade  → usada pelo sistema de ventilação (bônus extra futuro)
        resistencia → quanto tempo vive antes de morrer de exaustão
        fertilidade → chance de gerar filhos
        sorte       → favorece recursos mais raros
        lealdade    → reduz rebelião e fuga
    """

    _id_counter = 0  # Contador global de IDs; atualizado no from_dict

    # ------------------------------------------------------------------
    # Criação
    # ------------------------------------------------------------------

    def __init__(self, genero=None, pai=None, mae=None, lendario=False):
        Escravo._id_counter += 1
        self.id  = Escravo._id_counter
        self.uid = str(uuid.uuid4())[:8]

        # Gênero
        self.genero = genero if genero in ("M", "F") else random.choice(("M", "F"))

        # Nome
        pool = MALE_NAMES if self.genero == "M" else FEMALE_NAMES
        self.nome = random.choice(pool) + f"#{self.id}"

        # Idade (em anos de lore — não avança no tempo)
        self.idade = random.randint(16, 45)

        # Atributos
        if pai and mae:
            self._herdar(pai, mae)
        elif lendario:
            self._gerar_lendario()
        else:
            self._gerar_aleatorio()

        # Vida
        self.vida_max = self._calc_vida_max()
        self.vida     = self.vida_max
        self.vivo     = True

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

    def calcular_preco(self, mercado_negro=False):
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

        # Penalidade de saúde
        vida_mult = 0.5 + (self.vida / self.vida_max) * 0.5

        preco = int(BASE_SLAVE_PRICE + soma * raridade_mult * idade_mult * vida_mult)
        if mercado_negro:
            preco = int(preco * 1.5)
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
    # Update por frame
    # ------------------------------------------------------------------

    def update(self, delta, desgaste_mult=1.0):
        """
        Chamado a cada frame com delta de tempo de jogo.
        desgaste_mult: modificador externo (alimentação reduz desgaste).
        Retorna True se o escravo morreu neste frame.
        """
        if not self.vivo:
            return False

        # Bebê — só cresce
        if self.eh_bebe:
            self.tempo_crescimento -= delta
            if self.tempo_crescimento <= 0:
                self.eh_bebe  = False
                self.minerando = True
            return False

        # Acumula tempo na mina
        self.tempo_na_mina += delta

        # Desgaste: resistência alta = perde vida devagar
        taxa = (0.5 / (self.resistencia * 0.1 + 1)) * desgaste_mult
        self.vida -= taxa * delta

        if self.vida <= 0:
            self.vida        = 0
            self.vivo        = False
            self.causa_morte = self.causa_morte or "Exaustão"
            return True

        # Avança animação
        self.anim_frame = (self.anim_frame + delta * 12) % 60
        return False

    # ------------------------------------------------------------------
    # Mineração
    # ------------------------------------------------------------------

    def pode_minerar(self, tempo_jogo, intervalo):
        """True se já passou o intervalo desde o último ciclo."""
        return (self.vivo and self.minerando and not self.eh_bebe and
                (tempo_jogo - self.ultimo_ciclo) >= intervalo)

    def executar_mineracao(self, tempo_jogo, mult_raridade=1.0,
                           mult_recursos=1.0, mult_sorte=1.0):
        """
        Executa um ciclo de mineração.
        Retorna (recurso_nome, quantidade, valor_total).
        """
        self.ultimo_ciclo = tempo_jogo

        # Quantidade base (força afeta)
        qtd_base = 1 + self.forca // 30
        qtd = max(1, int(random.randint(qtd_base, qtd_base + 2) * mult_recursos))

        # Escolha de recurso
        sorte_ef = (self.sorte / 100) * mult_sorte
        recurso  = self._escolher_recurso(sorte_ef, mult_raridade)

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
        e.nome = d["nome"]; e.genero = d["genero"]; e.idade = d["idade"]
        e.forca = d["forca"]; e.velocidade = d["velocidade"]
        e.resistencia = d["resistencia"]; e.fertilidade = d["fertilidade"]
        e.sorte = d["sorte"]; e.lealdade = d["lealdade"]
        e.vida = d["vida"]; e.vida_max = d["vida_max"]; e.vivo = d["vivo"]
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
