# Changelog — Mina dos Servos Eternos

## [1.3.0] — 2026-04-12

### ✨ Novas Funcionalidades

#### Sistema de Entrega (Deliveries)
- Recursos minerados não vão mais diretamente ao inventário — percorrem um trajeto real com tempo calculado
- Tempo de entrega baseado na velocidade do servo e no nível da mina (`max(2s, 15s - velocidade/100*8 - nivel*0.5)`)
- Fila de entregas exibida no painel direito com barras de progresso individuais
- Ao carregar um save, entregas em trânsito são automaticamente concluídas

#### Ataques às Entregas
- Quatro tipos de atacante com chances e probabilidades de recuperação distintas:
  - **Alcateia de Lobos** (40% chance de ataque, 75% recuperação)
  - **Urso Gigante** (20%, 50% recuperação)
  - **Ladres** (25%, 50% recuperação)
  - **Horda de Orcs** (15%, 15% recuperação)
- Checks de ataque a cada 5 segundos reais enquanto a entrega está em trânsito
- Nome e cor do atacante aparecem visualmente na estrada

#### Sistema de Guardas
- Nova aba **Guardas** (índice 8) com dois painéis: lista de guardas e compra/loja
- 5 tiers de guarda: Velho, Básico, Normal, Épico, Lendário (preços variados)
- Atributos: Força (recuperação de ataque), Resistência, Agilidade (redução de chance de ataque)
- Fórmulas de contribuição coletiva:
  - Redução de ataque: `min(60%, soma_agilidade / 400)`
  - Bônus de recuperação: `min(35%, soma_força / 300)`
- Máximo de 10 guardas simultâneos
- 6 slots de equipamento por guarda: capacete, peitoral, calças, botas, espada, arco
- 17 itens de equipamento de guarda com bônus específicos por slot
- Modal de detalhe do guarda com 3 colunas: atributos, slots de equipamento e inventário filtrado
- Auto-equipar guarda (por raridade)
- Loja de itens de guarda que rotaciona periodicamente
- Guardas e seus itens são **preservados no Prestígio**

#### Vendedor Ambulante
- Vendedores aparecem aleatoriamente durante o jogo (chance configurável)
- 4 qualidades de vendedor: Bugigangas, Raro, Duvidoso, das Sombras
- Oferecem 3 itens (mistura de itens de servo e de guarda)
- Notificação visual com botão de acesso no painel direito
- Timer visível de quanto tempo o vendedor ainda permanece

#### Sistema de Gerentes (Capatazes)
- Nova aba **Gerência** (índice 9)
- 4 tiers com eficiência e intervalo de análise distintos:
  - **Júnior** — 15.000g, 50% eficiência, análise a cada 90s
  - **Experiente** — 60.000g, 75%, 60s
  - **Mestre** — 250.000g, 90%, 30s
  - **Lendário** — 1.000.000g, 100%, 15s
- 3 modos de autonomia: `Só Recomenda`, `Semi-Auto`, `Automático`
- 12 tipos de recomendação: stamina, idosos, aposentadoria, doenças, maldições, compra, equip, guardas, fracos, mercado negro, etc.
- Fila de recomendações exibida na aba com botões **Executar** e **Ignorar**
- Modal de configuração por gerente com toggles e sliders para todos os critérios
- Gerentes de menor eficiência veem apenas um subconjunto aleatório dos problemas
- Estatísticas por gerente: recomendações geradas e ações executadas
- Máximo de 3 gerentes simultâneos (1 por tier, sem duplicatas)
- Gerentes são **preservados no Prestígio**

### ⚖️ Balanceamento

#### Correção de Taxa de Morte
- `risco_morte` nas profundidades reduzido ~12× (valores estavam calibrados por minuto mas checados por ciclo de 5s)
- Profundidades: `[0.0008, 0.0018, 0.0035, 0.0060, 0.0100, 0.0180]`
- Fator de idade reduzido de ×3.4 para ×1.8 (máximo); cap de 70% → 30%
- Resultado: mortes por acidente muito menos frequentes, mortes por velhice mais representadas

### 🎨 Interface e Visual
- Barras de progresso de entrega no painel direito
- Botão de vendedor no painel direito quando disponível
- Resumo de guardas (redução de ataque e bônus de recuperação) na aba Guardas
- Modal de config do gerente com autonomia e todos os parâmetros ajustáveis
- ESC fecha modais em cascata: Vendedor → Gerente → Guarda → Servo

---

## [1.2.0] — 2026-04-11

### ✨ Novas Funcionalidades
- **Estrada de Entrega**: Divisão visual da tela da mina para mostrar a "Estrada de Entrega" no rodapé, com animações de cavalos e carroças transportando o ouro.
- **Ataques Animados**: Sprites específicos para cada tipo de ataque (Lobos, Ladrões, etc.) agora aparecem fisicamente atacando as carroças.
- **Auto-Equipar Geral**: Botão `⚡ AUTO-EQUIP GERAL` adicionado ao cabeçalho da lista de servos para equipar todos simultaneamente com os melhores itens.
- **Sistema Familiar**: Implementação de casais com bônus de "Lua de Mel" (9 meses) e "Cooldown de Reprodução" (2 anos).
- **Sistema de Humor**: Escravos agora possuem humor dinâmico (Feliz, Cansado, Doente, etc.) que impacta diretamente seus atributos (±20%).
- **Mercador de Itens**: Novo painel na Loja que reseta a cada 5 minutos reais, oferecendo equipamentos e consumíveis aleatórios.
- **Cronologia e Histórico**: Contador de Anos/Meses e aba de Histórico para registrar eventos marcantes da mina.
- **Auto-Retorno**: Servos em repouso voltam à mina automaticamente ao atingir 100% de stamina.
- **Deleção em Massa**: Funcionalidades no inventário para deletar itens comuns e incomuns rapidamente.

### 🎨 Interface e Visual
- **Pixel Art Feminino**: Melhoria significativa nas personagens femininas (cabelos longos e detalhados).
- **Bordas por Raridade**: Servos na lista e cards na loja agora possuem bordas coloridas e espessuras variadas conforme a raridade.
- **Log com Wrapping**: O log de eventos lateral agora suporta quebra de linha automática.
- **Top Bar Dinâmica**: Ouro e recursos reposicionados para evitar sobreposição de texto.
- **Clipping Real**: Sidebar de eventos e painéis agora possuem clipping real.

### ⚙️ Performance e Compatibilidade
- **Python 3.9+**: Adicionado suporte para versões anteriores do Python.
- **Rebalanceamento Escalonável**: Custos de upgrades da mina agora crescem de forma exponencial.

### 🐛 Correções de Bugs
- Corrigida a sobreposição de itens na aba Loja.
- Corrigido bug de scroll que impedia ver o último servo da lista.
- Ajustado o posicionamento do cabeçalho da lista de servos.
