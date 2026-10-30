import altair as alt
import pandas as pd
import streamlit as st

from src import ahp, filtros, metricas
from src.componentes import kpi, leitura
from src.config import AZUL25, DESTAQUE, RAMPA, TEXTO
from src.dados import malha, tabela

f = filtros.atuais()
CRIT = {c.chave: c for c in ahp.CRITERIOS}
CHAVES = list(CRIT)
# As cores seguem a origem do critério: risco vem da Defesa Civil (laranja); atraso e reincidência, do 156.
CORES = {"risco": DESTAQUE, "vulnerabilidade": "#9A3FB8", "atraso": "#0F62FE", "reincidencia": "#1B998B"}

st.title("Prioridade (AHP)")
st.markdown("Onde agir primeiro, com **critérios explícitos e ajustáveis**. O índice combina quatro critérios que "
            "saíram da EDA, com pesos obtidos pelo AHP (Analytic Hierarchy Process): quem decide compara os critérios "
            "dois a dois, e o método calcula os pesos e confere se os julgamentos são coerentes.")
st.info("Os julgamentos que vêm carregados são uma **proposta inicial do grupo para discussão**, não pesos validados "
        "pela Prefeitura. O próximo passo é refazer as comparações com a Profª Maíra, o Prof. Marcelo e, se possível, "
        "quem opera a Defesa Civil e a Emlurb. Você pode refazê-las abaixo e ver o mapa mudar.", icon=":material/info:")
filtros.legenda(f, {"Período": "fixo em 2021–2025 (estoque aberto: arquivos 2025–2026), como na EDA.",
                    "Território": "RPA e bairro destacam o mapa e filtram a lista; a posição é sempre na cidade toda."})

# --- Critérios ----------------------------------------------------------------------------------------
with st.expander("Os Quatro Critérios e Como Cada um É Medido", expanded=False):
    st.dataframe(pd.DataFrame([{"Critério": c.nome, "Indicador": c.unidade, "O que mede e por quê": c.descricao}
                               for c in ahp.CRITERIOS]), hide_index=True, width="stretch")
    st.caption("Cada bairro recebe, em cada critério, a sua posição relativa entre os 89 bairros com 1.000 moradores "
               "ou mais (0 = menor valor, 1 = maior). O índice é a soma ponderada dessas posições, uma nota de 0 a 10. Usar a "
               "posição, e não o valor bruto, evita que poucos bairros extremos achatem os outros.")

# --- Comparações par a par ----------------------------------------------------------------------------
OPCOES = [-9, -8, -7, -6, -5, -4, -3, -2, 1, 2, 3, 4, 5, 6, 7, 8, 9]


def chave_estado(a: str, b: str) -> str:
    return f"ahp_{a}_{b}"


def para_opcao(valor: float) -> int:
    return int(round(valor)) if valor >= 1 else -int(round(1 / valor))


def para_valor(opcao: int) -> float:
    return float(opcao) if opcao > 0 else 1 / -opcao


def restaurar_julgamentos() -> None:
    """Callback do botão: roda antes dos sliders serem desenhados, então pode trocar o valor deles.

    Alterar o estado de um widget depois de ele existir na página dá StreamlitAPIException.
    """
    for (a, b), v in ahp.JULGAMENTOS_PADRAO.items():
        st.session_state[chave_estado(a, b)] = para_opcao(v)


for (a, b), v in ahp.JULGAMENTOS_PADRAO.items():
    st.session_state.setdefault(chave_estado(a, b), para_opcao(v))

c1, c2 = st.columns([1.15, 1], gap="large")
with c1:
    st.subheader("1. Compare os Critérios Dois a Dois")
    st.caption("Para cada par, quanto um critério é mais importante que o outro para decidir onde agir primeiro "
               "(escala de Saaty: 1 = igual, 3 = moderadamente, 5 = fortemente, 7 = muito, 9 = extremamente).")
    julgamentos = {}
    for a, b in ahp.pares(CHAVES):
        na, nb = CRIT[a].nome, CRIT[b].nome

        def rotulo(o, na=na, nb=nb):
            if o == 1:
                return "igual importância"
            return f"{na} {o}× mais" if o > 0 else f"{nb} {-o}× mais"

        op = st.select_slider(f"{na} × {nb}", OPCOES, key=chave_estado(a, b), format_func=rotulo)
        julgamentos[(a, b)] = para_valor(op)
    st.button("Voltar à proposta inicial do grupo", icon=":material/restart_alt:", on_click=restaurar_julgamentos)

m = ahp.matriz_de_comparacao(julgamentos, CHAVES)
w = dict(zip(CHAVES, ahp.pesos(m)))
rc = ahp.razao_consistencia(m)

with c2:
    st.subheader("2. Pesos Resultantes")
    pesos = pd.DataFrame({"criterio": [CRIT[k].nome for k in CHAVES], "chave": CHAVES, "peso": [w[k] * 100 for k in CHAVES]})
    pesos["rotulo"] = pesos["peso"].map(lambda v: metricas.porcentagem(v, 1))
    base = alt.Chart(pesos).encode(
        y=alt.Y("criterio:N", sort=pesos.sort_values("peso", ascending=False)["criterio"].tolist(), title=None,
                axis=alt.Axis(labelOverlap=False)),
        x=alt.X("peso:Q", title="peso (%)", scale=alt.Scale(domain=[0, max(70, pesos["peso"].max() + 10)])),
        tooltip=[alt.Tooltip("criterio:N", title="Critério"), alt.Tooltip("rotulo:N", title="Peso")],
    )
    st.altair_chart((base.mark_bar().encode(color=alt.Color(
        "chave:N", scale=alt.Scale(domain=list(CORES), range=list(CORES.values())), legend=None))
        + base.mark_text(align="left", dx=4, color=TEXTO).encode(text="rotulo:N")).properties(height=alt.Step(34)),
        width="stretch")
    ok = rc <= ahp.RC_ACEITAVEL
    kpi(st, "Razão de consistência (RC)", metricas.porcentagem(rc * 100, 1),
        "julgamentos coerentes (RC ≤ 10%)" if ok else "incoerente: revise as comparações",
        "Compara a coerência dos julgamentos com a de comparações feitas ao acaso. Se A > B e B > C, então A deve "
        "ser > C. Acima de 10%, os pesos não devem ser usados.")
    if not ok:
        st.warning("RC acima de 10%: algum julgamento contradiz os outros. O mapa abaixo usa estes pesos mesmo assim, "
                   "só para você ver o efeito.", icon=":material/warning:")

# --- Índice ---------------------------------------------------------------------------------------------
ind = tabela("indicadores_bairro").set_index("bairro_oficial")
r = ahp.indice_prioridade(ind, w)
r["destaque"] = True
if f.rpas:
    r["destaque"] &= r["rpa"].isin(f.rpas)
if f.bairros:
    r["destaque"] &= r.index.isin(f.bairros)
r["indice_txt"] = r["indice"].map(lambda v: metricas.numero(v, 1))
for k in CHAVES:
    r[f"{k}_txt"] = r[CRIT[k].coluna].map(lambda v: metricas.numero(v, 1))

st.subheader("3. Onde Agir Primeiro")
c1, c2 = st.columns([1, 1.15], gap="large")
with c1:
    tabela_mapa = r.reset_index()
    campos = ["nome", "rpa", "indice", "indice_txt", "posicao", "destaque"] + [f"{k}_txt" for k in CHAVES]
    mapa = alt.Chart(alt.Data(values=malha()["features"])).mark_geoshape(stroke="white", strokeWidth=0.7).transform_lookup(
        lookup="properties.bairro_oficial", from_=alt.LookupData(tabela_mapa, "bairro_oficial", campos),
    ).encode(
        color=alt.condition("isValid(datum.indice)", alt.Color(
            "indice:Q", title="índice de prioridade (0 a 10)", scale=alt.Scale(range=RAMPA, domain=[0, ahp.NOTA_MAXIMA]),
            legend=alt.Legend(orient="bottom", direction="horizontal", gradientLength=220, titleLimit=300)),
            alt.value("#EEEEEE")),
        opacity=alt.condition("datum.destaque", alt.value(1), alt.value(0.25)),
        tooltip=[alt.Tooltip("nome:N", title="Bairro"), alt.Tooltip("posicao:Q", title="Posição"),
                 alt.Tooltip("indice_txt:N", title="Índice")]
                + [alt.Tooltip(f"{k}_txt:N", title=f"{CRIT[k].nome} ({CRIT[k].unidade})") for k in CHAVES],
    ).project(type="mercator").properties(height=520)
    st.altair_chart(mapa, width="stretch")
    leitura("Quanto mais escuro, maior a prioridade. Cinza: bairros com menos de 1.000 moradores, fora do índice.")

with c2:
    lista = r[r["destaque"]].head(15)
    longo = lista.reset_index().melt(id_vars=["bairro_oficial", "nome", "posicao", "indice"],
                                     value_vars=[f"contrib_{k}" for k in CHAVES], var_name="crit", value_name="pontos")
    longo["chave"] = longo["crit"].str.replace("contrib_", "")
    longo["criterio"] = longo["chave"].map(lambda k: CRIT[k].nome)
    longo["rotulo_bairro"] = longo["posicao"].astype(str) + "º · " + longo["nome"]
    longo["pontos_txt"] = longo["pontos"].map(lambda v: metricas.numero(v, 1))
    longo["indice_txt"] = longo["indice"].map(lambda v: metricas.numero(v, 1))
    ordem = (lista["posicao"].astype(str) + "º · " + lista["nome"]).tolist()
    titulo_lista = "Os 15 Bairros com Maior Índice" + (" no Recorte" if f.territorio_ativo else "")
    st.markdown(f"**{titulo_lista}** · quanto cada critério contribui")
    st.markdown("<div style='font-size:0.85rem'>" + " &nbsp; ".join(
        f"<span style='color:{CORES[k]}'>■</span> {CRIT[k].nome}" for k in CHAVES) + "</div>", unsafe_allow_html=True)
    barras = alt.Chart(longo).mark_bar(stroke="white", strokeWidth=1).encode(
        y=alt.Y("rotulo_bairro:N", sort=ordem, title=None, axis=alt.Axis(labelLimit=220, labelOverlap=False)),
        x=alt.X("pontos:Q", title="pontos do índice (0 a 10)", stack="zero", scale=alt.Scale(domain=[0, ahp.NOTA_MAXIMA])),
        color=alt.Color("criterio:N", title=None,
                        scale=alt.Scale(domain=[CRIT[k].nome for k in CHAVES], range=[CORES[k] for k in CHAVES]),
                        legend=None),
        order=alt.Order("ordem_crit:Q"),
        tooltip=[alt.Tooltip("nome:N", title="Bairro"), alt.Tooltip("criterio:N", title="Critério"),
                 alt.Tooltip("pontos_txt:N", title="Pontos"), alt.Tooltip("indice_txt:N", title="Índice total")],
    ).transform_calculate(ordem_crit=f"indexof({CHAVES}, datum.chave)").properties(height=alt.Step(24))
    st.altair_chart(barras, width="stretch")
    leitura("Barras mais longas, prioridade maior. A cor mostra o porquê: um bairro pode subir por risco (morros), "
            "por vulnerabilidade, por pedidos que passaram do prazo ou por problemas que voltam.")

# --- Sensibilidade --------------------------------------------------------------------------------------
st.subheader("4. O Resultado Depende Muito dos Pesos?")
sens = ahp.sensibilidade(ind, w, top=10)
quadro = sens.pivot(index="criterio", columns="fator", values="mantidos_no_top").reindex([CRIT[k].nome for k in CHAVES])
quadro.columns = [f"peso × {str(c).replace('.', ',')}" for c in quadro.columns]
quadro.index.name = "Critério"
st.dataframe(quadro, width="stretch",
             column_config={c: st.column_config.ProgressColumn(c, min_value=0, max_value=10, format="%d de 10")
                            for c in quadro.columns})
pior = sens.loc[sens["mantidos_no_top"].idxmin()]
leitura(f"Cada célula muda o peso de um critério (metade, três quartos, uma vez e um quarto, uma vez e meia), "
        f"redistribui o resto e conta quantos dos 10 primeiros continuam no top 10. Com os pesos atuais, o caso "
        f"mais sensível é <b>{pior['criterio']} × {str(pior['fator']).replace('.', ',')}</b>, que mantém "
        f"{int(pior['mantidos_no_top'])} de 10. Se quase tudo fica acima de 7, o ranking é estável e a discussão "
        "com especialistas pode focar nos poucos bairros de fronteira.")
st.caption("AHP não é aprendizado de máquina e não substitui o bônus de modelagem preditiva. Ele torna explícito e "
           "auditável um critério que hoje é implícito. Risco e vulnerabilidade andam juntos em parte (ρ ≈ 0,37), então "
           "os bairros de morro somam pontos nos dois.")
