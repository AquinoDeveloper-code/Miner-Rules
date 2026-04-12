from __future__ import annotations
# ============================================================
# manager.py — Classe Gerente (Capataz)
# ============================================================

import random
import uuid

from src.contexts.shared.constants import (
    MANAGER_TIERS, MANAGER_AUTONOMIA,
    RARITY_COLORS, MALE_NAMES, FEMALE_NAMES,
    RETIREMENT_AGE, MAX_AGE,
)

# Cores de urgência
_COR_INFO    = (140, 180, 140)
_COR_AVISO   = (230, 130,  35)
_COR_URGENTE = (220,  55,  55)
_COR_OPORT   = (255, 215,   0)


class Gerente:
    """
    Capataz que analisa o estado da mina e age de forma autônoma.

    Tiers: junior → experiente → mestre → lendário
    Autonomia: recomendacao | semi | automatico
    """

    _id_counter = 0

    # ---------------------------------------------------------------
    # Construção
    # ---------------------------------------------------------------

    def __init__(self, tipo: str = "junior"):
        Gerente._id_counter += 1
        self.id  = Gerente._id_counter
        self.uid = str(uuid.uuid4())[:8]

        tier = next((t for t in MANAGER_TIERS if t["tipo"] == tipo), MANAGER_TIERS[0])
        self.tipo          = tipo
        self.raridade      = tier["raridade"]
        self.eficiencia    = tier["eficiencia"]
        self.check_interval = tier["check_interval"]

        # Nome
        pool = MALE_NAMES + FEMALE_NAMES
        self.nome = random.choice(pool) + f"#{self.id}"
        self.genero = "M" if self.nome.split("#")[0] in MALE_NAMES else "F"

        # Autonomia
        self.autonomia = "recomendacao"

        # ── Configurações ajustáveis pelo jogador ─────────────────────
        # Venda automática
        self.cfg_vender_idosos     = True
        self.cfg_vender_idade_min  = 55      # vende se idade >= este valor E performance baixa
        self.cfg_vender_fracos     = False
        self.cfg_vender_attr_max   = 20      # vende se média de atributos <= este valor
        self.cfg_vender_doentes    = False   # vende doentes com stamina baixa
        # Compra automática
        self.cfg_comprar_auto      = False
        self.cfg_comprar_attr_min  = 40      # só compra se média >= este valor
        self.cfg_comprar_idade_max = 35
        # Equipamentos
        self.cfg_equip_auto        = True
        # Descanso
        self.cfg_descanso_auto     = True
        self.cfg_descanso_stamina  = 15      # força descanso se stamina <= X
        # Guardas (só mestre/lendário por padrão)
        self.cfg_guardas_auto      = (tipo in ("mestre", "lendario"))

        # ── Estatísticas ──────────────────────────────────────────────
        self.acoes_realizadas      = 0
        self.recomendacoes_geradas = 0

    # ---------------------------------------------------------------
    # Análise — retorna lista de recomendações/ações
    # ---------------------------------------------------------------

    def analisar(self, estado: dict) -> list[dict]:
        """
        Analisa o estado do jogo e retorna lista de recomendações.
        Cada item: {"tipo", "urgencia" (1-3), "msg", "cor",
                    "acao_tipo" (str|None), "acao_param"}
        """
        recs: list[dict] = []
        ef   = self.eficiencia

        escravos   = estado.get("escravos", [])
        ouro       = estado.get("ouro", 0)
        loja       = estado.get("loja", [])
        guardas    = estado.get("guardas", [])
        nivel_mina = estado.get("nivel_mina", 0)
        mercado_negro = estado.get("mercado_negro", False)
        inv_itens  = estado.get("inventario_itens", [])
        inv_guard  = estado.get("inventario_guard_itens", [])
        n_pares    = estado.get("n_pares", 0)
        capacidade = estado.get("capacidade", 10)

        # ── STAMINA GERAL ─────────────────────────────────────────────
        if ef >= 0.40 and escravos:
            baixo_stam = [e for e in escravos if e.stamina < 30]
            pct = len(baixo_stam) / len(escravos)
            if pct >= 0.40:
                recs.append({
                    "tipo": "stamina_baixa",
                    "urgencia": 2,
                    "msg": f"Stamina geral baixa ({pct*100:.0f}% dos servos abaixo de 30%). "
                           f"Considere comida de qualidade ou pausa forçada.",
                    "cor": _COR_AVISO,
                    "acao_tipo": "descanso_geral",
                    "acao_param": None,
                })

        # ── ESCRAVOS IDOSOS ───────────────────────────────────────────
        if ef >= 0.40 and self.cfg_vender_idosos:
            for e in escravos:
                if e.idade >= self.cfg_vender_idade_min and e.stamina < 25:
                    recs.append({
                        "tipo": "vender_idoso",
                        "urgencia": 2,
                        "msg": f"{e.nome} ({e.idade:.0f} anos, stamina {e.stamina:.0f}%) "
                               f"está desgastado. Recomendo vender ou aposentar.",
                        "cor": _COR_AVISO,
                        "acao_tipo": "vender_escravo",
                        "acao_param": e.id,
                    })

        # ── ESCRAVOS ELEGÍVEIS PARA APOSENTADORIA ─────────────────────
        if ef >= 0.50:
            for e in escravos:
                if e.idade >= RETIREMENT_AGE and not e.aposentado:
                    recs.append({
                        "tipo": "aposentar",
                        "urgencia": 1,
                        "msg": f"{e.nome} ({e.idade:.0f} anos) atingiu a idade de aposentadoria.",
                        "cor": _COR_INFO,
                        "acao_tipo": "aposentar_escravo",
                        "acao_param": e.id,
                    })

        # ── ESCRAVOS DOENTES ─────────────────────────────────────────
        if ef >= 0.50:
            from src.contexts.shared.constants import ITEMS
            pocoes = [iid for iid in inv_itens
                      if iid in ITEMS and ITEMS[iid].get("efeito_consumivel") == "curar_tudo"]
            doentes = [e for e in escravos if e.doente]
            for e in doentes[:len(pocoes)]:
                recs.append({
                    "tipo": "curar_doente",
                    "urgencia": 2,
                    "msg": f"{e.nome} está doente! Há poções disponíveis. Recomendo curar.",
                    "cor": _COR_AVISO,
                    "acao_tipo": "curar_escravo",
                    "acao_param": (e.id, pocoes[doentes.index(e)]),
                })

        # ── MALDIÇÕES ATIVAS COM REZA DISPONÍVEL ─────────────────────
        if ef >= 0.60:
            from src.contexts.shared.constants import ITEMS
            rezas = [iid for iid in inv_itens
                     if iid in ITEMS and ITEMS[iid].get("efeito_consumivel") == "quebrar_maldicao"]
            malditos = [e for e in escravos if e.tem_maldicao_ativa()]
            for e in malditos[:len(rezas)]:
                recs.append({
                    "tipo": "quebrar_maldicao",
                    "urgencia": 2,
                    "msg": f"{e.nome} está amaldiçoado e há Reza disponível. Recomendo usar.",
                    "cor": _COR_AVISO,
                    "acao_tipo": "usar_item_especial",
                    "acao_param": (e.id, rezas[malditos.index(e)]),
                })

        # ── COMPRA AUTOMÁTICA ─────────────────────────────────────────
        if ef >= 0.50 and self.cfg_comprar_auto and loja:
            slots_livres = capacidade - len(escravos)
            if slots_livres > 0:
                for oferta in loja:
                    e_loja = oferta.get("servo")
                    if not e_loja:
                        continue
                    media = (e_loja.forca + e_loja.velocidade + e_loja.resistencia +
                             e_loja.sorte + e_loja.lealdade) / 5
                    if (media >= self.cfg_comprar_attr_min and
                            e_loja.idade <= self.cfg_comprar_idade_max):
                        preco = e_loja.calcular_preco()
                        if ouro >= preco:
                            recs.append({
                                "tipo": "comprar_escravo",
                                "urgencia": 1,
                                "msg": f"Candidato na loja: {e_loja.nome} (média attrs {media:.0f}, "
                                       f"{e_loja.idade:.0f} anos) por {preco}g. Vale a pena!",
                                "cor": _COR_OPORT,
                                "acao_tipo": "comprar_oferta_loja",
                                "acao_param": oferta["id"],
                            })
                            break

        # ── EQUIP AUTO ────────────────────────────────────────────────
        if ef >= 0.60 and self.cfg_equip_auto and inv_itens:
            from src.contexts.shared.constants import ITEMS, SLOTS
            tem_itens_livres = any(
                iid in ITEMS and not ITEMS[iid].get("consumivel")
                for iid in inv_itens
            )
            if tem_itens_livres:
                recs.append({
                    "tipo": "equip_auto",
                    "urgencia": 1,
                    "msg": f"Há equipamentos no inventário sem uso. Auto-equipar todos os servos?",
                    "cor": _COR_INFO,
                    "acao_tipo": "auto_equipar_todos",
                    "acao_param": None,
                })

        # ── GUARDAS ───────────────────────────────────────────────────
        if ef >= 0.75 and nivel_mina >= 2 and len(guardas) == 0:
            recs.append({
                "tipo": "contratar_guarda",
                "urgencia": 2,
                "msg": f"Mina no nível {nivel_mina} sem nenhum guarda. As entregas estão vulneráveis!",
                "cor": _COR_AVISO,
                "acao_tipo": "comprar_guarda",
                "acao_param": "basico",
            })

        # ── GUARDAS EQUIP ─────────────────────────────────────────────
        if ef >= 0.80 and guardas and inv_guard:
            recs.append({
                "tipo": "equip_guardas",
                "urgencia": 1,
                "msg": f"Há equipamentos de guarda no inventário sem uso.",
                "cor": _COR_INFO,
                "acao_tipo": None,   # não há auto-equip coletivo de guardas ainda
                "acao_param": None,
            })

        # ── ESCRAVOS FRACOS ──────────────────────────────────────────
        if ef >= 0.70 and self.cfg_vender_fracos:
            for e in escravos:
                media = (e.forca + e.velocidade + e.resistencia +
                         e.sorte + e.lealdade) / 5
                if media <= self.cfg_vender_attr_max:
                    recs.append({
                        "tipo": "vender_fraco",
                        "urgencia": 1,
                        "msg": f"{e.nome} tem atributos muito baixos (média {media:.0f}). "
                               f"Vender e reinvestir?",
                        "cor": _COR_INFO,
                        "acao_tipo": "vender_escravo",
                        "acao_param": e.id,
                    })

        # ── MERCADO NEGRO ─────────────────────────────────────────────
        if ef >= 0.90 and mercado_negro:
            recs.append({
                "tipo": "mercado_negro",
                "urgencia": 2,
                "msg": "Mercado Negro ativo! Preços de venda +50%. Excelente hora para vender recursos!",
                "cor": _COR_OPORT,
                "acao_tipo": "vender_tudo",
                "acao_param": None,
            })

        # ── VENDER DOENTES ────────────────────────────────────────────
        if ef >= 0.75 and self.cfg_vender_doentes:
            for e in escravos:
                if e.doente and e.stamina < 10 and e.doenca_timer < 60:
                    recs.append({
                        "tipo": "vender_doente",
                        "urgencia": 3,
                        "msg": f"{e.nome} está grave (doente + stamina {e.stamina:.0f}%). Vender urgente.",
                        "cor": _COR_URGENTE,
                        "acao_tipo": "vender_escravo",
                        "acao_param": e.id,
                    })

        # Limita por eficiência (gerentes piores não vêem tudo)
        if ef < 1.0:
            n_visivel = max(1, int(len(recs) * ef))
            random.shuffle(recs)
            recs = recs[:n_visivel]

        self.recomendacoes_geradas += len(recs)
        return recs

    # ---------------------------------------------------------------
    # Serialização
    # ---------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "id":  self.id,   "uid": self.uid,
            "nome": self.nome, "genero": self.genero,
            "tipo": self.tipo, "raridade": self.raridade,
            "eficiencia": self.eficiencia,
            "check_interval": self.check_interval,
            "autonomia": self.autonomia,
            "cfg_vender_idosos":    self.cfg_vender_idosos,
            "cfg_vender_idade_min": self.cfg_vender_idade_min,
            "cfg_vender_fracos":    self.cfg_vender_fracos,
            "cfg_vender_attr_max":  self.cfg_vender_attr_max,
            "cfg_vender_doentes":   self.cfg_vender_doentes,
            "cfg_comprar_auto":     self.cfg_comprar_auto,
            "cfg_comprar_attr_min": self.cfg_comprar_attr_min,
            "cfg_comprar_idade_max":self.cfg_comprar_idade_max,
            "cfg_equip_auto":       self.cfg_equip_auto,
            "cfg_descanso_auto":    self.cfg_descanso_auto,
            "cfg_descanso_stamina": self.cfg_descanso_stamina,
            "cfg_guardas_auto":     self.cfg_guardas_auto,
            "acoes_realizadas":     self.acoes_realizadas,
            "recomendacoes_geradas":self.recomendacoes_geradas,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Gerente:
        g = cls.__new__(cls)
        g.id       = d["id"];   g.uid  = d.get("uid", str(uuid.uuid4())[:8])
        g.nome     = d["nome"]; g.genero = d.get("genero", "M")
        g.tipo     = d.get("tipo", "junior")
        g.raridade = d.get("raridade", "incomum")
        g.eficiencia     = d.get("eficiencia", 0.50)
        g.check_interval = d.get("check_interval", 90.0)
        g.autonomia      = d.get("autonomia", "recomendacao")
        g.cfg_vender_idosos     = d.get("cfg_vender_idosos",     True)
        g.cfg_vender_idade_min  = d.get("cfg_vender_idade_min",  55)
        g.cfg_vender_fracos     = d.get("cfg_vender_fracos",     False)
        g.cfg_vender_attr_max   = d.get("cfg_vender_attr_max",   20)
        g.cfg_vender_doentes    = d.get("cfg_vender_doentes",    False)
        g.cfg_comprar_auto      = d.get("cfg_comprar_auto",      False)
        g.cfg_comprar_attr_min  = d.get("cfg_comprar_attr_min",  40)
        g.cfg_comprar_idade_max = d.get("cfg_comprar_idade_max", 35)
        g.cfg_equip_auto        = d.get("cfg_equip_auto",        True)
        g.cfg_descanso_auto     = d.get("cfg_descanso_auto",     True)
        g.cfg_descanso_stamina  = d.get("cfg_descanso_stamina",  15)
        g.cfg_guardas_auto      = d.get("cfg_guardas_auto",      False)
        g.acoes_realizadas      = d.get("acoes_realizadas",      0)
        g.recomendacoes_geradas = d.get("recomendacoes_geradas", 0)
        if g.id >= Gerente._id_counter:
            Gerente._id_counter = g.id + 1
        return g

    def cor_raridade(self):
        return RARITY_COLORS.get(self.raridade, (200, 200, 200))
