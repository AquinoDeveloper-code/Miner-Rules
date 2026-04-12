# Mina dos Servos Eternos

Idle game de gerenciamento de mina com elementos de RPG, progressão incremental, sistema familiar, logística de entregas, guardas e automação via gerentes. O jogador administra servos, mineração, upgrades, reprodução, equipamentos, doenças, aposentadoria e prestígio.

## Novas Funcionalidades (v1.3.0)

### 🚚 Sistema de Entrega com Ataques
- Recursos minerados percorrem um **trajeto real** antes de chegar ao cofre (tempo proporcional à velocidade do servo + nível da mina)
- Quatro tipos de atacante: Alcateia de Lobos, Urso Gigante, Ladrões, Horda de Orcs — cada um com taxa de recuperação diferente
- Fila de entregas com **barras de progresso** no painel direito
- Entregas em trânsito ao salvar são concluídas automaticamente ao reabrir

### 🛡️ Sistema de Guardas
- Nova aba **Guardas** para contratar e gerenciar protetores
- 5 tiers (Velho → Lendário) com atributos de Força, Resistência e Agilidade
- Contribuição coletiva: reduz chance de ataque (até 60%) e aumenta recuperação (até 35%)
- 6 slots de equipamento por guarda (17 itens disponíveis)
- Modal de detalhe com auto-equip e loja de itens de guarda
- Guardas são **preservados no Prestígio**

### 🧳 Vendedor Ambulante
- Vendedores aparecem aleatoriamente com itens para servos e guardas
- 4 tipos de qualidade: Bugigangas, Raro, Duvidoso, Sombras
- Notificação e botão de acesso no painel direito com timer visível

### 🧠 Sistema de Gerentes (Capatazes)
- Nova aba **Gerência** com 4 tiers: Júnior (15k) → Lendário (1M de ouro)
- 3 modos de autonomia: **Só Recomenda**, **Semi-Auto**, **Automático**
- 12 tipos de recomendação (stamina, doenças, maldições, compras, equipamentos, guardas, mercado negro…)
- Fila de recomendações com botões **Executar** e **Ignorar**
- Modal de configuração por gerente com todos os critérios ajustáveis
- Gerentes são **preservados no Prestígio**

### ⚖️ Correção de Mortes
- Taxa de morte por acidente reduzida ~12× — mortes por acidente muito menos frequentes, mortes por velhice mais representadas

---

## Funcionalidades anteriores (v1.2.0)

- **Sistema de Humor**: 8 estados (±20% nos atributos)
- **Sistema Familiar**: Lua de Mel (9 meses) + Cooldown de reprodução (2 anos)
- **Auto-Equip por raridade** individual e geral
- **Mercador de Itens** na aba Loja (reseta a cada 5 min)
- **Cronologia**: Ano e Mês na barra superior; aba **Histórico** com timeline
- **Auto-Retorno do Repouso** ao atingir 100% de stamina
- **Inventário** com deleção em massa e tooltips comparativos

## Estrutura atual

```text
minerRules/
├── main.py
├── admin.py
├── README.md
├── MANUAL.md
├── CHANGELOG.md
├── tests/
└── src/
    ├── entrypoints/
    ├── contexts/
    │   ├── shared/
    │   │   └── constants.py       # todos os catálogos e constantes
    │   ├── configuration/
    │   └── gameplay/
    │       ├── domain/
    │       │   ├── slave.py       # Escravo, humor, breeding
    │       │   ├── guard.py       # Delivery, Guarda
    │       │   └── manager.py     # Gerente, analisar()
    │       ├── application/
    │       │   └── game_manager.py  # orquestrador principal
    │       └── infrastructure/
    └── ui/
        ├── pygame/
        │   └── renderer.py        # UI completa, 10 abas
        └── admin/
```

## Execução

```bash
pip install -r requirements.txt
python main.py
```

Painel administrativo:

```bash
python admin.py
```

## Abas disponíveis

| Aba | Função |
|-----|--------|
| `Loja` | Comprar servos + Mercador de Itens |
| `Upgrades` | Melhorias da mina |
| `Breeding` | Pares ativos e reprodução |
| `Mercado` | Vender recursos |
| `Prestígio` | Reset com bônus permanentes |
| `Conquistas` | Metas desbloqueadas |
| `Histórico` | Timeline de eventos marcantes |
| `Inventário` | Gerenciar itens coletados |
| `Guardas` | Contratar, equipar e gerenciar guardas |
| `Gerência` | Capatazes, recomendações e automação |

## Atalhos e Controles

| Ação | Como fazer |
|------|-----------|
| Scroll no log | Roda do mouse sobre a coluna EVENTOS |
| Fechar modal | ESC (cascata: Vendedor → Gerente → Guarda → Servo) |
| Detalhe do servo | Botão `Det.` na lista |
| Formar par | `Par` em M, depois `Par` em F |
| Auto-equip servo | Modal do servo → `⚡ Auto-Equip` |
| Auto-equip Geral | Topo da lista → `⚡ AUTO-EQUIP GERAL` |
| Detalhe do guarda | Aba Guardas → `Det.` |
| Config do gerente | Aba Gerência → `Config` |
| Executar rec. | Aba Gerência → `Exec.` na recomendação |
| Vendedor Ambulante | Painel direito → botão Vendedor |
| Ver histórico | Aba `Histórico` |
| Ver inventário | Aba `Inventário` |

## Persistência

- Save ativo: `save_eternal_mine.db` (SQLite)
- Regras dinâmicas: `game_rules.json`
- macOS: `~/Library/Application Support/MinaDosEscravosEternos/`

## Testes

```bash
python3 -m unittest discover -s tests -v
```

## Documentação detalhada

O manual completo está em [MANUAL.md](MANUAL.md).
O histórico de versões está em [CHANGELOG.md](CHANGELOG.md).
