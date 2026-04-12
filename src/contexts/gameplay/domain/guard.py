from __future__ import annotations
# ============================================================
# guard.py — Classe Guarda e Delivery
# ============================================================

import random
import uuid

from src.contexts.shared.constants import (
    GUARD_SLOTS, GUARD_TIERS, GUARD_ITEMS,
    RARITY_COLORS, MALE_NAMES, FEMALE_NAMES,
    DELIVERY_BASE_TIME, DELIVERY_MIN_TIME,
    DELIVERY_ATTACKS, DELIVERY_ATTACK_RATE,
)


# ============================================================
# DELIVERY — item em trânsito para o cofre
# ============================================================

class Delivery:
    """Representa recursos minerados em trânsito para o cofre."""

    _id_counter = 0

    def __init__(self, recurso: str, qtd: int, valor: int,
                 escravo_nome: str, timer: float):
        Delivery._id_counter += 1
        self.id           = Delivery._id_counter
        self.recurso      = recurso
        self.qtd          = qtd
        self.valor        = valor
        self.escravo_nome = escravo_nome
        self.timer        = timer          # segundos reais restantes
        self.timer_max    = timer
        # "transito" → "entregue" | "perdido"
        self.status       = "transito"
        self.ataque_nome  = None           # nome do atacante (para log visual)
        self.ataque_cor   = (200, 100, 100)
        self._atk_check   = 5.0           # próximo check de ataque (segundos reais)

    def to_dict(self) -> dict:
        return {
            "id":           self.id,
            "recurso":      self.recurso,
            "qtd":          self.qtd,
            "valor":        self.valor,
            "escravo_nome": self.escravo_nome,
            "timer":        self.timer,
            "timer_max":    self.timer_max,
            "status":       self.status,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Delivery:
        obj = cls(
            d["recurso"], d["qtd"], d["valor"],
            d["escravo_nome"], d.get("timer", 0.0),
        )
        obj.id        = d["id"]
        obj.timer_max = d.get("timer_max", d.get("timer", 15.0))
        obj.status    = d.get("status", "entregue")  # se estava em trânsito, considera entregue
        if obj.id >= Delivery._id_counter:
            Delivery._id_counter = obj.id + 1
        return obj


# ============================================================
# GUARDA — protege as entregas
# ============================================================

class Guarda:
    """
    Representa um guarda contratado para proteger as entregas da mina.

    Atributos:
        forca      → aumenta chance de recuperação em ataques
        resistencia → reduz itens perdidos em ataques não recuperados
        agilidade  → reduz probabilidade de ser atacado
    """

    _id_counter = 0

    def __init__(self, tipo: str = "basico"):
        Guarda._id_counter += 1
        self.id  = Guarda._id_counter
        self.uid = str(uuid.uuid4())[:8]

        # Tier
        tier = next((t for t in GUARD_TIERS if t["tipo"] == tipo), GUARD_TIERS[1])
        self.tipo      = tipo
        self.raridade  = tier["raridade"]

        # Gênero e nome
        self.genero = random.choice(("M", "F"))
        pool = MALE_NAMES if self.genero == "M" else FEMALE_NAMES
        self.nome = random.choice(pool) + f"#{self.id}"

        # Atributos base
        lo, hi = tier["attr_range"]
        self.forca       = random.randint(lo, hi)
        self.resistencia = random.randint(lo, hi)
        self.agilidade   = random.randint(lo, hi)

        # Idade
        id_lo, id_hi = tier["idade_range"]
        self.idade = float(random.randint(id_lo, id_hi))

        # Estado
        self.ativo = True   # False = de_folga (recuperando)

        # Equipamentos
        self.equipamentos: dict[str, str | None] = {slot: None for slot in GUARD_SLOTS}

    # ------------------------------------------------------------------
    # Bônus de equipamento
    # ------------------------------------------------------------------

    def bonus_equip(self, attr: str) -> int:
        total = 0
        for slot in GUARD_SLOTS:
            iid = self.equipamentos.get(slot)
            if iid and iid in GUARD_ITEMS:
                total += GUARD_ITEMS[iid]["bonus"].get(attr, 0)
        return total

    def forca_efetiva(self) -> int:
        return max(1, self.forca + self.bonus_equip("forca"))

    def resistencia_efetiva(self) -> int:
        return max(1, self.resistencia + self.bonus_equip("resistencia"))

    def agilidade_efetiva(self) -> int:
        return max(1, self.agilidade + self.bonus_equip("agilidade"))

    def poder_total(self) -> int:
        return (self.forca_efetiva() + self.resistencia_efetiva()
                + self.agilidade_efetiva())

    def cor_raridade(self):
        return RARITY_COLORS.get(self.raridade, (200, 200, 200))

    # ------------------------------------------------------------------
    # Serialização
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "id":           self.id,
            "uid":          self.uid,
            "nome":         self.nome,
            "genero":       self.genero,
            "tipo":         self.tipo,
            "raridade":     self.raridade,
            "forca":        self.forca,
            "resistencia":  self.resistencia,
            "agilidade":    self.agilidade,
            "idade":        self.idade,
            "ativo":        self.ativo,
            "equipamentos": self.equipamentos,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Guarda:
        g = cls.__new__(cls)
        g.id           = d["id"]
        g.uid          = d.get("uid", str(uuid.uuid4())[:8])
        g.nome         = d["nome"]
        g.genero       = d.get("genero", "M")
        g.tipo         = d.get("tipo", "basico")
        g.raridade     = d.get("raridade", "comum")
        g.forca        = d.get("forca", 20)
        g.resistencia  = d.get("resistencia", 20)
        g.agilidade    = d.get("agilidade", 20)
        g.idade        = float(d.get("idade", 25))
        g.ativo        = d.get("ativo", True)
        g.equipamentos = d.get("equipamentos", {slot: None for slot in GUARD_SLOTS})
        for slot in GUARD_SLOTS:
            if slot not in g.equipamentos:
                g.equipamentos[slot] = None
        if g.id >= Guarda._id_counter:
            Guarda._id_counter = g.id + 1
        return g
