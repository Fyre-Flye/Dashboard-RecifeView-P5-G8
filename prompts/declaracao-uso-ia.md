# Declaração de Uso de IA

**Projeto:** RecifeView · Projetos 5 · CESAR School · 2026.2 · Grupo 08 (trilha AVD)
**Entregas cobertas:** N4, Dashboard Interativo (Semana 13) · N5, Proposta de Integração e Publicação (Semana 14) ·
N6, Dashboard Consolidado (Semana 15)
**Quem usou:** Gustavo Henrique Cruz de Oliveira, em nome do grupo
**Período:** 28/10 a 13/11/2026

## Ferramenta

Claude (Anthropic), usado como assistente de programação e de revisão, com acesso de leitura aos materiais do grupo
(entregas anteriores, dataset tratado e requisitos da disciplina) e à prática de Streamlit de AVD.

## Como a IA foi usada

Os pedidos foram feitos em linguagem natural, em português, e cobriram quatro frentes:

1. **Planejamento:** propor a estrutura do repositório e das páginas a partir dos enunciados das entregas, das
   entregas anteriores e da prática de Streamlit. Os planos foram discutidos e ajustados pelo grupo antes do código.
2. **Código:** escrever o pipeline de agregação, as páginas do painel, o cálculo do AHP e os testes, seguindo as
   decisões do grupo sobre narrativa, identidade visual e privacidade dos dados.
3. **Conferência:** comparar os números do painel com os da EDA (N3), testar o app publicado de ponta a ponta, revisar
   a interface em tamanhos de tela diferentes e corrigir os defeitos encontrados.
4. **Texto:** rascunhar os relatórios das entregas, o README e os textos de leitura do painel, revisados pelo grupo.

## O que foi aceito, modificado ou rejeitado e por quê

- **Aceito:**
  - Estrutura do repositório no padrão da prática de AVD (`app.py` com `st.navigation`, `views/`, `src/`,
    `data/raw` fora do Git, `data/clean` versionado, `entregas/`, `prompts/`, tema em `.streamlit/config.toml`).
  - Pipeline que aplica as correções da EDA (N3) e gera só tabelas agregadas, com testes.
  - Gráficos em Altair com seleção cruzada, na ordem dos insights da N3.
  - Índice de prioridade por bairro com AHP, com os julgamentos editáveis na própria página.
  - Na consolidação (N6): o Painel Geral como página inicial, a página de Achados, o dicionário do dataset e a
    indicação dos filtros que cada página aplica.

- **Modificado:**
  - Todos os números do painel foram conferidos contra a N3 antes de cada entrega.
  - O Sankey usa Plotly, porque o Altair não tem esse tipo de gráfico; o resto é Altair, como a prática pede.
  - Rótulos, títulos, cores e espaçamentos foram ajustados pelo grupo depois de conferir o painel nos temas claro e
    escuro e em telas de celular, notebook e monitor.
  - A divisão entre o dashboard (entrega de AVD) e a aplicação RecifeView (parte da solução, que replica o dashboard)
    foi corrigida pelo grupo depois da N5.

- **Rejeitado ou deixado de fora:**
  - Publicar o dataset do grupo no repositório: ele tem campos de uso interno. Só sobem agregados, e um teste
    confere que nenhuma tabela publicada tem colunas sensíveis.
  - Tratar pesos do AHP sugeridos por IA como resultado. Os julgamentos padrão do painel são uma proposta inicial do
    grupo, a validar com os professores e com quem opera os serviços.
  - Critérios de prioridade sem base nos dados ou de cunho político.

O grupo revisou o código, os números e os textos e responde pelo conteúdo entregue.
