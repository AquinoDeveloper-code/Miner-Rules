# Manual Completo — Mina dos Servos Eternos

## 1. Visão geral

`Mina dos Servos Eternos` é um idle game de gerenciamento contínuo. O jogador opera uma mina subterrânea, contrata e vende servos, organiza casais para reprodução, equipa trabalhadores, reage a eventos aleatórios e escala a operação por profundidade, upgrades e prestígio.

O jogo mistura:

- gestão incremental
- progressão por ciclos cronológicos (Anos e Meses)
- simulação de atributos e humor dos servos
- sistema de entrega de recursos com ataques em tempo real
- segurança com guardas e equipamentos
- automação estratégica via Gerentes (Capatazes)
- risco sistêmico
- sistema familiar com lua de mel e cooldown de reprodução

## 2. Ambientação e proposta

O jogo apresenta uma mina brutal e decadente, sustentada por mão de obra explorada, onde riqueza e sobrevivência entram em conflito o tempo inteiro. A progressão existe em camadas:

- camada operacional: manter a mina lucrando
- camada tática: escolher quem comprar, vender, equipar e aposentar
- camada sistêmica: controlar fome, doença, rebelião, eventos e lotação
- camada familiar: gerenciar pares, lua de mel, cooldowns e nascimentos
- camada logística: proteger entregas em trânsito com guardas
- camada estratégica: contratar gerentes para automatizar decisões
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
  - constantes de entrega, ataques, guardas, vendedores e gerentes
  - balanceamento base e custos de upgrades

- `src/contexts/gameplay/domain/slave.py`
  - entidade `Escravo` com atributos, humor, honeymoon, breeding cooldown
  - envelhecimento, stamina, mineração, serialização

- `src/contexts/gameplay/domain/guard.py`
  - entidade `Delivery` — recurso em trânsito com timer real e lógica de ataque
  - entidade `Guarda` — protetor com 3 atributos, 6 slots de equipamento, serialização

- `src/contexts/gameplay/domain/manager.py`
  - entidade `Gerente` — capataz com 4 tiers, 3 modos de autonomia
  - método `analisar(estado)` — retorna fila de recomendações tipadas
  - 12 critérios configuráveis via `cfg_*`

- `src/contexts/gameplay/application/game_manager.py`
  - orquestra o estado global da run
  - loja de servos, loja de itens do mercador, loja de itens de guardas
  - sistema de entrega (`_update_deliveries`) com delta real
  - vendedor ambulante com timer e qualidades
  - breeding com lua de mel e cooldown
  - eventos, upgrades, prestígio, save/load
  - cronômetro de Anos e Meses, histórico de eventos marcantes
  - sistema de gerentes: snapshot, fila de recomendações, execução automática

- `src/ui/pygame/renderer.py`
  - interface do jogo com pixel art
  - log com scroll e clip real
  - 10 abas: Loja, Upgrades, Breeding, Mercado, Prestígio, Conquistas, Histórico, Inventário, Guardas, Gerência

## 5. Persistência

O save usa SQLite (`save_eternal_mine.db`). Regras dinâmicas ficam em `game_rules.json`.

Guardas, itens de guarda e gerentes são **preservados no Prestígio**.

## 6. Interface do jogo

### 6.1. Barra superior

- **Título** + **Ano X, Mês Y** em tempo real (1 Ano = 50s de jogo)
- **Ouro atual**
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
- Estrada de Entrega na parte inferior com carroças em trânsito e ataques animados

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
- **Fila de Entregas**: barras de progresso de cada recurso em trânsito
- **Botão do Vendedor Ambulante** (quando disponível): abre o modal de compra

### 6.6. Painel inferior por abas

| Aba | O que faz |
|-----|-----------|
| `Loja` | Comprar servos + **Mercador de Itens** (canto direito) |
| `Upgrades` | Melhorias de ferramentas, segurança, iluminação, ventilação, alimentação |
| `Breeding` | Gerenciar pares ativos e reprodução |
| `Mercado` | Vender recursos em lote |
| `Prestígio` | Resetar run com bônus permanentes |
| `Conquistas` | Ver conquistas desbloqueadas |
| `Histórico` | Timeline de eventos marcantes (mortes, nascimentos, itens raros) |
| `Inventário` | Ver e gerenciar todos os itens da mochila |
| `Guardas` | Contratar, equipar e gerenciar guardas de entrega |
| `Gerência` | Contratar gerentes, ver recomendações e configurar automação |

## 7. Sistema de tempo cronológico

- **1 Ano de jogo = 50 segundos reais** (na velocidade 1x)
- **1 Mês de jogo = ≈ 4.16 segundos** (1 Ano ÷ 12)
- O tempo atual aparece na **barra superior**: `Ano X, Mês Y`

### Aba Histórico

A aba **Histórico** mostra os eventos mais marcantes com timestamp:

- Rosa = Nascimentos
- Vermelho = Mortes
- Dourado = Itens lendários/míticos
- Laranja = Doenças graves e aposentadorias

## 8. Sistema de servos

### 8.1. Atributos

- força, velocidade, resistência, fertilidade, sorte, lealdade

### 8.2. Humor e Status do servo

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

### 8.3. Stamina

- Vai de 0 a 100%
- Ao atingir 0, o servo entra em **Repouso automático**
- Ao atingir 100% no repouso, **volta ao trabalho automaticamente**
- O botão **Voltar à Mina** fica disponível com > 10% de stamina

### 8.4. Morte e aposentadoria

Quando um servo morre ou é aposentado:

- Um aviso `[MORTO] causa` ou `[APOSENTADO]` aparece no modal de detalhes
- O evento é registrado no **Histórico** com Ano e Mês exatos

## 9. Sistema de Entrega de Recursos

Ao terminar um ciclo de mineração, o recurso não vai diretamente ao inventário — ele entra em **trânsito**.

### 9.1. Tempo de entrega

```
tempo = max(2s, 15s - (velocidade_efetiva / 100) × 8 - nivel_mina × 0.5)
```

- Servos mais velozes e minas mais profundas entregam mais rápido
- O mínimo absoluto é 2 segundos reais

### 9.2. Ataques durante o trânsito

A cada 5 segundos reais, cada entrega em trânsito pode ser atacada:

| Atacante | Probabilidade base | Recuperação |
|----------|-------------------|-------------|
| Alcateia de Lobos | 40% | 75% |
| Urso Gigante | 20% | 50% |
| Ladrões | 25% | 50% |
| Horda de Orcs | 15% | 15% |

- A chance total de ataque por check é `DELIVERY_ATTACK_RATE` (configurável)
- Guardas reduzem a chance de ataque e aumentam a taxa de recuperação

### 9.3. Fila de Entregas

O painel direito exibe todas as entregas com:
- Nome do servo e recurso
- Barra de progresso (tempo restante)
- Status visual em caso de ataque

### 9.4. Carregamento de save

Entregas em trânsito no momento do save são concluídas automaticamente ao recarregar — nenhum recurso é perdido entre sessões.

## 10. Sistema de Guardas

A aba **Guardas** permite contratar e gerenciar protetores para as entregas.

### 10.1. Atributos do guarda

| Atributo | Efeito |
|----------|--------|
| Força | Aumenta chance de recuperar recurso em caso de ataque |
| Resistência | Reduz perda em ataques não recuperados |
| Agilidade | Reduz probabilidade de ser atacado |

### 10.2. Contribuição coletiva

Todos os guardas contribuem em conjunto:

```
Redução de ataque   = min(60%, soma_agilidade / 400)
Bônus recuperação   = min(35%, soma_força / 300)
```

Os percentuais finais aparecem no rodapé da aba Guardas.

### 10.3. Tiers de guarda

| Tier | Raridade | Intervalo de atributos |
|------|----------|----------------------|
| Velho | Comum | 5–20 |
| Básico | Incomum | 15–40 |
| Normal | Raro | 30–60 |
| Épico | Épico | 55–80 |
| Lendário | Lendário | 75–100 |

Máximo de **10 guardas** simultâneos.

### 10.4. Equipamentos de guarda

6 slots por guarda: `capacete`, `peitoral`, `calças`, `botas`, `espada`, `arco`

- 17 itens disponíveis com bônus de força, resistência ou agilidade
- Compra via Loja de Equipamentos na aba Guardas (rotaciona periodicamente)
- Vendedor Ambulante também pode oferecer itens de guarda
- Auto-equipar por raridade disponível no modal de detalhe do guarda

### 10.5. Modal de detalhe do guarda

Clique em `Det.` na lista de guardas para abrir:
- Coluna 1: atributos base e efetivos, contribuição individual, poder total
- Coluna 2: slots de equipamento com botão de desequipar
- Coluna 3: inventário de itens de guarda (filtrado pelo slot selecionado)

### 10.6. Presistência no prestígio

Guardas e seus equipamentos **não são perdidos** ao fazer prestígio.

## 11. Vendedor Ambulante

Vendedores aparecem aleatoriamente durante o jogo. Quando disponível, um botão aparece no **painel direito**.

### 11.1. Tipos de vendedor

| Qualidade | Nome | Tipo de oferta |
|-----------|------|----------------|
| `barato` | Mercador de Bugigangas | Itens comuns a preços baixos |
| `raro` | Comerciante Raro | Itens raros e épicos |
| `ruim` | Mascate Duvidoso | Itens de baixa qualidade |
| `maldito` | Vendedor das Sombras | Itens amaldiçoados |

### 11.2. Funcionamento

- Oferece 3 itens (mix de itens de servo e de guarda)
- Timer visível de quanto tempo o vendedor permanece
- Fechar o modal não cancela o vendedor — ele some quando o timer zerar
- ESC ou botão `[FECHAR]` fecha o modal sem dispensar o vendedor

## 12. Sistema de Gerentes (Capatazes)

A aba **Gerência** permite contratar gerentes que analisam o estado da mina e sugerem ou executam ações automaticamente.

### 12.1. Tiers de gerente

| Tier | Custo | Eficiência | Intervalo | Destaques |
|------|-------|-----------|-----------|-----------|
| Júnior | 15.000g | 50% | 90s | Problemas básicos de stamina e venda |
| Experiente | 60.000g | 75% | 60s | Equipamentos, doenças, otimização |
| Mestre | 250.000g | 90% | 30s | Breeding, guardas, maldições |
| Lendário | 1.000.000g | 100% | 15s | IA perfeita — mercado negro, risco total |

- Máximo de **3 gerentes** simultâneos (1 por tier, sem duplicatas)
- Gerentes são preservados no Prestígio

### 12.2. Eficiência

Gerentes de menor eficiência veem apenas um **subconjunto aleatório** dos problemas:
- Júnior: ~50% dos problemas detectados por análise
- Lendário: 100% (vê tudo)

### 12.3. Modos de autonomia

| Modo | Comportamento |
|------|--------------|
| `Só Recomenda` | Gera recomendações na fila — o jogador decide |
| `Semi-Auto` | Executa ações de urgência alta, recomenda as demais |
| `Automático` | Executa todas as ações sem intervenção |

Para alterar o modo, clique em **Config** na linha do gerente e selecione o modo desejado no modal.

### 12.4. Tipos de recomendação

| Tipo | Urgência | Descrição |
|------|----------|-----------|
| `stamina_baixa` | Média | ≥40% dos servos com stamina < 30% |
| `vender_idoso` | Média | Servo idoso e desgastado |
| `aposentar` | Baixa | Servo atingiu a idade de aposentadoria |
| `curar_doente` | Média | Servo doente com poção disponível |
| `quebrar_maldicao` | Média | Servo amaldiçoado com Reza disponível |
| `comprar_escravo` | Baixa | Bom candidato na loja com slot livre |
| `equip_auto` | Baixa | Itens sem uso no inventário |
| `contratar_guarda` | Média | Mina avançada sem guardas |
| `equip_guardas` | Baixa | Itens de guarda sem uso |
| `vender_fraco` | Baixa | Servo com atributos muito abaixo do limiar |
| `mercado_negro` | Média | Evento de mercado negro ativo |
| `vender_doente` | Alta | Servo grave — doente + stamina crítica |

### 12.5. Fila de recomendações

Exibida na metade esquerda da aba Gerência:

- Cada rec tem cor de urgência (cinza / laranja / vermelho)
- **Executar**: aplica a ação imediatamente
- **Ignorar**: descarta a recomendação da fila
- Fila mantém no máximo 20 entradas; recomendações duplicadas por tipo não se acumulam

### 12.6. Modal de configuração

Clique em **Config** em qualquer gerente contratado:

- **Autonomia**: alterna entre os 3 modos
- **Venda Automática**: toggles para idosos, fracos e doentes + limiares numéricos
- **Compra Automática**: toggle + atributo mínimo + idade máxima
- **Descanso**: toggle + stamina mínima para forçar descanso
- **Outros**: auto-equip de servos e de guardas
- **Estatísticas**: intervalo, recomendações geradas e ações executadas

## 13. Sistema familiar (Breeding)

### 13.1. Formando um par

- Clique em `Par` em um servo masculino, depois `Par` em um feminino
- Ao formar um casal, **ambos ganham Lua de Mel por 9 meses de jogo (37.5s)**

### 13.2. Lua de Mel

Durante a lua de mel:

- **+20% em Força, Velocidade, Resistência, Sorte e Lealdade**
- **+30% em Fertilidade**
- O status exibido será **"Muito Feliz"**
- A lista de servos exibe `♥ Lua de mel`

### 13.3. Cooldown de reprodução (2 anos)

Após um nascimento:

- Pai e mãe ficam com **cooldown de 2 anos de jogo (100s)** — não podem ter outro filho nesse período

### 13.4. Bebês

- Nascem em estado de bebê — não mineraram
- Crescem automaticamente após o tempo configurado
- Aparecem na lista com indicador de crescimento `Cres.X%`

## 14. Auto-Equip

No modal de detalhe do servo, existe o botão **⚡ Auto-Equip (Por Raridade)**.

Ao clicar:

- O sistema varre todos os itens do inventário
- Para cada slot, equipa o item de **maior raridade** disponível
- Itens atuais de raridade menor são devolvidos ao inventário
- Slots com maldição ativa são ignorados

Hierarquia de raridade: `Comum < Incomum < Raro < Épico < Lendário`

### 14.1. Auto-Equip Geral

No topo da lista central existe o botão **"⚡ AUTO-EQUIP GERAL"** — processa todos os mineradores vivos sequencialmente.

## 15. Loja

### 15.1. Loja de Servos

- Cards com atributos e tempo de expiração de cada oferta

### 15.2. Mercador de Itens (painel direito da aba Loja)

- 3 a 5 itens aleatórios — equipamentos e consumíveis
- Preço = **2× o valor base** da raridade
- Reseta a cada 5 minutos de jogo

### 15.3. Vendedor Ambulante

Ver seção 11.

### 15.4. Loja de Itens de Guarda (aba Guardas)

- Painel no lado direito da aba Guardas
- Rotaciona periodicamente com itens aleatórios
- Preços baseados na raridade do item

## 16. Upgrades

| Upgrade | Nível 1 | Nível 2 | Nível 3 | Nível 4 |
|---------|---------|---------|---------|---------|
| Ferramentas | 2.500g | 19.000g | 90.000g | 500.000g |
| Alimentação | 2.000g | 14.000g | 72.000g | 380.000g |
| Segurança | 3.800g | 24.000g | 125.000g | 620.000g |
| Iluminação | 3.000g | 21.000g | 108.000g | 580.000g |
| Ventilação | 4.200g | 28.000g | 144.000g | 720.000g |

## 17. Inventário

A aba **Inventário** mostra todos os itens coletados.

Funcionalidades:

- **Tooltip ao passar o mouse**: comparação com item equipado (seta verde = melhor, seta vermelha = pior)
- **Deleção em massa**: Deletar Comuns, Deletar Incomuns, Deletar Selecionados, Deletar Não Selecionados
- **Clique para selecionar** itens individualmente

## 18. Eventos aleatórios

- rebelião, caverna secreta, fuga, doação, epidemia, veia lendária, acidente, mercado negro
- Eventos marcantes (mortes, itens raros) são registrados no **Histórico** com data

## 19. Prestígio

Quando o requisito de ouro total é atingido:

- A run pode ser reiniciada com bônus permanentes
- Conquistas, estatísticas permanentes e itens selecionados são preservados
- **Guardas, itens de guarda e gerentes são preservados**

## 20. Admin

O painel administrativo (`python admin.py`) controla regras dinâmicas sem editar código:

- economia, tempos, alimentação, doenças, chances de eventos
- resetar progresso, salvar/recarregar regras

## 21. Atalhos e controles

| Ação | Como fazer |
|------|-----------|
| Scroll no log | Roda do mouse sobre a coluna EVENTOS |
| Fechar modal | ESC (cascata: Vendedor → Gerente → Guarda → Servo) |
| Detalhe do servo | Botão `Det.` na lista |
| Formar par | `Par` em M, depois `Par` em F |
| Auto-equip servo | Modal do servo → `⚡ Auto-Equip` |
| Auto-equip Geral | Topo da Lista de Servos → `⚡ AUTO-EQUIP GERAL` |
| Detalhe do guarda | Aba Guardas → `Det.` |
| Config do gerente | Aba Gerência → `Config` |
| Executar recomendação | Aba Gerência → `Exec.` na rec desejada |
| Abrir Vendedor | Painel direito → botão Vendedor (quando disponível) |

## 22. Sequência de progressão sugerida

1. Comece com 1 servo trabalhando na mina
2. Acumule ouro e compre mais servos
3. Forme pares para obter bebês e bônus de lua de mel
4. Colete itens e use o Auto-Equip
5. Compre itens no Mercador (aba Loja) e no Vendedor Ambulante
6. Aprofunde a mina — recursos mais raros mas mais ataques
7. Contrate guardas para proteger as entregas
8. Invista em Upgrades progressivamente
9. Contrate um Gerente Júnior para começar a automatizar
10. Use a aba Histórico para acompanhar a saga da sua mina
11. Escale para gerentes de tier maior conforme o ouro cresce
12. Faça Prestígio para runs mais poderosas, mantendo guardas e gerentes
