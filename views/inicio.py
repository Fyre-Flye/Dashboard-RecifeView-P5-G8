import altair as alt
import streamlit as st

from src import filtros, metricas
from src.componentes import kpi
from src.config import ESCALA_FONTE, eixo_numero
from src.dados import tabela

f = filtros.atuais()

st.title("Demandas do cidadão no Recife")
st.markdown(
    "**Onde, em quais serviços e em que etapa** as demandas que chegam à Prefeitura por cinco portas diferentes "
    "se repetem, demoram ou ficam sem resposta. Painel para quem gerencia a retaguarda: a triagem da Ouvidoria "
    "e os gestores dos órgãos executores."
)
filtros.legenda(f)

# --- KPIs -------------------------------------------------------------------------------------------
demanda = tabela("demanda")
d = f.aplicar(demanda, categoria=False)
if f.categorias:
    d = d[d["fonte"].isin(["156_EMLURB", "CAMARA_REQUERIMENTOS"]) & d["categoria"].isin(f.categorias)]
if f.territorio_ativo:
    d = d[d["bairro_oficial"].notna() | d["rpa"].notna()]
d = d[~((d["fonte"] == "DEFESA_CIVIL") & (d["iniciativa"] != "CIDADAO"))]   # só a demanda do cidadão

ind = f.aplicar(tabela("camara_indicacoes"))
rep = f.aplicar(tabela("reincidencia_156"))
praz = f.aplicar(tabela("prazos_156"))

k1, k2, k3, k4 = st.columns(4)
kpi(k1, "Demandas registradas", metricas.numero(d["n"].sum()), "cinco fontes",
    "Pedidos, manifestações, chamados e indicações das cinco fontes no recorte. Na Defesa Civil, só as ações "
    "pedidas pelo cidadão (o monitoramento proativo fica fora).")
enviadas = ind["enviada"].mean() * 100 if len(ind) else None
kpi(k2, "Indicações respondidas", metricas.porcentagem(ind["respondida"].mean() * 100 if len(ind) else None),
    f"{metricas.porcentagem(enviadas)} chegam à Prefeitura",
    f"Das {metricas.numero(len(ind))} indicações de vereadores no recorte, quase todas são enviadas à Prefeitura; "
    "esta é a parte que volta com resposta registrada na tramitação da Câmara.")
kpi(k3, "Local repetido (156)",
    metricas.porcentagem(rep["repetidos"].sum() / rep["registros"].sum() * 100 if len(rep) else None),
    "156, mesmo local + serviço",
    "Pedidos do 156 com número no endereço cujo local + serviço aparece 2 ou mais vezes entre 2015 e 2025.")
p90 = metricas.quantil_ponderado(praz["dias"], praz["n"], 0.9)
mediana = metricas.quantil_ponderado(praz["dias"], praz["n"], 0.5)
kpi(k4, "Prazo do 156 (p90)", metricas.dias(p90), f"mediana: {metricas.dias(mediana)}",
    "1 em cada 10 pedidos atendidos leva mais que isso. A maioria se resolve rápido e uma cauda leva meses; "
    "por isso o painel mostra percentis, não média.")

# --- Mensagem principal -----------------------------------------------------------------------------
with st.container(border=True):
    st.markdown("#### A porta de entrada funciona. A perda está depois dela.")
    st.markdown(
        "O app Conecta Recife é só cerca de 3% das manifestações da Ouvidoria, e quase toda indicação de vereador "
        "chega à Prefeitura. O que falha é o caminho de volta: pouca coisa retorna com resposta registrada, o mesmo "
        "problema volta ao mesmo lugar e uma parte dos pedidos fica meses na fila. Cada página abaixo mostra uma "
        "dessas perdas, e as duas últimas mostram onde agir primeiro."
    )
    c1, c2, c3 = st.columns(3)
    c1.page_link("views/retorno.py", label="Retorno e fragmentação", icon=":material/call_split:")
    c1.caption("Para onde vai cada tipo de pedido e quanto volta.")
    c2.page_link("views/reincidencia.py", label="Reincidência", icon=":material/repeat:")
    c2.caption("Repetir não é duplicar: o problema volta.")
    c3.page_link("views/prazos.py", label="Prazos", icon=":material/schedule:")
    c3.caption("Quem demora está demorando mais.")
    c4, c5, _ = st.columns(3)
    c4.page_link("views/territorio.py", label="Território", icon=":material/map:")
    c4.caption("Serviço urbano e emergência apontam para bairros diferentes.")
    c5.page_link("views/prioridade.py", label="Prioridade (AHP)", icon=":material/low_priority:")
    c5.caption("Um índice com critérios explícitos e ajustáveis.")

# --- Volume por fonte -------------------------------------------------------------------------------
st.subheader("Quanto chega por cada porta")
serie = d.groupby(["ano", "fonte_nome"], as_index=False)["n"].sum()
serie["registros"] = serie["n"].map(metricas.numero)
if serie.empty:
    st.info("Nenhum registro para os filtros escolhidos.")
else:
    clique = alt.selection_point(fields=["fonte_nome"], bind="legend")
    base = alt.Chart(serie).encode(
        x=alt.X("ano:O", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("n:Q", axis=eixo_numero("registros por ano")),
        color=alt.Color("fonte_nome:N", title="Fonte", scale=ESCALA_FONTE),
        opacity=alt.condition(clique, alt.value(1), alt.value(0.15)),
        tooltip=[alt.Tooltip("fonte_nome:N", title="Fonte"), alt.Tooltip("ano:O", title="Ano"),
                 alt.Tooltip("registros:N", title="Registros")],
    )
    grafico = (base.mark_line() + base.mark_point(size=50)).add_params(clique).properties(height=320)
    st.altair_chart(grafico, width="stretch")
    notas = ["Clique numa fonte da legenda para destacá-la."]
    if f.territorio_ativo:
        notas.append("Com filtro de território, a Ouvidoria sai do gráfico: a fonte não publica o bairro.")
    if f.categorias:
        notas.append("Com filtro de categoria, só o 156 e a Câmara ficam: as outras fontes usam outra classificação.")
    notas.append("2025 e 2026 são parciais em algumas fontes; a Defesa Civil mostra só ações pedidas pelo cidadão.")
    st.caption(" ".join(notas))
