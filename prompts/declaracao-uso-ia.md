# Declaração de Uso de IA

**Projeto:** RecifeView · Projetos 5 · CESAR School · 2026.2 · Grupo 08 (trilha AVD)
**Entrega:** N4, Dashboard Interativo (versão inicial), Semana 13
**Quem usou:** Gustavo Henrique Cruz de Oliveira, em nome do grupo
**Data:** 29/10/2026 (trabalho feito entre 28/10 e 29/10/2026)

## Ferramenta

Claude (Anthropic), modelo Claude Opus 5.5, com acesso à pasta do grupo no Google Drive e à prática de Streamlit da
disciplina de AVD.

## Prompt usado

Os pedidos foram feitos em português, nesta ordem (resumidos; alguns estão quase como escritos):

1. "De acordo com a semana de hoje, nossa entrega é: Dashboard Interativo — Versão Inicial [...] Quero que essa
   primeira versão do dashboard seja feita em streamlit [...] E usar nosso dataset tratado. [...] Suba no drive o
   projeto. Eu vou criar um repositório no github ai dps você faz o push, mas separe os commits de cada
   funcionalidade ou mudança significativa. [...] Antes de começar, me diga seu plano."
2. Depois do plano: "Vai ser publico, mas cuidado na hora de subir os dados. [...] Tente aplicar o AHP acho que seria
   interessante. Pode seguir em frente. É coautoria, você e eu. [...] suba o PDF na pasta referente a semana. [...]
   Sim use nossa identidade visual. [...] siga o que o texto pediu mas seguindo nosso roteiro msm de entregas
   conforme as passadas."

Antes de escrever código, a IA leu a pasta `Contexto` do Drive, o README e o dicionário do dataset, os requisitos de
CC/AVD, as entregas N1, N2 e N3 (PDFs e o notebook da EDA) e o repositório da prática de Streamlit da Profª Maíra
(roteiro, slides das Aulas 21 e 22, estrutura de pastas e guia de seleção cruzada no Altair).

## O que foi aceito, modificado ou rejeitado e por quê

- **Aceito:**
  - Estrutura do repositório no padrão da prática de AVD (`app.py` com `st.navigation`, `views/`, `src/`,
    `data/raw` fora do Git, `data/clean` versionado, `entregas/`, `prompts/`, tema em `.streamlit/config.toml`).
  - Pipeline em `pipeline/` que aplica as correções da EDA (N3) e gera só tabelas agregadas, com testes.
  - Narrativa do painel na ordem dos insights da seção 8.2 da N3 e gráficos em Altair, com seleção cruzada no
    mapa de calor (categoria → Sankey) e nos mapas (bairro → detalhe).
  - Índice de prioridade por bairro com AHP, com os julgamentos editáveis na própria página.
  - Commits separados por funcionalidade, com o Gustavo como autor e a IA como coautora.

- **Modificado:**
  - Os números do painel foram conferidos contra a N3 antes da entrega (por exemplo: 53,3% em local repetido em
    2015–2025, mediana de 3 dias e p90 de 43 dias no 156, 21% das indicações com resposta registrada, mediana de
    241 dias até a resposta). Todos batem.
  - O Sankey usa Plotly, porque o Altair não tem esse tipo de gráfico; o resto é Altair, como a prática pede.
  - Rótulos e cartões que ficavam cortados na tela foram encurtados depois de conferir prints do app.

- **Rejeitado ou deixado de fora:**
  - Publicar o dataset do grupo no repositório: ele tem o texto da SEDEC (uso interno) e o pseudônimo de endereço.
    Só sobem agregados, e um teste confere que nenhuma tabela publicada tem colunas sensíveis.
  - Usar como resultado os pesos do AHP que apareceram numa conversa anterior com outra IA (ilustrativos) e o
    critério "impacto político" (autoria do vereador). Os julgamentos padrão do painel são uma proposta inicial do
    grupo, a validar com a Profª Maíra, o Prof. Marcelo e quem opera a Defesa Civil e a Emlurb.
  - Clima (chuva × demanda): continua como estudo futuro, como decidido na N2.

**Limitação:** a IA não teve acesso ao Google Classroom; o enunciado usado foi o texto da entrega colado pelo Gustavo
e a lista de requisitos de CC/AVD salva no Drive. A conferência visual foi feita com prints automáticos do app
rodando localmente.
