# Mina dos Servos Eternos

Idle game de gerenciamento de mina com elementos de RPG, progressão incremental, sistema familiar e eventos sistêmicos. O jogador administra servos, mineração, upgrades, reprodução, equipamentos, doenças, aposentadoria e prestígio.

## Novas Funcionalidades (Última atualização)

### ⏰ Cronologia e Histórico
- **Contador de Tempo**: Ano e Mês exibidos na barra superior em tempo real (1 Ano = 50s de jogo)
- **Aba Histórico**: Timeline visual com os eventos mais marcantes (nascimentos, mortes, aposentadorias, itens raros) com timestamp cronológico

### 😄 Sistema de Humor dos Servos
- Cada servo possui um **estado de humor** que modifica todos os seus atributos efetivos
- 8 estados: `Muito Feliz`, `Satisfeito`, `Normal`, `Cansado`, `Muito Cansado`, `Doente`, `Faminto`, `Amaldiçoado`
- Efeito vai de **–20%** (Doente/Faminto) a **+20%** (Muito Feliz)
- Status visível na **lista de servos** e no **modal de detalhes**

### ♥ Sistema Familiar Aprimorado
- **Lua de Mel (9 meses de jogo)**: ao formar um par, ambos ganham +20% em todos os atributos e +30% em fertilidade por 37.5s de jogo
- **Cooldown de Reprodução (2 anos)**: após um nascimento, pai e mãe ficam 100s de jogo sem poder ter outro filho
- Status de lua de mel e cooldown exibidos na lista de servos e no modal

### ⚡ Auto-Equip por Raridade
- Devolve itens inferiores ao inventário automaticamente
- **⚡ Auto-Equip Geral**: Botão na lista central que otimiza o equipamento de todos os mineradores vivos simultaneamente

### 🏪 Mercador de Itens
- Painel **Mercador de Itens** na aba **Loja** (canto direito)
- 3 a 5 itens aleatórios por sessão — equipamentos e consumíveis
- Preço = 2× valor base da raridade
- **Reseta a cada 5 minutos de jogo** (timer exibido)

### 💰 Rebalanceamento de Upgrades
- Custos dos upgrades de estrutura aumentados drasticamente (até **×60** no nível máximo)
- Progressão: Nível 1 = ~3.000g, Nível 4 = ~600.000g

### 🛌 Auto-Retorno do Repouso
- Servo em repouso com **stamina = 100%** volta ao trabalho automaticamente
- Botão manual **Voltar à Mina** disponível com > 10% de stamina

### 📋 Status no Modal de Detalhes
- [MORTO] com causa da morte exibido em vermelho
- [APOSENTADO] exibido em amarelo
- Timer de Lua de Mel e Cooldown de reprodução visíveis
- **Polimento UI**: Log com wrapping automático, Top Bar fixa e Bordas por Raridade (Épico/Lendário)

## Estrutura atual

```text
minerRules/
├── main.py
├── admin.py
├── README.md
├── MANUAL.md
├── tests/
└── src/
    ├── entrypoints/
    ├── contexts/
    │   ├── shared/
    │   ├── configuration/
    │   └── gameplay/
    │       ├── domain/        # Escravo, humor, breeding
    │       ├── application/   # GameManager, histórico, loja_itens
    │       └── infrastructure/
    └── ui/
        ├── pygame/            # Renderer, log clip, painel mercador
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

## Atalhos e Controles

| Ação | Como fazer |
|------|-----------|
| Scroll no log | Roda do mouse sobre a coluna EVENTOS |
| Detalhe do servo | Botão `Det.` na lista ou clique no card da mina |
| Formar par | Botão `Par` em um M, depois `Par` em um F |
| Auto-equip | Modal do servo → `⚡ Auto-Equip` |
| Auto-equip Geral | Topo da Lista de Servos → `⚡ AUTO-EQUIP GERAL` |
| Comprar item | Aba Loja → painel "Mercador de Itens" |
| Ver histórico | Aba `Histórico` |
| Ver inventário | Aba `Inventário` |

## Abas disponíveis

| Aba | Função |
|-----|--------|
| `Loja` | Comprar servos + **Mercador de Itens** |
| `Upgrades` | Melhorias da mina |
| `Breeding` | Pares ativos |
| `Mercado` | Vender recursos |
| `Prestígio` | Reset com bônus |
| `Conquistas` | Metas desbloqueadas |
| `Histórico` | **Timeline de eventos marcantes** |
| `Inventário` | Gerenciar itens coletados |

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
