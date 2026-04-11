# Mina dos Escravos Eternos

Simulador de gerenciamento idle/incremental com elementos de RPG. Gerencie uma mina subterrânea, compre e cruce escravos, extraia recursos raros e acumule riqueza enquanto lida com mortes, rebeliões e eventos imprevisíveis.

---

## Instalação e execução

```bash
# 1. Instale a dependência
pip install pygame

# ou usando o requirements.txt
pip install -r requirements.txt

# 2. Execute o jogo
python main.py
```

**Requisitos:** Python 3.11+ · pygame 2.5+

O jogo salva automaticamente na pasta de dados do usuário:

- **Windows:** `%APPDATA%\MinaDosEscravosEternos\save_eternal_mine.json`
- **macOS:** `~/Library/Application Support/MinaDosEscravosEternos/save_eternal_mine.json`
- **Linux:** `~/.local/share/MinaDosEscravosEternos/save_eternal_mine.json`

Se existir um `save_eternal_mine.json` antigo na pasta do projeto, ele ainda é carregado como compatibilidade.

---

## Estrutura dos arquivos

```
minerRules/
├── main.py           — Loop principal, inicialização do pygame
├── app_paths.py      — Caminhos de save e dados do usuário
├── eternal_mine.spec — Configuração do PyInstaller
├── build_windows.bat — Build do .exe no Windows
├── constants.py      — Todas as constantes e dados de balanceamento
├── slave.py          — Classe Escravo: atributos, mineração, herança
├── game_manager.py   — Lógica central: ciclos, eventos, save/load
├── renderer.py       — Interface pygame: painéis, abas, tooltip, animações
├── requirements.txt  — pygame>=2.5.0
├── requirements-build.txt — Dependências de build
└── save_eternal_mine.json  — Save legado opcional (compatibilidade)
```

---

## Gerar `.exe` no Windows

O build de Windows precisa ser executado em uma máquina Windows. Neste projeto, o comando já está preparado:

```bat
build_windows.bat
```

Isso gera:

```text
dist\MinaDosEscravosEternos.exe
```

Se o projeto estiver no GitHub, o workflow [`.github/workflows/build-windows-exe.yml`](/Users/lucasaquino/Documents/Lucas/minerRules/.github/workflows/build-windows-exe.yml) também gera e publica o artefato `.exe` em `windows-latest`.

---

## Layout da tela (1280 × 720)

```
┌─────────────────────────────────────────────────────────────────────┐
│  BARRA SUPERIOR — Ouro · Prestígio · Velocidade · Salvar · Acelerar │
├──────────────┬────────────────────────────┬─────────────────────────┤
│              │                            │                         │
│  MINA        │  LISTA DE ESCRAVOS         │  RECURSOS               │
│  VISUAL      │  (scrollável)              │  & ESTATÍSTICAS         │
│  (300px)     │  (520px)                   │  (460px)                │
│              │                            │                         │
├──────────────┴────────────────────────────┴─────────────────────────┤
│  ABAS: Loja │ Upgrades │ Breeding │ Mercado │ Prestígio │ Conquistas │
├─────────────────────────────────────────────────────────────────────┤
│  LOG DE EVENTOS (últimas 3 mensagens coloridas)                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Controles e interface

### Barra superior (sempre visível)

| Botão | Ação |
|---|---|
| **Acelerar** | Força todos os escravos a minerarem imediatamente. Custa `5g × nº de escravos`. |
| **Salvar** | Salva manualmente o progresso na pasta de dados do usuário. |
| **Pause** | Pausa o tempo de jogo. Eventos, mineração e breeding param. Borda vermelha = pausado. |
| **1x / 2x / 4x** | Velocidade do jogo. Borda dourada = velocidade ativa. A 4x, 5s reais = 20s de jogo. |

> O ouro no canto superior exibe o saldo atual. O valor `(+Xg inv.)` ao lado mostra o potencial de venda do inventário inteiro sem sair do painel.

---

### Painel esquerdo — Visualização da mina

Mostra até 25 escravos simultaneamente em uma grade 5×5. Cada escravo é representado por:

- **Círculo colorido** — azul (homem) ou rosa (mulher), com borda na cor da raridade geral.
- **Picareta animada** — oscila enquanto o escravo está minerando.
- **Barra de vida** — verde → amarelo → vermelho conforme a saúde diminui.
- **Flash branco** — pisca por 0,25s cada vez que o escravo conclui um ciclo de mineração.
- **Partículas douradas** — surgem ao redor do escravo no momento da mineração.

No rodapé do painel aparece o nível atual da mina e a contagem de escravos ativos e bebês.

---

### Painel central — Lista de escravos

Lista scrollável de todos os escravos vivos (adultos + bebês). Role com o **scroll do mouse** dentro do painel.

Cada linha mostra:

```
[M/F] Nome#ID          [████░░░░░░] vida/vidamax
 F:▓▓▓ V:▓░░ R:▓▓░ Fe:░░░ S:▓░░ L:░░░   [status]   [Vend.] [Par]
```

- **M/F** — gênero (azul = homem, rosa = mulher).
- **Barra de vida** — verde se > 50%, amarela se > 25%, vermelha abaixo.
- **6 mini-barras de atributos** — cada uma colorida pela raridade do atributo específico.
- **Status** — exibe `♥ Par` se em breeding, ou `Crescendo X%` se bebê.
- **Borda esquerda** — cor da raridade geral do escravo.
- **Borda ciano** — indica o escravo selecionado aguardando formação de par.

#### Botões por escravo

| Botão | Condição | Ação |
|---|---|---|
| **Vend.** | Adulto | Vende o escravo pelo preço calculado (ver seção Preços). |
| **Par** | Adulto sem par | Seleciona para breeding. Clique em "Par" de outro escravo compatível para formar o casal. |
| **Desfaz** | Adulto com par | Desfaz o par de breeding atual. |
| **Vend. Bebê** | Bebê | Vende o bebê antes de crescer. |

#### Tooltip — hover sobre um escravo

Posicione o cursor sobre a zona de nome/vida (fora dos botões) para ver o painel completo:

```
Nome#ID
Homem | Idade 24 | raro
────────────────────────
Força:       72  [raro]
Velocidade:  45  [incomum]
Resistência: 88  [épico]
Fertilidade: 31  [comum]
Sorte:       61  [raro]
Lealdade:    55  [incomum]
────────────────────────
Vida: 248/290
Tempo na mina: 4.2 min
Valor total encontrado: 1340g
Preço de venda: 187g
```

---

### Painel direito — Recursos e estatísticas

#### Inventário de recursos

Lista os 8 tipos de recursos com quantidade atual e valor unitário. Recursos com quantidade zero aparecem em cinza escuro.

**Botão Vender Tudo** — vende todo o inventário de uma vez pela soma dos valores unitários (×1,5 se Mercado Negro estiver ativo).

#### Estatísticas exibidas

| Métrica | Descrição |
|---|---|
| Escravos comprados | Total histórico de escravos adquiridos (compra + doação + nascimento). |
| Mortos totais | Acumulado de todas as run (persiste no prestígio). |
| Filhos nascidos | Total de filhos gerados pelo sistema de breeding. |
| Máx simultâneos | Pico de escravos vivos ao mesmo tempo. |
| Ouro total ganho | Acumulado de vendas de recursos e escravos. É este valor que desbloqueia o prestígio. |
| Intervalo minerar | Tempo atual de jogo entre ciclos = `MINING_INTERVAL ÷ bônus_ventilação`. |
| Mult. raridade | Multiplicador sobre as probabilidades de recursos raros = profundidade × iluminação × prestígio. |
| Mult. recursos | Multiplicador sobre quantidade de itens por ciclo = ferramentas × prestígio. |
| Risco acidente | Probabilidade de morte por acidente por ciclo = profundidade × (1 − redução_segurança). |
| Lealdade média | Média da lealdade de todos os escravos vivos. Abaixo de 50 aumenta chance de rebelião. |
| Bônus prestígio | Multiplicador global atual = 1 + (nº prestígios × 0,10). |

#### Aprofundar Mina

Exibe o próximo nível disponível e seu custo. O botão **Aprofundar Mina** fica verde quando há ouro suficiente.

---

## Abas do painel inferior

### Aba: Loja

Exibe 3–6 escravos disponíveis para compra, gerados aleatoriamente. Cada card mostra:

- Gênero, nome, raridade geral.
- Os 6 atributos com cores de raridade.
- Preço de compra.
- Botão **Comprar** (verde = pode comprar, cinza = ouro insuficiente).

**Botão Refresca** — gasta ouro para gerar novos escravos na loja. O custo começa em 50g e aumenta 1,5× a cada uso. A loja também se atualiza automaticamente a cada 5 minutos reais.

> Escravos lendários têm 4% de chance de aparecer na loja (todos os atributos entre 85–100).

---

### Aba: Upgrades

Cinco categorias de melhoria, cada uma com 4 níveis compráveis (além do nível 0 inicial):

#### Ferramentas
Aumenta a quantidade de recursos coletada por ciclo de mineração.

| Nível | Nome | Custo | Multiplicador |
|---|---|---|---|
| 0 | Mãos nuas | — | 1,0× |
| 1 | Picaretas simples | 200g | 1,3× |
| 2 | Picaretas de ferro | 800g | 1,7× |
| 3 | Picaretas de aço | 2.500g | 2,2× |
| 4 | Picaretas encantadas | 8.000g | 3,0× |

#### Alimentação
Reduz o desgaste diário (os escravos perdem vida mais devagar). O `bonus_vida` divide a taxa de desgaste.

| Nível | Nome | Custo | Redução de desgaste |
|---|---|---|---|
| 0 | Sobras | — | 1,0× (sem redução) |
| 1 | Rações básicas | 150g | 1,3× mais devagar |
| 2 | Refeições decentes | 600g | 1,7× mais devagar |
| 3 | Comida nutritiva | 2.000g | 2,2× mais devagar |
| 4 | Banquete | 6.000g | 3,0× mais devagar |

#### Segurança
Reduz dois riscos independentes: mortes por acidente e chance de rebelião.

| Nível | Nome | Custo | Red. morte | Red. rebelião |
|---|---|---|---|---|
| 0 | Nenhuma | — | 0% | 0% |
| 1 | Guardas básicos | 300g | 15% | 10% |
| 2 | Correntes reforçadas | 1.000g | 30% | 20% |
| 3 | Sistema de vigilância | 3.500g | 50% | 40% |
| 4 | Fortaleza subterrânea | 10.000g | 70% | 60% |

#### Iluminação
Aumenta a efetividade do atributo Sorte de cada escravo, favorecendo recursos mais raros.

| Nível | Nome | Custo | Mult. sorte |
|---|---|---|---|
| 0 | Escuro total | — | 1,0× |
| 1 | Tochas de madeira | 250g | 1,2× |
| 2 | Lanternas a óleo | 900g | 1,5× |
| 3 | Luminárias de cristal | 3.000g | 2,0× |
| 4 | Luz mágica eterna | 9.000g | 2,8× |

#### Ventilação
Divide o intervalo de mineração, fazendo os ciclos acontecerem mais rápido.

| Nível | Nome | Custo | Divisor do intervalo |
|---|---|---|---|
| 0 | Sufocante | — | ÷1,00 (5s padrão) |
| 1 | Buracos de ar | 350g | ÷1,15 (≈4,3s) |
| 2 | Dutos de ventilação | 1.200g | ÷1,35 (≈3,7s) |
| 3 | Ventiladores mecânicos | 4.000g | ÷1,60 (≈3,1s) |
| 4 | Sistema pressurizado | 12.000g | ÷2,00 (2,5s) |

---

### Aba: Breeding

Sistema de reprodução entre pares de escravos.

**Como formar um par:**
1. Na lista de escravos (painel central), clique em **Par** no escravo masculino.
2. O escravo fica destacado com borda ciana.
3. Clique em **Par** em uma escrava feminina.
4. O par é formado e aparece na aba Breeding.

**Mecânica de reprodução:**
- A cada `BREEDING_INTERVAL` (30s de jogo), o sistema verifica cada par.
- Chance de gravidez = `(fertilidade_média / 100) × 0,35 + bônus_lealdade`.
  - Bônus lealdade = `(lealdade_média_do_par / 100) × 0,2`.
  - Exemplo: dois escravos com fertilidade 70 e lealdade 80 → chance ≈ 40% por verificação.
- Ao nascer, o bebê aparece na mina e na lista com status **Crescendo X%**.
- Após `GROWTH_TIME` (180s de jogo = 3 minutos a 1×), o bebê vira adulto e começa a minerar.

**Herança de atributos:**
- Cada atributo do filho = `média(pai, mãe) ± variação aleatória (−10 a +10)`.
- 5% de chance de **mutação positiva**: um atributo aleatório ganha +10 a +25 pontos.
- Estratégia: cruzar dois escravos lendários gera filhos com atributos próximos de 85–100, potencialmente lendários.

**Botão Desfazer** — rompe o par. Os dois ficam livres para novos pares.

---

### Aba: Mercado

Venda seletiva de recursos com contexto visual do Mercado Negro.

- Lista todos os 8 recursos com quantidade atual e valor total.
- Botão **Vender** por recurso — vende todo o estoque daquele item.
- Botão **Vender Tudo** — vende o inventário inteiro.
- Quando o **Mercado Negro** está ativo, todos os preços ficam 1,5× maiores por 60 segundos de jogo. O tempo restante aparece em ciano.

---

### Aba: Prestígio

Mecanismo de fim de jogo que reseta a run em troca de bônus permanentes.

**Requisito:** acumular **100.000g de ouro total ganho** (soma histórica de todas as vendas da run atual).

**O que acontece no prestígio:**
1. A mina é resetada (escravos, inventário, upgrades e profundidade voltam ao início).
2. O contador de prestigios aumenta em 1.
3. Você recebe `1 + nº_prestígios` **Almas Eternas** (moeda permanente).
4. O **bônus global** aumenta em 10%: `bônus = 1 + (prestígios × 0,10)`.
   - Este bônus multiplica simultaneamente `mult_raridade` e `mult_recursos`.
5. O ouro inicial da nova run = `250 + almas_eternas × 20g`.

**O que persiste entre prestígios:**
- Estatísticas acumuladas (mortos, filhos, ouro total, etc.)
- Conquistas desbloqueadas
- Número de prestígios e Almas Eternas
- Bônus global

A barra de progresso exibe `ouro_total_ganho / 100.000`.

---

### Aba: Conquistas

15 conquistas rastreadas automaticamente. Conquistas desbloqueadas ficam com borda dourada e texto visível.

| Conquista | Condição |
|---|---|
| Primeiro Escravo | Comprar o 1º escravo |
| Mão de Obra | 5 escravos vivos ao mesmo tempo |
| Exército | 20 escravos ao mesmo tempo |
| Legião Eterna | 50 escravos ao mesmo tempo |
| Faísca de Ouro | Encontrar Ouro pela 1ª vez |
| Coração de Diamante | Encontrar um Diamante |
| Sangue de Pedra | Encontrar um Rubi |
| Toque Lendário | Encontrar Adamantita |
| Comerciante | Ter 1.000g de saldo |
| Magnata da Mina | Ter 50.000g de saldo |
| Berço da Mina | 1º filho nascido |
| Cemitério Subterrâneo | 100 mortes totais |
| Sobrevivente | Um escravo com 30 min de jogo sem morrer |
| Renascimento | 1º prestígio |
| Eterno | 5 prestígios |

---

## Sistema de escravos — detalhe completo

### Atributos e raridades

Cada atributo é um inteiro de **1 a 100**, gerado com a seguinte distribuição de probabilidade:

| Raridade | Intervalo | Prob. por atributo | Cor |
|---|---|---|---|
| Lendário | 95–100 | 1% | Dourado |
| Épico | 80–94 | 7% | Roxo |
| Raro | 60–79 | 17% | Azul |
| Incomum | 40–59 | 30% | Verde |
| Comum | 1–39 | 45% | Cinza |

A **raridade geral** do escravo é baseada na média dos 6 atributos e determina a cor da borda na lista e na mina.

### Efeito de cada atributo

| Atributo | Abrev. | Efeito direto |
|---|---|---|
| **Força** | F | Quantidade de recursos por ciclo: base `1 + força÷30`, +1 ou +2 aleatório. |
| **Velocidade** | V | Usado internamente (expansão futura). Peso 1,0 no preço. |
| **Resistência** | R | Vida máxima: `100 + resistência×2 − penalidade_idade`. Taxa de desgaste: `0,5 ÷ (resistência×0,1 + 1)`. Escravo com R=100 tem vida ≈ 300 e perde ~0,045/s. |
| **Fertilidade** | Fe | Componente principal da chance de ter filho no breeding. |
| **Sorte** | S | Favorece recursos raros: eleva probabilidade de raros e reduz a de comuns. Amplificado pela Iluminação. |
| **Lealdade** | L | Baixa lealdade média aumenta a chance de rebelião e fuga. Peso menor no preço. |

### Cálculo do preço

```
soma_ponderada = (Força×1,2 + Velocidade×1,0 + Resistência×0,8 +
                  Fertilidade×0,6 + Sorte×0,9 + Lealdade×0,5) ÷ 6

mult_raridade  = 0,7 (comum) | 1,0 (incomum) | 1,4 (raro) | 2,0 (épico) | 3,0 (lendário)
mult_idade     = 0,8 (< 20 anos) | 1,2 (20–29) | 1,0 (30–39) | 0,7 (40+)
mult_vida      = 0,5 + (vida_atual ÷ vida_max) × 0,5

preço = max(10, int(100 + soma_ponderada × mult_raridade × mult_idade × mult_vida))
```

No **Mercado Negro**: preço final × 1,5.

### Causas de morte

| Causa | Condição |
|---|---|
| **Exaustão** | `vida` chega a 0 pelo desgaste natural ao longo do tempo. |
| **Acidente na mina** | Verificado após cada ciclo de mineração. Prob. = `risco_profundidade × (1 − red_segurança)`. |
| **Rebelião** | Evento aleatório que mata ~20% dos escravos vivos. |
| **Fuga** | Evento aleatório que remove o escravo com menor lealdade. |

### Ciclo de vida típico (estimativas a 1× sem upgrades)

- **Resistência 10** → vida ≈ 120 → dura ≈ 3–4 minutos reais de jogo.
- **Resistência 50** → vida ≈ 200 → dura ≈ 40 minutos reais.
- **Resistência 100** → vida ≈ 300 → dura ≈ 110 minutos reais.
- Alimentação nível 4 triplica essas durações.

---

## Recursos — probabilidades e valores

| Recurso | Prob. base | Valor/un. | Raridade |
|---|---|---|---|
| Terra | 40% | 1g | Muito comum |
| Pedra | 25% | 3g | Comum |
| Ferro | 15% | 8g | Frequente |
| Ouro | 8% | 25g | Incomum |
| Esmeralda | 5% | 80g | Raro |
| Diamante | 4% | 200g | Raro |
| Rubi | 2,5% | 350g | Muito raro |
| Adamantita | 0,5% | 1.500g | Lendário |

> As probabilidades acima são **modificadas** pelo atributo Sorte do escravo, pela Iluminação e pela profundidade da mina. Sorte alta e iluminação máxima podem aumentar a chance de Adamantita em até 20× em relação à base.

**Fórmula de ajuste de probabilidade por Sorte:**
- Para recursos raros (prob < 10%): `prob × (1 + sorte_efetiva × 2) × mult_raridade`
- Para recursos comuns (prob > 30%): `prob × max(0,3; 1 − sorte_efetiva × 0,5)`
- Sorte efetiva = `(sorte ÷ 100) × mult_iluminação`

---

## Profundidades da mina

| Nível | Nome | Custo | Mult. raridade | Risco/ciclo |
|---|---|---|---|---|
| 0 | Superfície | — | 1,0× | 1,0% |
| 1 | Nível 1 — Raso | 500g | 1,3× | 2,0% |
| 2 | Nível 2 — Médio | 2.000g | 1,8× | 4,0% |
| 3 | Nível 3 — Fundo | 7.000g | 2,5× | 7,0% |
| 4 | Nível 4 — Abismo | 20.000g | 4,0× | 12,0% |
| 5 | Nível 5 — Núcleo | 60.000g | 7,0× | 20,0% |

> No Nível 5 com Segurança nível 0, cada ciclo tem 20% de chance de matar o escravo por acidente — planeje a segurança antes de aprofundar.

---

## Eventos aleatórios

O jogo verifica eventos a cada **45 segundos reais** (independente da velocidade de jogo). No máximo um evento por verificação.

| Evento | Tipo | Chance base | Efeito |
|---|---|---|---|
| **Rebelião** | Negativo | Variável* | Mata ~20% dos escravos, rouba até 200g. |
| **Escravo Fugiu** | Negativo | Variável* | Remove o escravo com menor lealdade. |
| **Acidente na Mina** | Negativo | 8% | Mata ~10% dos escravos (ao menos 1). |
| **Epidemia** | Negativo | 6% | Todos os escravos perdem 20–50 pontos de vida. |
| **Caverna Secreta** | Positivo | 5% | Adiciona 5–20 unidades de Ouro, Esmeralda e Diamante. |
| **Mercado Negro** | Neutro | 5% | Preços de venda +50% por 60s de jogo. |
| **Doação Inesperada** | Positivo | 4% | Um escravo aleatório é doado gratuitamente. |
| **Veia Lendária** | Positivo | 3% | Adiciona 1–3 Adamantita ao inventário. |

\* **Rebelião e Fuga** têm chances dinâmicas baseadas na lealdade média:
- Rebelião: `(0,02 + (50 − lealdade_média) × 0,002) × (1 − red_rebelião_segurança)`
- Fuga: `0,05 + max(0, 50 − lealdade_média) × 0,001`

Com lealdade média 20 e segurança nível 0, a chance de rebelião por verificação é ~8%.

---

## Save / Load

### Automático
O jogo salva a cada **30 segundos reais** na pasta de dados do usuário. Uma mensagem cinza aparece no log ao salvar.

### Manual
Botão **Salvar** na barra superior.

### Ao fechar
A janela (`X`) aciona um save final antes de encerrar.

### Ao iniciar
Se existir um save na pasta de dados do usuário, ele é carregado automaticamente. Se não houver, o tutorial aparece.

### O que é salvo
Ouro, inventário, nível da mina, upgrades, todos os escravos vivos com seus atributos e estatísticas individuais, pares de breeding, estatísticas globais, conquistas, dados de prestígio.

### Novo jogo
Delete o arquivo de save da pasta de dados do usuário e reinicie.

---

## Balanceamento e configuração

Todas as constantes de balanceamento estão no topo de `constants.py` e podem ser editadas sem afetar o restante do código.

### Tempos (em segundos)

```python
# constants.py

MINING_INTERVAL   = 5.0   # Intervalo base entre ciclos de mineração.
                           # A ventilação divide esse valor.

BREEDING_INTERVAL = 30.0  # Intervalo entre verificações de reprodução.
                           # Diminua para filhos mais frequentes.

GROWTH_TIME       = 180.0 # Tempo para bebê virar adulto (3 min a 1×).
                           # 180 ÷ velocidade_jogo = tempo real.

AUTOSAVE_INTERVAL = 30.0  # Tempo real entre salvamentos automáticos.

EVENT_INTERVAL    = 45.0  # Tempo real entre tentativas de evento aleatório.

SHOP_REFRESH_TIME = 300.0 # Tempo real entre refreshes automáticos da loja.
```

### Outros parâmetros relevantes

| Constante | Local | Descrição |
|---|---|---|
| `BASE_SLAVE_PRICE` | `constants.py` | Preço mínimo base de um escravo (padrão: 100g). |
| `PRESTIGE_GOLD_REQ` | `constants.py` | Ouro total ganho para desbloquear prestígio (padrão: 100.000g). |
| `PRESTIGE_BONUS_STEP` | `constants.py` | Bônus por prestígio (padrão: 0,10 = +10%). |
| `self.ouro = 250.0` | `game_manager.py` — `_init_state` | Ouro inicial de cada run. |
| `self.custo_refresco = 50` | `game_manager.py` — `_init_state` | Custo inicial do refresh da loja. |

### Exemplo: modo mais rápido para testes

```python
# constants.py
MINING_INTERVAL   = 1.0   # mineração a cada 1 segundo
BREEDING_INTERVAL = 10.0  # filho a cada ~15 segundos
GROWTH_TIME       = 30.0  # bebê adulto em 30s
EVENT_INTERVAL    = 15.0  # evento a cada 15s reais
```

---

## Decisões estratégicas

O jogo foi desenhado para criar dilemas constantes. Alguns exemplos:

**Ferramentas vs. Ventilação**
Ferramentas multiplicam o que cada ciclo produz; Ventilação aumenta quantos ciclos acontecem por minuto. Com 1 escravo, ambas são equivalentes. Com 10 escravos, Ventilação é multiplicada por cada um deles — tendência a valer mais cedo.

**Segurança vs. Profundidade**
Aprofundar sem segurança a partir do Nível 3 começa a matar escravos rapidamente. A pergunta é: vale perder 2 escravos para ganhar 4× mais raros?

**Breeding vs. Compra**
Filhos são gratuitos mas demoram para crescer. Um escravo comprado começa a trabalhar imediatamente. Se você tem um par com atributos épicos, o filho provável supera qualquer compra da loja — mas leva tempo.

**Vender escravo vs. Manter**
Um escravo fraco vale ~80g na loja. Em 10 ciclos (50s), ele provavelmente produz menos que isso. Mas se ele for o único homem ou mulher disponível para breeding, removê-lo quebra a linha de produção.

**Prestígio precoce vs. tardio**
Prestigiar cedo garante o bônus mais rápido, mas você começa do zero mais vezes. Prestigiar tarde significa uma run mais longa com bônus acumulado maior — especialmente relevante para Adamantita e conquistas de late-game.

---

## Arquitetura técnica

```
main.py
  └── cria GameManager + Renderer
      └── loop: handle_event → update(delta) → draw()

GameManager.update(delta, now_real)
  ├── avança tempo_jogo += delta
  ├── para cada Escravo: update() + pode_minerar() → executar_mineracao()
  ├── morte por acidente verificada após cada ciclo
  ├── limpeza de escravos mortos
  ├── _update_breeding() a cada BREEDING_INTERVAL de jogo
  ├── _tentar_evento() a cada EVENT_INTERVAL real
  └── save() a cada AUTOSAVE_INTERVAL real

Escravo.update(delta)
  ├── bebê: decrementa tempo_crescimento
  └── adulto: perde vida pelo desgaste (taxa ÷ alimentação)

Renderer.draw()
  ├── _draw_topbar(): ouro, botões, velocidade
  ├── _draw_left(): cave surface + escravos animados + partículas
  ├── _draw_center(): lista scrollável + botões dinâmicos
  ├── _draw_right(): inventário + stats + aprofundar
  ├── _draw_bottom(): aba atual (loja/upgrades/breeding/mercado/prestígio/conquistas)
  ├── _draw_log(): últimas 3 mensagens
  ├── _draw_tooltip(): overlay sobre escravo em hover
  └── _draw_notif() / _draw_tutorial(): modais
```

**Tempo duplo:** o jogo usa dois relógios independentes:
- **`tempo_jogo`** — avança com `delta_real × velocidade`. Controla mineração, breeding, crescimento e desgaste. Pausável.
- **`time.time()`** — tempo real do sistema. Controla autosave e eventos aleatórios. Não é afetado pela velocidade nem pela pausa.

Isso garante que pausar o jogo não adie o autosave, e que acelerar para 4× não multiplica a frequência de eventos.
