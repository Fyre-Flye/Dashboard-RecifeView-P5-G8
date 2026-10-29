# RecifeView · Dashboard (versão inicial)

Painel analítico do projeto **RecifeView** (Projetos 5, CESAR School, 2026.2, Grupo 08, trilha AVD) sobre o desafio
"Fragmentação do Tratamento de Denúncias Recebidas via Conecta Recife", do Banco de Oportunidades da Prefeitura do
Recife. Esta é a entrega **N4 — Dashboard Interativo, versão inicial**.

**Link do app:** _(preencher após o deploy no Streamlit Community Cloud)_

## O que o painel mostra

A pergunta central vem do Plano de Análise (N1): onde, em quais serviços e em que etapa as demandas do cidadão se
repetem, demoram ou ficam sem resposta. A narrativa segue os insights da EDA (N3):

| Página | Mensagem | Principais visuais |
|---|---|---|
| Início | A porta de entrada funciona; a perda está depois dela | 4 KPIs, volume por fonte e ano |
| Retorno e fragmentação | Quase tudo chega à Prefeitura, 1 em cada 5 volta com resposta | funil, resposta por canal de envio, mapa de calor categoria × órgão ligado a um Sankey, canais da Ouvidoria |
| Reincidência | Repetir não é duplicar: o problema volta | % em local repetido por categoria, intervalo entre pedidos, pontos crônicos |
| Prazos | Quem demora está demorando mais | mediana e p90 por ano, faixas de prazo, prazo por categoria, estoque aberto fora do prazo |
| Território | Serviço urbano e emergência apontam para bairros diferentes | dois mapas por habitante, detalhe do bairro clicado, vulnerabilidade × demanda |
| Prioridade (AHP) | Onde agir primeiro, com critérios explícitos | comparação par a par editável, pesos, RC, mapa e ranking, sensibilidade |
| Sobre os dados | Fontes, cobertura, cuidados, correções e privacidade | tabela de cobertura por fonte e ano, glossário |

Filtros globais na barra lateral (valem em todas as páginas): **período**, **RPA**, **bairro** e **categoria de
serviço**. Cada página diz quais filtros não consegue aplicar e por quê (a Ouvidoria não tem bairro, por exemplo).

## Como rodar

Requer Python 3.11 a 3.13.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

O app lê só `data/clean/`, que já está no repositório.

## Como regerar os dados

As tabelas de `data/clean/` saem do dataset do grupo (camada ouro), que **não** fica no repositório.

1. Copie da pasta `Dados` do Drive do grupo para `data/raw/`:
   - `01_DATASET_PRINCIPAL_recifeview-dataset/recifeview_demandas_recife_2012_2026.csv.xz`
   - `02_fontes_separadas/bruto/referencia_bairros.zip`
2. Rode:

```bash
python -m pip install -r requirements-dev.txt
python -m pipeline.preparar_dados      # cerca de 30 segundos
python -m pytest                       # testes do pipeline, do AHP, dos filtros e das páginas
```

O pipeline aplica as correções da EDA (N3) em `pipeline/correcoes.py` e gera os agregados em
`pipeline/agregados.py`. O resumo das correções fica em `data/clean/resumo_preparacao.json`.

## Privacidade

O repositório é público, então só tem **contagens e indicadores agregados** por ano, bairro, RPA, categoria e
órgão, a partir de dados abertos da Prefeitura, da Câmara e do IBGE. Ficam de fora: o texto da SEDEC (mascarado por
heurística, uso interno do grupo), as ementas, o pseudônimo de endereço (`id_local`), as coordenadas e a autoria das
indicações. O teste `test_nenhum_arquivo_publicado_tem_coluna_sensivel` falha se alguma tabela publicada tiver
essas colunas.

## Estrutura

```
app.py                 navegação, filtros globais e rodapé
views/                 uma página por arquivo
src/                   configuração visual, leitura dos dados, filtros, métricas e AHP
pipeline/              correções e agregação (roda fora do app)
data/raw/              dataset do grupo (não versionado)
data/clean/            agregados lidos pelo app (versionados)
entregas/              rascunho do layout, justificativa das métricas, julgamentos do AHP
prompts/               declaração de uso de IA
tests/                 pytest + AppTest do Streamlit
static/fonts/          Montserrat (licença OFL), servida pelo próprio app
assets/                marca RecifeView
```

## Identidade visual

RecifeView: azul `#0F62FE`, azul claro `#EAF2FF`, texto preto, fundo branco e tipografia Montserrat. Nos mapas,
uma rampa de azuis de um só matiz; laranja só para ênfase pontual.

## Uso de IA

Feito pelo grupo com auxílio do Claude (Anthropic). Detalhes em [prompts/declaracao-uso-ia.md](prompts/declaracao-uso-ia.md).
