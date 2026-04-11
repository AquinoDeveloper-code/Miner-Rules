# Manual Completo — Mina dos Servos Eternos

## 1. Visão geral

`Mina dos Servos Eternos` é um idle game de gerenciamento contínuo. O jogador opera uma mina subterrânea, contrata e vende servos, organiza casais para reprodução, equipa trabalhadores, reage a eventos aleatórios e escala a operação por profundidade, upgrades e prestígio.

O jogo mistura:

- gestão incremental
- progressão por ciclos cronológicos (Anos e Meses)
- simulação de atributos e humor dos servos
- risco sistêmico
- sistema familiar com lua de mel e cooldown de reprodução

## 2. Ambientação e proposta

O jogo apresenta uma mina brutal e decadente, sustentada por mão de obra explorada, onde riqueza e sobrevivência entram em conflito o tempo inteiro. A progressão existe em camadas:

- camada operacional: manter a mina lucrando
- camada tática: escolher quem comprar, vender, equipar e aposentar
- camada sistêmica: controlar fome, doença, rebelião, eventos e lotação
- camada familiar: gerenciar pares, lua de mel, cooldowns e nascimentos
- camada meta: prestigiar para acelerar runs futuras

## 3. Como iniciar

### Jogo principal

```bash
python main.py
```

### Painel administrativo

```bash
python admin.py
```

## 4. Estrutura técnica

### 4.1. Entry points

- `main.py`: wrapper compatível que chama `src.entrypoints.main`
- `admin.py`: wrapper compatível que chama `src.entrypoints.admin`

### 4.2. Estrutura real em `src`

- `src/contexts/shared/constants.py`
  - catálogo de recursos, itens, upgrades, eventos, conquistas
  - balanceamento base e custos de upgrades

- `src/contexts/gameplay/domain/slave.py`
  - entidade `Escravo` com atributos, humor, honeymoon, breeding cooldown
  - envelhecimento, stamina, mineração, serialização

- `src/contexts/gameplay/application/game_manager.py`
  - orquestra o estado global da run
  - loja de servos e loja de itens do mercador
  - breeding com lua de mel e cooldown
  - eventos, upgrades, prestígio, save/load
  - cronômetro de Anos e Meses
  - histórico de eventos marcantes

- `src/ui/pygame/renderer.py`
  - interface do jogo com pixel art
  - log com scroll e clip real
  - abas: Loja, Upgrades, Breeding, Mercado, Prestígio, Conquistas, Histórico, Inventário

## 5. Persistência

O save usa SQLite (`save_eternal_mine.db`). Regras dinâmicas ficam em `game_rules.json`.

## 6. Interface do jogo

### 6.1. Barra superior

- **Título** + **Ano X, Mês Y** em tempo real (1 Ano = 50s de jogo)
- **Ouro atual** (deslocado para evitar sobreposição com o título)
- `Reset`, `Acelerar`, `Salvar`, `Pause`, `1x/2x/4x`, `Encerrar`

### 6.2. Sidebar de log (EVENTOS)

- Exibe o histórico de eventos em tempo real
- **Scroll funciona com roda do mouse** (cima = histórico mais antigo)
- Texto com clipping real — nada vaza para fora da coluna
- Cores por tipo: verde = cura/ganho, vermelho = morte/fome, roxo = item, amarelo = conquista

### 6.3. Painel da mina (esquerda)

- Servos em pixel art animados
- Partículas de destaque ao minerar
- Brilho por raridade do servo

### 6.4. Lista central de servos

Cada linha de servo exibe:

- Gênero (M/F) e nome
- Barra de stamina com cor (verde/amarelo/vermelho)
- Idade com cor indicativa
- Atributos abreviados: F, V, R, Fe, S, L
- **Status de Humor** — exemplo: `[Muito Feliz]`, `[Doente]`, `[Cansado]`
- **♥ Lua de mel** ou **♥ Par** quando em casal
- Botões: `Det.` (detalhe), `Vend.` (vender), `Par` (criar par)
- Botão **Voltar à Mina** quando em repouso (disponível com > 10% stamina)

### 6.5. Painel lateral direito

- Inventário de recursos com quantidade e valor
- Estatísticas da run
- Venda rápida por recurso

### 6.6. Painel inferior por abas

| Aba | O que faz |
|-----|-----------|
| `Loja` | Comprar servos + **Mercador de Itens** (canto direito) |
| `Upgrades` | Melhorias de ferramentas, segurança, iluminação, ventilação, alimentação |
| `Breeding` | Gerenciar pares ativos e reprodução |
| `Mercado` | Vender recursos em lote |
| `Prestígio` | Resetar run com bônus permanentes |
| `Conquistas` | Ver conquistas desbloqueadas |
| `Histórico` | **Timeline de eventos marcantes** (mortes, nascimentos, itens raros) |
| `Inventário` | Ver e gerenciar todos os itens da mochila |

## 7. Sistema de tempo cronológico

O jogo possui um contador de tempo interno:

- **1 Ano de jogo = 50 segundos reais** (na velocidade 1x)
- **1 Mês de jogo = ≈ 4.16 segundos** (1 Ano ÷ 12)
- O tempo atual aparece na **barra superior**: `Ano X, Mês Y`

### Aba Histórico

A aba **Histórico** mostra os eventos mais marcantes com timestamp:

- 🩷 Rosa = Nascimentos
- 🔴 Vermelho = Mortes
- 🟡 Dourado = Itens lendários/míticos
- 🟠 Laranja = Doenças graves e aposentadorias

## 8. Sistema de servos

### 8.1. Atributos

- força, velocidade, resistência, fertilidade, sorte, lealdade

### 8.2. Humor e Status do servo

Cada servo possui um estado de humor que **modifica todos os atributos efetivos**:

| Humor | Efeito |
|-------|--------|
| `Muito Feliz` | +20% em todos os atributos |
| `Satisfeito` | +10% |
| `Normal` | Sem modificador |
| `Cansado` | Stamina < 50% |
| `Muito Cansado` | Stamina < 20% — -15% nos atributos |
| `Doente` | -20% nos atributos |
| `Faminto` | -20% nos atributos |
| `Amaldiçoado` | -20% nos atributos |

O status aparece visível em **cada linha da lista de servos** e no modal de detalhes.

### 8.3. Stamina

- Vai de 0 a 100%
- Ao atingir 0, o servo entra em **Repouso automático**
- Ao atingir 100% no repouso, **volta ao trabalho automaticamente**
- O botão **Voltar à Mina** fica disponível com > 10% de stamina

### 8.4. Morte e aposentadoria

Quando um servo morre ou é aposentado:

- Um aviso `[MORTO] causa` ou `[APOSENTADO]` aparece no modal de detalhes
- O evento é registrado no **Histórico** com Ano e Mês exatos

## 9. Sistema familiar (Breeding)

### 9.1. Formando um par

- Clique em `Par` em um servo masculino, depois `Par` em um feminino
- Ao formar um casal, **ambos ganham Lua de Mel por 9 meses de jogo (37.5s)**

### 9.2. Lua de Mel

Durante a lua de mel:

- **+20% em Força, Velocidade, Resistência, Sorte e Lealdade**
- **+30% em Fertilidade**
- O status exibido será **"Muito Feliz"**
- A lista de servos exibe `♥ Lua de mel`

### 9.3. Cooldown de reprodução (2 anos)

Após um nascimento:

- Pai e mãe ficam com **cooldown de 2 anos de jogo (100s)** — não podem ter outro filho nesse período
- O cooldown é exibido no modal de detalhes do servo

### 9.4. Bebês

- Nascem em estado de bebê — não mineraram
- Crescem automaticamente após o tempo configurado
- Aparecem na lista com indicador de crescimento `Cres.X%`

## 10. Auto-Equip

No modal de detalhe do servo, existe o botão **⚡ Auto-Equip (Por Raridade)**.

Ao clicar:

- O sistema varre todos os itens do inventário
- Para cada slot (capacete, picareta, etc.), equipa o item de **maior raridade** disponível
- Itens atuais de raridade menor são devolvidos ao inventário
- Slots com maldição ativa são ignorados

Hierarquia de raridade: `Comum < Incomum < Raro < Épico < Lendário`

### 10.1. Auto-Equip Geral
Além do auto-equip individual, no topo da lista central de **"SERVOS"** existe o botão **"⚡ AUTO-EQUIP GERAL"**.

Ao clicar:
- Todos os mineradores vivos na mina são processados sequencialmente.
- Cada um recebe o melhor equipamento disponível no inventário para cada slot.
- Um resumo no log lateral confirma as atribuições.

## 11. Loja

### 11.1. Loja de Servos (painel principal)

- Cards com atributos e tempo de expiração de cada oferta
- Ao comprar um refresh, ofertas antigas expiram mais cedo

### 11.2. Mercador de Itens (painel direito da aba Loja)

- Painel roxo no canto direito da aba **Loja**
- Mostra **3 a 5 itens aleatórios** — equipamentos e consumíveis
- Cada item tem preço = **2x o valor base** da raridade
- O mercador **reseta a cada 5 minutos de jogo** (o timer é exibido no painel)
- Botão `Comprar` individual por item

## 12. Upgrades

Os upgrades de estrutura da mina foram rebalanceados com custo progressivo:

| Upgrade | Nível 1 | Nível 2 | Nível 3 | Nível 4 |
|---------|---------|---------|---------|---------|
| Ferramentas | 2.500g | 19.000g | 90.000g | 500.000g |
| Alimentação | 2.000g | 14.000g | 72.000g | 380.000g |
| Segurança | 3.800g | 24.000g | 125.000g | 620.000g |
| Iluminação | 3.000g | 21.000g | 108.000g | 580.000g |
| Ventilação | 4.200g | 28.000g | 144.000g | 720.000g |

## 13. Inventário

A aba **Inventário** mostra todos os itens coletados.

Funcionalidades:

- **Tooltip ao passar o mouse**: mostra se o item é melhor ou pior que o equipado (seta verde = melhor, seta vermelha = pior)
- **Deleção em massa**: Deletar Comuns, Deletar Incomuns, Deletar Selecionados, Deletar Não Selecionados
- **Clique para selecionar** itens individualmente

## 14. Histórico de eventos

A aba **Histórico** registra os eventos mais marcantes com o horário cronológico do jogo:

```
[Ano 2, Mês 04]    NASCIMENTO: Kira#3 de Slag#1 e Flint#2
[Ano 3, Mês 07]    MORTO: Slag#1 (Velhice)
[Ano 5, Mês 01]    APOSENTADO: Flint#2
```

## 15. Pixel Art e visuais

- Personagens masculinos e femininos têm visuais diferentes (femininos com cabelos longos, volumosos e com brilho)
- Cada slot de equipamento muda visualmente o personagem (cor e forma) conforme a raridade do item
- Consumíveis ativos criam um brilho/aura colorida ao redor do servo
- Servos com **lua de mel** têm destaque especial na lista
- Bordas coloridas indicam o nível de raridade (Épico e Lendário possuem bordas mais grossas)

## 16. Eventos aleatórios

- rebelião, caverna secreta, fuga, doação, epidemia, veia lendária, acidente, mercado negro
- Eventos marcantes (mortes, itens raros) são registrados no **Histórico** com data

## 17. Prestígio

Quando o requisito de ouro total é atingido:

- A run pode ser reiniciada com bônus permanentes
- Conquistas, estatísticas permanentes e itens selecionados são preservados

## 18. Admin

O painel administrativo (`python admin.py`) controla regras dinâmicas sem editar código:

- economia, tempos, alimentação, doenças, chances de eventos
- resetar progresso, salvar/recarregar regras

## 19. Observações finais

Sequência sugerida de progressão:

1. Comece com 1 servo trabalhando na mina
2. Acumule ouro e compre mais servos
3. Forme pares para obter bebês e bônus de lua de mel
4. Colete itens e use o Auto-Equip
5. Compra itens no Mercador (aba Loja) quando aparecerem bons itens
6. Invista em Upgrades progressivamente (custam muito — planeje)
7. Use a aba Histórico para acompanhar a saga da sua mina
8. Faça Prestígio para runs mais poderosas
