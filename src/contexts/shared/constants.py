# ============================================================
# constants.py — Constantes globais do jogo
# "Mina dos Escravos Eternos"
# ============================================================

# ============================================================
# CONFIGURAÇÕES PRINCIPAIS — altere aqui para balancear o jogo
# ============================================================
MINING_INTERVAL    = 5.0   # Segundos de jogo entre ciclos de mineração
BREEDING_INTERVAL  = 30.0  # Segundos de jogo entre verificações de reprodução
GROWTH_TIME        = 180.0 # Segundos de jogo para bebê virar adulto (3 min)
AUTOSAVE_INTERVAL  = 30.0  # Segundos reais entre salvamentos automáticos
EVENT_INTERVAL     = 45.0  # Segundos reais entre eventos aleatórios
SHOP_REFRESH_TIME  = 300.0 # Segundos reais entre refreshes automáticos da loja

# ============================================================
# TELA
# ============================================================
SCREEN_WIDTH  = 1600
SCREEN_HEIGHT = 900
FPS           = 60
TITLE         = "Mina dos Servos Eternos"

# Layout dos painéis
LOG_SIDEBAR_W = 220  # Barra lateral esquerda — log de eventos (altura total)
LEFT_W    = 460   # Painel da mina / mineradores
CENTER_W  = 600   # Painel central (lista de servos)
RIGHT_W   = 320   # Painel direito (recursos / stats)
TOP_H     = 54    # Barra do topo
BOTTOM_H  = 230   # Painel de abas (loja, upgrades, etc.)
LOG_H     = 50    # Faixa do log de eventos
MAIN_H    = SCREEN_HEIGHT - TOP_H - BOTTOM_H - LOG_H

# ============================================================
# CORES
# ============================================================
BLACK       = (0,   0,   0)
DARK_BG     = (12,  8,   4)
PANEL_BG    = (22,  15,  8)
PANEL_BDR   = (55,  35,  15)
CAVE_BG     = (18,  12,  6)

DARK_BROWN  = (40,  25,  10)
MED_BROWN   = (75,  48,  18)
LIGHT_BROWN = (115, 75,  35)

WHITE       = (255, 255, 255)
GRAY        = (160, 160, 160)
DARK_GRAY   = (70,  70,  70)

RED         = (220, 55,  55)
DARK_RED    = (140, 20,  20)
GREEN       = (60,  210, 90)
DARK_GREEN  = (20,  120, 40)
BLUE        = (80,  130, 230)
YELLOW      = (230, 210, 55)
ORANGE      = (230, 130, 35)
PURPLE      = (160, 85,  215)
CYAN        = (55,  210, 210)
GOLD        = (255, 215, 0)
PINK        = (240, 130, 175)

# Raridade → cor de destaque
RARITY_COLORS = {
    "comum":    (140, 140, 140),
    "incomum":  (60,  210, 90),
    "raro":     (80,  130, 230),
    "épico":    (160, 85,  215),
    "lendário": (255, 175, 0),
}

# ============================================================
# RECURSOS — nome: {raridade_base, valor_por_unidade, cor, símbolo}
# raridade_base = probabilidade base de sair num ciclo
# ============================================================
RESOURCES = {
    "Terra":      {"raridade": 0.40,  "valor": 1,    "cor": (110, 72,  35),  "simbolo": "T"},
    "Pedra":      {"raridade": 0.25,  "valor": 3,    "cor": (145, 145, 145), "simbolo": "P"},
    "Ferro":      {"raridade": 0.15,  "valor": 8,    "cor": (185, 185, 205), "simbolo": "Fe"},
    "Ouro":       {"raridade": 0.08,  "valor": 25,   "cor": (255, 215, 0),   "simbolo": "Au"},
    "Esmeralda":  {"raridade": 0.05,  "valor": 80,   "cor": (50,  225, 85),  "simbolo": "Em"},
    "Diamante":   {"raridade": 0.04,  "valor": 200,  "cor": (160, 230, 255), "simbolo": "Di"},
    "Rubi":       {"raridade": 0.025, "valor": 350,  "cor": (255, 55,  55),  "simbolo": "Ru"},
    "Adamantita": {"raridade": 0.005, "valor": 1500, "cor": (210, 60,  255), "simbolo": "Ad"},
}
RESOURCE_ORDER = list(RESOURCES.keys())  # Ordem fixa para exibição

# ============================================================
# RARIDADES DOS ATRIBUTOS
# (nome, valor_mínimo, valor_máximo, mult_preço)
# ============================================================
ATTR_RARITIES = [
    ("lendário", 95, 100, 3.0),
    ("épico",    80,  94, 2.0),
    ("raro",     60,  79, 1.4),
    ("incomum",  40,  59, 1.0),
    ("comum",     1,  39, 0.7),
]

BASE_SLAVE_PRICE = 600  # Preço base de um escravo

# ============================================================
# NOMES DOS ESCRAVOS
# ============================================================
MALE_NAMES = [
    "Brutus","Kairo","Duro","Ferro","Zax","Mrak","Gorn","Thad",
    "Kell","Rax","Brak","Orin","Vorn","Crux","Slag","Ash",
    "Crag","Dirk","Flint","Grim","Hale","Jorn","Knox","Lex",
    "Mace","Nark","Odrak","Pyle","Qax","Sorn","Tusk","Urk",
]
FEMALE_NAMES = [
    "Mara","Sela","Vira","Dara","Kira","Orna","Brea","Zara",
    "Nyx","Lyra","Sera","Tara","Wren","Xena","Yara","Zola",
    "Calla","Demi","Elva","Faye","Gala","Hira","Ilma","Jana",
    "Kala","Lera","Mora","Nala","Opra","Pira","Qara","Reva",
]

# ============================================================
# UPGRADES DA MINA
# ============================================================
MINE_UPGRADES = {
    "ferramentas": {
        "nome": "Ferramentas",
        "desc": "Aumenta quantidade de recursos por ciclo",
        "icone": "Fe",
        "niveis": [
            {"custo": 0,       "bonus_recursos": 1.0, "nome": "Mãos nuas"},
            {"custo": 2500,    "bonus_recursos": 1.3, "nome": "Picaretas simples"},
            {"custo": 19000,   "bonus_recursos": 1.7, "nome": "Picaretas de ferro"},
            {"custo": 90000,   "bonus_recursos": 2.2, "nome": "Picaretas de aço"},
            {"custo": 500000,  "bonus_recursos": 3.0, "nome": "Picaretas encantadas"},
        ],
    },
    "alimentacao": {
        "nome": "Alimentação",
        "desc": "Reduz desgaste (aumenta vida útil) e lealdade",
        "icone": "Al",
        "niveis": [
            {"custo": 0,       "bonus_vida": 1.0, "bonus_lealdade": 0,  "nome": "Sobras"},
            {"custo": 2000,    "bonus_vida": 1.3, "bonus_lealdade": 5,  "nome": "Rações básicas"},
            {"custo": 14000,   "bonus_vida": 1.7, "bonus_lealdade": 12, "nome": "Refeições decentes"},
            {"custo": 72000,   "bonus_vida": 2.2, "bonus_lealdade": 20, "nome": "Comida nutritiva"},
            {"custo": 380000,  "bonus_vida": 3.0, "bonus_lealdade": 35, "nome": "Banquete"},
        ],
    },
    "seguranca": {
        "nome": "Segurança",
        "desc": "Reduz mortes por acidente e chance de rebelião",
        "icone": "Sg",
        "niveis": [
            {"custo": 0,       "red_morte": 0.00, "red_rebel": 0.0, "nome": "Nenhuma"},
            {"custo": 3800,    "red_morte": 0.15, "red_rebel": 0.1, "nome": "Guardas básicos"},
            {"custo": 24000,   "red_morte": 0.30, "red_rebel": 0.2, "nome": "Correntes reforçadas"},
            {"custo": 125000,  "red_morte": 0.50, "red_rebel": 0.4, "nome": "Sistema de vigilância"},
            {"custo": 620000,  "red_morte": 0.70, "red_rebel": 0.6, "nome": "Fortaleza subterrânea"},
        ],
    },
    "iluminacao": {
        "nome": "Iluminação",
        "desc": "Aumenta a sorte de encontrar recursos raros",
        "icone": "Il",
        "niveis": [
            {"custo": 0,       "bonus_sorte": 1.0, "nome": "Escuro total"},
            {"custo": 3000,    "bonus_sorte": 1.2, "nome": "Tochas de madeira"},
            {"custo": 21000,   "bonus_sorte": 1.5, "nome": "Lanternas a óleo"},
            {"custo": 108000,  "bonus_sorte": 2.0, "nome": "Luminárias de cristal"},
            {"custo": 580000,  "bonus_sorte": 2.8, "nome": "Luz mágica eterna"},
        ],
    },
    "ventilacao": {
        "nome": "Ventilação",
        "desc": "Reduz o intervalo de mineração (mineração mais rápida)",
        "icone": "Vt",
        "niveis": [
            {"custo": 0,       "bonus_vel": 1.0,  "nome": "Sufocante"},
            {"custo": 4200,    "bonus_vel": 1.15, "nome": "Buracos de ar"},
            {"custo": 28000,   "bonus_vel": 1.35, "nome": "Dutos de ventilação"},
            {"custo": 144000,  "bonus_vel": 1.60, "nome": "Ventiladores mecânicos"},
            {"custo": 720000,  "bonus_vel": 2.0,  "nome": "Sistema pressurizado"},
        ],
    },
}
UPGRADE_ORDER = list(MINE_UPGRADES.keys())

# ============================================================
# NÍVEIS DE PROFUNDIDADE DA MINA
# ============================================================
MINE_DEPTHS = [
    {"nome": "Superfície",         "custo": 0,      "mult_raridade": 1.0, "risco_morte": 0.010},
    {"nome": "Nível 1 — Raso",     "custo": 500,    "mult_raridade": 1.3, "risco_morte": 0.020},
    {"nome": "Nível 2 — Médio",    "custo": 2000,   "mult_raridade": 1.8, "risco_morte": 0.040},
    {"nome": "Nível 3 — Fundo",    "custo": 7000,   "mult_raridade": 2.5, "risco_morte": 0.070},
    {"nome": "Nível 4 — Abismo",   "custo": 20000,  "mult_raridade": 4.0, "risco_morte": 0.120},
    {"nome": "Nível 5 — Núcleo",   "custo": 60000,  "mult_raridade": 7.0, "risco_morte": 0.200},
]

# ============================================================
# EVENTOS ALEATÓRIOS
# ============================================================
RANDOM_EVENTS = [
    {"id": "rebelliao",       "nome": "Rebelião!",            "chance": 0.10, "tipo": "negativo"},
    {"id": "caverna_secreta", "nome": "Caverna Secreta!",     "chance": 0.05, "tipo": "positivo"},
    {"id": "fuga",            "nome": "Servo Fugiu!",         "chance": 0.12, "tipo": "negativo"},
    {"id": "doacao",          "nome": "Doação Inesperada!",   "chance": 0.04, "tipo": "positivo"},
    {"id": "epidemia",        "nome": "Epidemia!",            "chance": 0.06, "tipo": "negativo"},
    {"id": "mineral_lend",    "nome": "Veia Lendária!",       "chance": 0.03, "tipo": "positivo"},
    {"id": "acidente",        "nome": "Acidente na Mina!",    "chance": 0.08, "tipo": "negativo"},
    {"id": "mercado_negro",   "nome": "Mercado Negro!",       "chance": 0.05, "tipo": "neutro"},
]

# ============================================================
# CONQUISTAS
# condicao: (tipo, valor)
# tipos: escravos_total, escravos_vivos, recurso, ouro,
#        mortos, filhos, prestigios, tempo_sobrev
# ============================================================
ACHIEVEMENTS = [
    {"id": "primeiro",    "nome": "Primeiro Servo",           "desc": "Tenha seu primeiro servo",              "cond": ("escravos_total", 1)},
    {"id": "mao_obra",    "nome": "Mão de Obra",              "desc": "Tenha 5 servos ao mesmo tempo",         "cond": ("escravos_vivos", 5)},
    {"id": "exercito",    "nome": "Exército",                 "desc": "Tenha 20 servos ao mesmo tempo",        "cond": ("escravos_vivos", 20)},
    {"id": "legiao",      "nome": "Legião Eterna",            "desc": "Tenha 50 servos simultaneamente",       "cond": ("escravos_vivos", 50)},
    {"id": "ouro_1",      "nome": "Faísca de Ouro",           "desc": "Encontre Ouro pela primeira vez",       "cond": ("recurso", "Ouro")},
    {"id": "diamante_1",  "nome": "Coração de Diamante",      "desc": "Encontre um Diamante",                  "cond": ("recurso", "Diamante")},
    {"id": "rubi_1",      "nome": "Sangue de Pedra",          "desc": "Encontre um Rubi",                      "cond": ("recurso", "Rubi")},
    {"id": "ada_1",       "nome": "Toque Lendário",           "desc": "Encontre Adamantita",                   "cond": ("recurso", "Adamantita")},
    {"id": "rico",        "nome": "Comerciante",              "desc": "Acumule 1.000 de ouro",                 "cond": ("ouro", 1000)},
    {"id": "magnata",     "nome": "Magnata da Mina",          "desc": "Acumule 50.000 de ouro",                "cond": ("ouro", 50000)},
    {"id": "nascimento",  "nome": "Berço da Mina",            "desc": "Primeiro filho nascido na mina",        "cond": ("filhos", 1)},
    {"id": "cemiterio",   "nome": "Cemitério Subterrâneo",    "desc": "100 servos morreram",                   "cond": ("mortos", 100)},
    {"id": "sobreviv",    "nome": "Sobrevivente",             "desc": "Um servo viveu 30 min de jogo",         "cond": ("tempo_sobrev", 1800)},
    {"id": "prestg_1",    "nome": "Renascimento",             "desc": "Faça seu primeiro prestígio",           "cond": ("prestigios", 1)},
    {"id": "prestg_5",    "nome": "Eterno",                   "desc": "Faça 5 prestígios",                     "cond": ("prestigios", 5)},
]

# ============================================================
# PRESTÍGIO
# ============================================================
PRESTIGE_GOLD_REQ   = 100_000   # Ouro total ganho para poder prestigiar
PRESTIGE_BONUS_STEP = 0.10      # Bônus por prestígio (+10% em tudo)

# ============================================================
# SISTEMA DE IDADE
# ============================================================
SLAVE_AGING_RATE     = 1.0 / 120.0   # anos/s de jogo (1 ano a cada 2min)
RETIREMENT_AGE       = 50
MAX_AGE              = 70             # morte natural garantida

# ============================================================
# STAMINA
# ============================================================
STAMINA_DRAIN_BASE   = 8.0    # % por ciclo de mineração
STAMINA_REGEN_RATE   = 0.20   # % por segundo de jogo (base)

# ============================================================
# ALIMENTAÇÃO
# ============================================================
FOOD_COST_BASIC      = 5      # ouro por checagem
FOOD_COST_QUALITY    = 25
FOOD_CHECK_INTERVAL  = 120.0  # segundos de jogo

# ============================================================
# DISEASE
# ============================================================
DISEASE_BASE_CHANCE  = 0.002  # por segundo de jogo (muito baixo)
DISEASE_DURATION     = 600.0  # 10 minutos base

# ============================================================
# SLOTS DE EQUIPAMENTO
# ============================================================
SLOTS = ["capacete", "camiseta", "calcas", "botas", "picareta", "especial"]
SLOT_NOMES = {
    "capacete": "Capacete",
    "camiseta": "Peitoral",
    "calcas":   "Calcas",
    "botas":    "Botas",
    "picareta": "Picareta",
    "especial": "Amuleto",
}

# ============================================================
# ITENS DO JOGO
# Cada item tem: nome, slot, raridade, efeitos (dict de bônus),
# maldito (bool), duracao_maldicao (seg), consumivel (bool),
# efeito_consumivel (str ou None)
# ============================================================
ITEMS = {
    # ---- CAPACETES ----
    "cap_couro": {
        "nome": "Elmo de Couro", "slot": "capacete", "raridade": "comum",
        "bonus": {"resistencia": 3, "forca": 0},
        "maldito": False, "duracao_maldicao": 0, "consumivel": False,
        "cor_visual": (180, 100, 50),
    },
    "cap_ferro": {
        "nome": "Elmo de Ferro", "slot": "capacete", "raridade": "incomum",
        "bonus": {"resistencia": 8},
        "maldito": False, "duracao_maldicao": 0, "consumivel": False,
        "cor_visual": (180, 180, 190),
    },
    "cap_aco": {
        "nome": "Elmo de Aco", "slot": "capacete", "raridade": "raro",
        "bonus": {"resistencia": 16, "sorte": 4},
        "maldito": False, "duracao_maldicao": 0, "consumivel": False,
        "cor_visual": (130, 140, 160),
    },
    "cap_maldito": {
        "nome": "Elmo Maldito", "slot": "capacete", "raridade": "épico",
        "bonus": {"forca": 25, "resistencia": -15},
        "maldito": True, "duracao_maldicao": 300.0, "consumivel": False,
        "cor_visual": (80, 30, 90),
    },
    # ---- PEITORAL ----
    "cam_pano": {
        "nome": "Camisa de Pano", "slot": "camiseta", "raridade": "comum",
        "bonus": {"resistencia": 2},
        "maldito": False, "duracao_maldicao": 0, "consumivel": False,
        "cor_visual": (200, 190, 170),
    },
    "cam_couro": {
        "nome": "Colete de Couro", "slot": "camiseta", "raridade": "incomum",
        "bonus": {"resistencia": 7, "velocidade": 3},
        "maldito": False, "duracao_maldicao": 0, "consumivel": False,
        "cor_visual": (120, 70, 30),
    },
    "cam_cota": {
        "nome": "Cota de Malha", "slot": "camiseta", "raridade": "raro",
        "bonus": {"resistencia": 14, "velocidade": 5},
        "maldito": False, "duracao_maldicao": 0, "consumivel": False,
        "cor_visual": (160, 160, 170),
    },
    # ---- CALCAS ----
    "cal_pano": {
        "nome": "Calcas de Pano", "slot": "calcas", "raridade": "comum",
        "bonus": {"velocidade": 2},
        "maldito": False, "duracao_maldicao": 0, "consumivel": False,
        "cor_visual": (180, 170, 150),
    },
    "cal_couro": {
        "nome": "Calcas de Couro", "slot": "calcas", "raridade": "incomum",
        "bonus": {"velocidade": 6, "resistencia": 2},
        "maldito": False, "duracao_maldicao": 0, "consumivel": False,
        "cor_visual": (100, 60, 20),
    },
    # ---- BOTAS ----
    "bot_pano": {
        "nome": "Sandalia de Corda", "slot": "botas", "raridade": "comum",
        "bonus": {"velocidade": 3},
        "maldito": False, "duracao_maldicao": 0, "consumivel": False,
        "cor_visual": (190, 180, 150),
    },
    "bot_couro": {
        "nome": "Botas de Couro", "slot": "botas", "raridade": "incomum",
        "bonus": {"velocidade": 7, "forca": 2},
        "maldito": False, "duracao_maldicao": 0, "consumivel": False,
        "cor_visual": (90, 50, 20),
    },
    "bot_ferro": {
        "nome": "Botas de Ferro", "slot": "botas", "raridade": "raro",
        "bonus": {"velocidade": 5, "resistencia": 8},
        "maldito": False, "duracao_maldicao": 0, "consumivel": False,
        "cor_visual": (150, 150, 160),
    },
    # ---- PICARETAS ----
    "pic_pedra": {
        "nome": "Picareta de Pedra", "slot": "picareta", "raridade": "comum",
        "bonus": {"mineracao_mult": 1.2, "raridade_mult": 1.0},
        "maldito": False, "duracao_maldicao": 0, "consumivel": False,
        "cor_visual": (120, 120, 120),
    },
    "pic_ferro": {
        "nome": "Picareta de Ferro", "slot": "picareta", "raridade": "incomum",
        "bonus": {"mineracao_mult": 1.5, "raridade_mult": 1.1},
        "maldito": False, "duracao_maldicao": 0, "consumivel": False,
        "cor_visual": (190, 190, 200),
    },
    "pic_aco": {
        "nome": "Picareta de Aco", "slot": "picareta", "raridade": "raro",
        "bonus": {"mineracao_mult": 2.0, "raridade_mult": 1.3},
        "maldito": False, "duracao_maldicao": 0, "consumivel": False,
        "cor_visual": (140, 150, 170),
    },
    "pic_ouro": {
        "nome": "Picareta Dourada", "slot": "picareta", "raridade": "épico",
        "bonus": {"mineracao_mult": 2.5, "raridade_mult": 1.8, "sorte": 15},
        "maldito": False, "duracao_maldicao": 0, "consumivel": False,
        "cor_visual": (255, 215, 0),
    },
    "pic_lend": {
        "nome": "Picareta Lendaria", "slot": "picareta", "raridade": "lendário",
        "bonus": {"mineracao_mult": 4.0, "raridade_mult": 2.5, "sorte": 25},
        "maldito": False, "duracao_maldicao": 0, "consumivel": False,
        "cor_visual": (100, 255, 255),
    },
    "pic_maldita": {
        "nome": "Picareta Amaldicada", "slot": "picareta", "raridade": "épico",
        "bonus": {"mineracao_mult": 3.5, "raridade_mult": 2.0, "resistencia": -20},
        "maldito": True, "duracao_maldicao": 600.0, "consumivel": False,
        "cor_visual": (180, 40, 40),
    },
    # ---- AMULETOS / ESPECIAL ----
    "amu_sorte": {
        "nome": "Amuleto da Sorte", "slot": "especial", "raridade": "incomum",
        "bonus": {"sorte": 12},
        "maldito": False, "duracao_maldicao": 0, "consumivel": False,
    },
    "amu_forca": {
        "nome": "Amuleto da Forca", "slot": "especial", "raridade": "incomum",
        "bonus": {"forca": 10},
        "maldito": False, "duracao_maldicao": 0, "consumivel": False,
    },
    "amu_vida": {
        "nome": "Amuleto da Vida", "slot": "especial", "raridade": "raro",
        "bonus": {"resistencia": 12, "sorte": 5},
        "maldito": False, "duracao_maldicao": 0, "consumivel": False,
    },
    "amu_maldito": {
        "nome": "Olho Maldito", "slot": "especial", "raridade": "épico",
        "bonus": {"sorte": 30, "forca": 20, "velocidade": -15, "resistencia": -10},
        "maldito": True, "duracao_maldicao": 480.0, "consumivel": False,
    },
    # ---- CONSUMÍVEIS (usados via usar_item_especial) ----
    "reza_simples": {
        "nome": "Reza Simples", "slot": "especial", "raridade": "comum",
        "bonus": {},
        "maldito": False, "duracao_maldicao": 0,
        "consumivel": True, "efeito_consumivel": "quebrar_maldicao",
        "cor_visual": (150, 200, 255), # Aura color
    },
    "pocao_cura": {
        "nome": "Pocao de Cura", "slot": "especial", "raridade": "incomum",
        "bonus": {},
        "maldito": False, "duracao_maldicao": 0,
        "consumivel": True, "efeito_consumivel": "curar_tudo",
        "cor_visual": (100, 255, 100), # Aura color
    },
}

# Chance de drop de cada item por ciclo de mineração
ITEM_DROP_CHANCES = {
    "pic_pedra":   0.0030,
    "cap_couro":   0.0025,
    "cam_pano":    0.0025,
    "cal_pano":    0.0025,
    "bot_pano":    0.0025,
    "cap_ferro":   0.0012,
    "cam_couro":   0.0012,
    "cal_couro":   0.0012,
    "bot_couro":   0.0012,
    "pic_ferro":   0.0010,
    "amu_sorte":   0.0008,
    "amu_forca":   0.0008,
    "cap_aco":     0.0005,
    "cam_cota":    0.0005,
    "bot_ferro":   0.0005,
    "pic_aco":     0.0004,
    "amu_vida":    0.0004,
    "reza_simples":0.0006,
    "pocao_cura":  0.0003,
    "pic_ouro":    0.0002,
    "amu_maldito": 0.0001,
    "cap_maldito": 0.0001,
    "pic_maldita": 0.0001,
    "pic_lend":    0.00005,
}
