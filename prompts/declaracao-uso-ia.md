# Declaração de Uso de IA

**Projeto:** RecifeView · Projetos 5 · CESAR School · 2026.2 · Grupo 08 (trilha AVD)
**Entrega:** N4, Dashboard Interativo (versão inicial), Semana 13
**Quem usou:** Gustavo Henrique Cruz de Oliveira, em nome do grupo
**Período:** 28/10 a 30/10/2026

## Ferramenta

Claude (Anthropic), usado como assistente de programação e de revisão, com acesso de leitura aos materiais do grupo
(entregas anteriores, dataset tratado e requisitos da disciplina) e à prática de Streamlit de AVD.

## Como a IA foi usada

Os pedidos foram feitos em linguagem natural, em português, e cobriram quatro frentes:

1. **Planejamento:** propor a estrutura do repositório e das páginas a partir do enunciado da N4, das entregas N1 a
   N3 e da prática de Streamlit. O plano foi discutido e ajustado pelo grupo antes de qualquer código.
2. **Código:** escrever o pipeline de agregação, as páginas do painel, o cálculo do AHP e os testes, seguindo as
   decisões do grupo sobre narrativa, identidade visual e privacidade dos dados.
3. **Conferência:** comparar os números do painel com os da EDA (N3), testar o app publicado de ponta a ponta e
   corrigir os defeitos encontrados.
4. **Texto:** rascunhar o relatório da semana, o README e as justificativas, revisados pelo grupo.

## O que foi aceito, modificado ou rejeitado e por quê

- **Aceito:**
  - Estrutura do repositório no padrão da prática de AVD (`app.py` com `st.navigation`, `views/`, `src/`,
    `data/raw` fora do Git, `data/clean` versionado, `entregas/`, `prompts/`, tema em `.streamlit/config.toml`).
  - Pipeline que aplica as correções da EDA (N3) e gera só tabelas agregadas, com testes.
  - Gráficos em Altair com seleção cruzada, na ordem dos insights da N3.
  - Índice de prioridade por bairro com AHP, com os julgamentos editáveis na própria página.

- **Modificado:**
  - Todos os números do painel foram conferidos contra a N3 antes da entrega.
  - O Sankey usa Plotly, porque o Altair não tem esse tipo de gráfico; o resto é Altair, como a prática pede.
  - Rótulos, títulos e cores foram ajustados depois de conferir o painel nos temas claro e escuro.

- **Rejeitado ou deixado de fora:**
  - Publicar o dataset do grupo no repositório: ele tem campos de uso interno. Só sobem agregados, e um teste
    confere que nenhuma tabela publicada tem colunas sensíveis.
  - Tratar pesos do AHP sugeridos por IA como resultado. Os julgamentos padrão do painel são uma proposta inicial do
    grupo, a validar com os professores e com quem opera os serviços.
  - Critérios de prioridade sem base nos dados ou de cunho político.

O grupo revisou o código, os números e os textos e responde pelo conteúdo entregue.
