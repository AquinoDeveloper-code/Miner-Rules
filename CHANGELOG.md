# Changelog — Versão 1.2.0 (Expansão de Mecânicas e Polimento)

Todas as novas funcionalidades e melhorias implementadas na "Mina dos Servos Eternos".

## [1.2.0] — 2026-04-11

### ✨ Novas Funcionalidades
- **Auto-Equipar Geral**: Botão `⚡ AUTO-EQUIP GERAL` adicionado ao cabeçalho da lista de servos para equipar todos simultaneamente com os melhores itens.
- **Sistema Familiar**: Implementação de casais com bônus de "Lua de Mel" (9 meses) e "Cooldown de Reprodução" (2 anos).
- **Sistema de Humor**: Escravos agora possuem humor dinâmico (Feliz, Cansado, Doente, etc.) que impacta diretamente seus atributos (±20%).
- **Mercador de Itens**: Novo painel na Loja que reseta a cada 5 minutos reais, oferecendo equipamentos e consumíveis aleatórios.
- **Cronologia e Histórico**: Contador de Anos/Meses e aba de Histórico para registrar eventos marcantes da mina.
- **Auto-Retorno**: Servos em repouso voltam à mina automaticamente ao atingir 100% de stamina.
- **Deleção em Massa**: Funcionalidades no inventário para deletar itens comuns e incomuns rapidamente.

### 🎨 Interface e Visual
- **Pixel Art Feminino**: Melhoria significativa nas personagens femininas (cabelos longos e detalhados).
- **Bordas por Raridade**: Servos na lista e cards na loja agora possuem bordas coloridas e espessuras variadas conforme a raridade (Incomum, Raro, Épico, Lendário).
- **Log com Wrapping**: O log de eventos lateral agora suporta quebra de linha automática (word wrap), tornando-o totalmente legível.
- **Top Bar Dinâmica**: Ouro e recursos reposicionados para evitar sobreposição de texto em qualquer resolução.
- **Clipping Real**: Sidebar de eventos e painéis agora possuem clipping real (pygame.set_clip) para evitar vazamento de pixels.

### ⚙️ Performance e Compatibilidade
- **Python 3.9+**: Adicionado suporte para versões anteriores do Python (uso de `from __future__ import annotations`).
- **Rebalanceamento Escalonável**: Custos de upgrades da mina agora crescem de forma exponencial (mais difícil no late game).

### 🐛 Correções de Bugs
- Corrigida a sobreposição de itens na aba Loja.
- Corrigido bug de scroll que impedia ver o último servo da lista.
- Ajustado o posicionamento do cabeçalho da lista de servos.
