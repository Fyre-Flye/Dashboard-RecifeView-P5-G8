import altair as alt
import pandas as pd
import streamlit as st

from src import filtros, metricas
from src.componentes import kpi, leitura
from src.config import AZUL, AZUL25, DESTAQUE, RAMPA, SEM_DADO, cor_forte
from src.dados import malha, tabela

f = filtros.atuais()

st.title("Território")
st.markdown("**Há pelo menos dois mapas de prioridade.** O pedido de serviço urbano (156) e a demanda de emergência "
            "(Defesa Civil) apontam para bairros diferentes. A demanda aparece por mil habitantes, porque bairro "
            "grande pede mais só por ser grande; o volume absoluto fica ao lado, no detalhe.")
filtros.legenda(f, {"Mapas": "RPA e bairro escolhidos ficam em destaque (o resto da cidade continua visível); "
                             "a categoria vale só para o 156."})

bairros = tabela("bairros").set_index("bairro_oficial")
demanda = f.aplicar(tabela("demanda"), territorio=False, categoria=False)

FONTES = {
    "156": ("156_EMLURB", "Serviço Urbano (156)", "pedidos / mil hab. / ano", 1000),
    "dc": ("DEFESA_CIVIL", "Emergência (Defesa Civil)", "ações pedidas / mil hab. / ano", 1000),
    "sedec": ("SEDEC_CHAMADOS", "Áreas de Risco (SEDEC)", "chamados / mil hab. / ano", 1000),
    "camara": ("CAMARA_REQUERIMENTOS", "Indicações de Vereadores", "indicações / 10 mil hab. / ano", 10000),
}


def taxas(chave: str) -> pd.DataFrame:
    fonte, _, _, por = FONTES[chave]
    d = demanda[demanda["fonte"] == fonte]
    if fonte == "DEFESA_CIVIL":
        d = d[d["iniciativa"] == "CIDADAO"]                 # só a demanda do cidadão, sem o monitoramento proativo
    if fonte in ("156_EMLURB", "CAMARA_REQUERIMENTOS") and f.categorias:
        d = d[d["categoria"].isin(f.categorias)]
    anos = d["ano"].nunique()                               # anos do recorte em que a fonte tem dado
    vol = d.groupby("bairro_oficial")["n"].sum()
    t = bairros[["nome", "rpa", "populacao", "pct_favela", "taxa_confiavel"]].copy()
    t["volume"] = vol.reindex(t.index).fillna(0)
    t["taxa"] = (t["volume"] / max(anos, 1) / t["populacao"] * por).where(t["taxa_confiavel"])
    t["anos"] = anos
    t["faixa"] = faixas_quintil(t["taxa"])
    t["taxa_txt"] = t["taxa"].map(lambda v: metricas.numero(v, 1) if pd.notna(v) else "não calculada (< 1.000 moradores)")
    t["volume_txt"] = t["volume"].map(metricas.numero)
    t["favela_txt"] = t["pct_favela"].map(lambda v: metricas.porcentagem(v, 1))
    destaque = pd.Series(True, index=t.index)
    if f.rpas:
        destaque &= t["rpa"].isin(f.rpas)
    if f.bairros:
        destaque &= t.index.isin(f.bairros)
    t["destaque"] = destaque
    return t.reset_index()


def faixas_quintil(taxa: pd.Series) -> pd.Series:
    """Cinco faixas com o mesmo número de bairros; o rótulo traz os limites ("25,7 a 52,5")."""
    validos = taxa.dropna()
    if validos.nunique() < 5:
        return taxa.map(lambda v: metricas.numero(v, 1) if pd.notna(v) else None)
    classes = pd.qcut(validos, 5, duplicates="drop")
    rotulos = {c: f"{metricas.numero(max(c.left, 0), 1)} a {metricas.numero(c.right, 1)}" for c in classes.cat.categories}
    return classes.map(rotulos).astype(object).reindex(taxa.index)


def mapa(t: pd.DataFrame, titulo_legenda: str, chave: str) -> alt.Chart:
    geo = alt.Data(values=malha()["features"])
    campos = ["nome", "rpa", "taxa", "faixa", "taxa_txt", "volume_txt", "favela_txt", "destaque"]
    # A seleção usa um campo calculado sem ponto no nome: com "properties.bairro_oficial", o Streamlit
    # devolve a chave escapada ("properties\\.bairro_oficial") e o clique no mapa não abria o detalhe.
    clique = alt.selection_point(fields=["bairro"], name="bairro", on="click", empty=False)
    ordem = t.dropna(subset=["taxa"]).groupby("faixa")["taxa"].min().sort_values().index.tolist()
    return alt.Chart(geo).mark_geoshape(stroke="white", strokeWidth=0.7).transform_calculate(
        bairro="datum.properties.bairro_oficial",
    ).transform_lookup(
        lookup="properties.bairro_oficial", from_=alt.LookupData(t, "bairro_oficial", campos),
    ).encode(
        color=alt.condition("isValid(datum.faixa)", alt.Color(
            "faixa:O", title=titulo_legenda, sort=ordem, scale=alt.Scale(domain=ordem, range=RAMPA[1:1 + len(ordem)]),
            legend=alt.Legend(orient="bottom", direction="horizontal", titleLimit=320, labelLimit=120,
                              symbolType="square", columns=3)),
            alt.value(SEM_DADO)),
        opacity=alt.condition("datum.destaque", alt.value(1), alt.value(0.25)),
        strokeWidth=alt.condition(clique, alt.value(2.5), alt.value(0.7)),
        stroke=alt.condition(clique, alt.value(DESTAQUE), alt.value("white")),
        tooltip=[alt.Tooltip("nome:N", title="Bairro"), alt.Tooltip("rpa:N", title="RPA"),
                 alt.Tooltip("taxa_txt:N", title=titulo_legenda), alt.Tooltip("volume_txt:N", title="Volume no período"),
                 alt.Tooltip("favela_txt:N", title="% em favela")],
    ).add_params(clique).project(type="mercator").properties(height=470)


t156, tdc = taxas("156"), taxas("dc")
c1, c2 = st.columns(2, gap="medium")
with c1:
    st.markdown(f"**{FONTES['156'][1]}** · {FONTES['156'][2]}")
    ev1 = st.altair_chart(mapa(t156, FONTES["156"][2], "156"), width="stretch", on_select="rerun", key="mapa_156")
with c2:
    st.markdown(f"**{FONTES['dc'][1]}** · {FONTES['dc'][2]}")
    ev2 = st.altair_chart(mapa(tdc, FONTES["dc"][2], "dc"), width="stretch", on_select="rerun", key="mapa_dc")
    if tdc["volume"].sum() == 0:
        st.caption("A Defesa Civil publica dados de 2014 a 2024; não há registros no período escolhido.")
leitura("Cores em cinco faixas com o mesmo número de bairros cada (quintis), do mais claro (menor taxa) ao mais escuro. "
        "Bairros em cinza têm menos de 1.000 moradores, e a taxa por habitante distorce. As taxas mais altas do 156 "
        "estão em bairros centrais e pequenos (o pedido vem de quem circula; a população é de quem mora); a emergência "
        "se concentra nos morros do Norte e Noroeste e no Ibura e na Cohab. <b>Clique num bairro</b> para ver o detalhe.")

# --- Detalhe do bairro clicado ------------------------------------------------------------------------
def bairro_clicado(evento) -> str | None:
    if not evento:
        return None
    pontos = evento.selection.get("bairro", [])
    return pontos[0].get("bairro") if pontos else None


escolhido = bairro_clicado(ev1) or bairro_clicado(ev2) or (f.bairros[0] if len(f.bairros) == 1 else None)
ind = tabela("indicadores_bairro").set_index("bairro_oficial")
if escolhido:
    linha = bairros.loc[escolhido]
    st.subheader(f"{linha['nome']} · RPA {linha['rpa']}")
    k = st.columns(5)
    kpi(k[0], "População", metricas.numero(linha["populacao"]), f"{metricas.porcentagem(linha['pct_favela'], 1)} em favela",
        "Censo 2022 (IBGE).")
    a = t156.set_index("bairro_oficial").loc[escolhido]
    b = tdc.set_index("bairro_oficial").loc[escolhido]
    kpi(k[1], "Pedidos ao 156", a["volume_txt"], f"{a['taxa_txt'].split(' (')[0]} / mil hab. / ano")
    kpi(k[2], "Defesa Civil", b["volume_txt"], f"{b['taxa_txt'].split(' (')[0]} / mil hab. / ano",
        "Ações da Defesa Civil pedidas pelo cidadão (vistoria, lona). A Defesa Civil publica até 2024.")
    if escolhido in ind.index:
        i = ind.loc[escolhido]
        kpi(k[3], "Local repetido (156)", metricas.porcentagem(i["pct_reincidencia_156"], 1), "2021–2025")
        kpi(k[4], "Abertos fora do prazo", metricas.porcentagem(i["pct_atraso_156"]),
            f"de {metricas.numero(i['abertos_156'])} abertos")
    st.page_link("views/prioridade.py", label="Ver a posição deste bairro no índice de prioridade",
                 icon=":material/arrow_forward:")

# --- Vulnerabilidade x demanda ------------------------------------------------------------------------
st.subheader("Mais Pedido Não Quer Dizer Mais Problema")
def dispersao(t: pd.DataFrame, titulo: str, escala: alt.Scale, valores=None) -> alt.Chart:
    d = t[t["taxa"].notna()]
    pontos = alt.Chart(d).mark_circle(size=70, opacity=0.85, stroke="white", strokeWidth=1).encode(
        x=alt.X("pct_favela:Q", title="% da população em favela (Censo 2022)"),
        y=alt.Y("taxa:Q", title=titulo, scale=escala, axis=alt.Axis(values=valores) if valores else alt.Axis()),
        color=alt.condition("datum.destaque", alt.value(AZUL), alt.value(AZUL25)),
        tooltip=[alt.Tooltip("nome:N", title="Bairro"), alt.Tooltip("favela_txt:N", title="% em favela"),
                 alt.Tooltip("taxa_txt:N", title="Taxa")],
    )
    tendencia = alt.Chart(d).transform_loess("pct_favela", "taxa", bandwidth=0.6).mark_line(
        color=cor_forte(), strokeWidth=2.5).encode(x="pct_favela:Q", y=alt.Y("taxa:Q", scale=escala))
    return (pontos + tendencia).properties(height=280)


c1, c2 = st.columns(2, gap="large")
with c1:
    st.markdown(f"**{FONTES['156'][1]}**")
    st.altair_chart(dispersao(t156, FONTES["156"][2], alt.Scale(zero=True)), width="stretch")
with c2:
    st.markdown(f"**{FONTES['dc'][1]}**")
    st.altair_chart(dispersao(tdc, FONTES["dc"][2] + " (escala log)", alt.Scale(type="symlog", constant=1),
                              valores=[0, 1, 3, 10, 30, 100]),
                    width="stretch")
leitura("<b>Serviço urbano:</b> a nuvem é plana. Bairros mais vulneráveis não pedem menos ao 156 por habitante "
        "(ρ de Spearman ≈ −0,13, não significativo; N3). <b>Emergência:</b> a tendência sobe acima de 30–40% da "
        "população em favela, e alguns bairros de morro ficam muito acima dos demais (ρ ≈ 0,37). A linha escura é uma "
        "tendência suavizada (LOESS). Por isso o índice de prioridade usa a vulnerabilidade como critério próprio, em "
        "vez de confiar só no volume de pedidos.")

# --- Tabela -------------------------------------------------------------------------------------------
with st.expander("Tabela por Bairro (para Conferir e Exportar)"):
    tabela_b = t156[["nome", "rpa", "populacao", "pct_favela", "volume", "taxa"]].merge(
        tdc[["bairro_oficial", "volume", "taxa"]].rename(columns={"volume": "volume_dc", "taxa": "taxa_dc"}),
        left_on=t156["bairro_oficial"], right_on="bairro_oficial").drop(columns=["bairro_oficial"])
    st.dataframe(tabela_b.sort_values("taxa", ascending=False), hide_index=True, width="stretch",
                 column_config={
                     "nome": "Bairro", "rpa": "RPA", "populacao": st.column_config.NumberColumn("População", format="localized"),
                     "pct_favela": st.column_config.NumberColumn("% em favela", format="%.1f"),
                     "volume": st.column_config.NumberColumn("Pedidos 156", format="localized"),
                     "taxa": st.column_config.NumberColumn("156 / mil hab. / ano", format="%.1f"),
                     "volume_dc": st.column_config.NumberColumn("Ações Def. Civil", format="localized"),
                     "taxa_dc": st.column_config.NumberColumn("Def. Civil / mil hab. / ano", format="%.1f"),
                 })
