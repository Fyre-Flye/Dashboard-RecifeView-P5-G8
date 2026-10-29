import altair as alt
import pandas as pd
import streamlit as st

from src import metricas
from src.config import RAMPA, TEXTO
from src.dados import resumo_preparacao, tabela

st.title("Sobre os dados")
st.markdown("O painel lê um retrato agregado do **dataset do RecifeView** (versão 1.0, 13/10/2026): 2,6 milhões de "
            "registros de cinco portas de entrada, 2012 a 2026, só o município do Recife. O mesmo dataset foi usado na "
            "EDA (entrega N3), e os números do painel batem com os dela.")

st.subheader("Fontes")
st.dataframe(pd.DataFrame([
    ["Central 156 / Emlurb", "2012–2026", "1.377.158", "solicitação de serviço urbano", "Portal de Dados Abertos do Recife (ODbL)"],
    ["Defesa Civil", "2014–2024", "886.263", "ação (vistoria, lona, monitoramento), não pedido", "Portal de Dados Abertos do Recife"],
    ["Ouvidoria-Geral", "2018–2025", "222.855", "manifestação (reclamação, denúncia, pedido…)", "Portal de Dados Abertos do Recife"],
    ["SEDEC (áreas de risco)", "2012–2024", "90.659", "chamado em área de risco", "cópia de 09/03/2024 no Internet Archive"],
    ["Câmara Municipal", "2021–2025", "66.546", "indicação ou requerimento de vereador", "sistema público SAGL da Câmara"],
    ["IBGE, Censo 2022", "2022", "94 bairros", "população, domicílios e % em favela", "SIDRA, tabelas 9922, 9923 e 10206"],
], columns=["Fonte", "Período", "Registros", "Uma linha é", "Origem"]), hide_index=True, width="stretch")

st.subheader("Cobertura: registros por fonte e ano")
d = tabela("demanda")
cob = d[d["ano"] >= 2012].groupby(["fonte_nome", "ano"])["n"].sum().reset_index()
cob["n_txt"] = cob["n"].map(metricas.numero)
mapa = alt.Chart(cob).encode(
    x=alt.X("ano:O", title=None, axis=alt.Axis(labelAngle=0)),
    y=alt.Y("fonte_nome:N", title=None, axis=alt.Axis(labelLimit=220)),
    tooltip=[alt.Tooltip("fonte_nome:N", title="Fonte"), alt.Tooltip("ano:O", title="Ano"),
             alt.Tooltip("n_txt:N", title="Registros")],
)
st.altair_chart((mapa.mark_rect(stroke="white", strokeWidth=2).encode(
    color=alt.Color("n:Q", scale=alt.Scale(type="log", range=RAMPA[1:]), legend=None))
    + mapa.mark_text(fontSize=9).encode(
        text=alt.Text("n_txt:N"), color=alt.condition("datum.n > 40000", alt.value("white"), alt.value(TEXTO))))
    .properties(height=alt.Step(36)), width="stretch")
st.caption("Células vazias: a fonte não publica aquele ano. 2025 e 2026 são parciais (a Ouvidoria de 2025 só traz parte "
           "do ano; o arquivo de 2025 da Defesa Civil foi publicado vazio; 2026 vai até o download, em 07/10/2026).")

st.subheader("Cuidados de leitura")
st.markdown("""
- **Não há chave comum entre as fontes.** O mesmo problema registrado no 156 e na Ouvidoria vira duas linhas que não se ligam; o cruzamento é por bairro, serviço e período. Por isso a fragmentação é medida de forma indireta (pela Câmara), e o pedido de acesso à informação (LAI) ao SGDE, protocolado em 08/10, pode mudar isso.
- **Mais pedido não é mais problema.** O painel mostra taxa por habitante ao lado do volume e trata bairros com menos de 1.000 moradores à parte.
- **Defesa Civil conta ações.** O painel usa só as ações pedidas pelo cidadão (o monitoramento proativo fica fora).
- **Câmara:** categoria e órgão vêm de palavras-chave na ementa (rótulo fraco); "sem resposta registrada" não quer dizer que o serviço não foi feito.
- **Prazos:** só pedidos atendidos têm tempo final. Prazo zero costuma ser encerramento administrativo. Anos recentes têm cauda incompleta.
- **Estoque aberto:** só os arquivos 2025 e 2026 do 156, porque cada arquivo anual é um retrato e pedidos antigos podem ter congelado nele.
- **Coordenadas não são usadas:** faltam em boa parte do 156, e não ao acaso; o recorte territorial é o bairro oficial (94 bairros) e a RPA.
""")

st.subheader("O que foi corrigido antes de agregar")
log = resumo_preparacao()
st.dataframe(pd.DataFrame([{"Correção": k, "Registros": metricas.numero(v)} for k, v in log["correcoes"].items()]),
             hide_index=True, width="content")
st.caption("As mesmas correções da EDA (N3, seção 1), agora no pipeline do painel (pipeline/correcoes.py), mais a marca "
           f"de prazo zero. Tabelas geradas em {log['gerado_em']} a partir de {metricas.numero(log['linhas_no_dataset'])} "
           "registros.")

st.subheader("Privacidade")
st.markdown("O repositório público só tem **contagens e indicadores agregados** por ano, bairro, RPA, categoria e órgão. "
            "Não saem do Drive do grupo: o texto livre da SEDEC (mascarado por heurística, uso só interno), as ementas, "
            "o pseudônimo de endereço (`id_local`), as coordenadas e a autoria das indicações. A lista de pontos "
            "crônicos mostra bairro e serviço, nunca o endereço. Um teste automático confere que nenhuma tabela "
            "publicada tem essas colunas.")

st.subheader("Glossário")
st.table(pd.DataFrame([
    ("RPA", "Região Político-Administrativa: as 6 regiões em que a Prefeitura divide os 94 bairros."),
    ("Mediana", "O valor do meio: metade dos pedidos leva menos que isso."),
    ("p90", "90% dos pedidos levam menos que isso; 1 em cada 10 leva mais."),
    ("Local repetido", "Pedido cujo endereço + serviço aparece 2 ou mais vezes (156, 2015–2025)."),
    ("Duplicidade", "Repetição em até 7 dias: provável pedido em dobro."),
    ("Reincidência", "Repetição 30 dias ou mais depois: o problema voltou."),
    ("Indicação", "Pedido de providência que um vereador envia à Prefeitura."),
    ("AHP", "Método que transforma comparações par a par entre critérios em pesos, com teste de coerência."),
], columns=["Termo", "Significado"]).set_index("Termo"))

st.subheader("Uso de IA")
st.markdown("Este painel foi construído pelo grupo com auxílio do Claude (Anthropic): código, testes e textos foram "
            "gerados a partir das entregas N1 a N3 e revisados pelo grupo. A declaração completa está em "
            "`prompts/declaracao-uso-ia.md` no repositório.")
