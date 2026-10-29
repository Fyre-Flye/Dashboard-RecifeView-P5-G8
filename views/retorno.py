import altair as alt
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import filtros, metricas
from src.componentes import kpi, leitura
from src.config import (AZUL, AZUL25, AZUL40, AZUL70, CINZA, DESTAQUE, FONTE, NAVY, RAMPA, TEXTO, eixo_numero,
                        nome_categoria, nome_orgao)
from src.dados import tabela

f = filtros.atuais()

st.title("Retorno e fragmentação")
st.markdown("Depois que a demanda entra, ela **muda de mão** entre órgãos e **raramente volta** com resposta registrada. "
            "A Câmara é a única fonte pública que mostra o caminho inteiro, do pedido do vereador até a resposta da Prefeitura.")
filtros.legenda(f, {"Ouvidoria": "não tem bairro nem a mesma classificação de serviço; o último bloco segue só o período."})

ind = f.aplicar(tabela("camara_indicacoes"))
if ind.empty:
    st.info("Nenhuma indicação da Câmara para os filtros escolhidos. A Câmara cobre 2021–2025 e só as categorias "
            "de serviço urbano citadas nas ementas.")
    st.stop()

enviadas = ind["enviada"].sum()
respondidas = ind["respondida"].sum()
mediana_resposta = ind["dias_ate_resposta"].median()

k1, k2, k3, k4 = st.columns(4)
kpi(k1, "Indicações de vereadores", metricas.numero(len(ind)), "pedidos à Prefeitura",
    "Indicações (pedidos de providência) apresentadas na Câmara Municipal no recorte, lidas do sistema público SAGL.")
kpi(k2, "Chegam à Prefeitura", metricas.porcentagem(enviadas / len(ind) * 100),
    f"envio em {metricas.dias(ind['dias_ate_envio'].median())}",
    "Indicações com envio à Prefeitura registrado na tramitação, e a mediana de dias até o envio.")
kpi(k3, "Voltam com resposta", metricas.porcentagem(respondidas / len(ind) * 100),
    f"{metricas.numero(respondidas)} indicações",
    "Indicações com resposta da Prefeitura registrada na tramitação. Sem resposta registrada não quer dizer "
    "que o serviço não foi feito: quer dizer que a informação não voltou.")
kpi(k4, "Tempo até a resposta", metricas.dias(mediana_resposta), "mediana",
    "Mediana dos dias entre a apresentação da indicação e a resposta registrada, só para as que têm resposta.")

# --- Funil e canal de envio --------------------------------------------------------------------------
st.subheader("A perda está toda depois da entrada")
c1, c2 = st.columns([1, 1.25], gap="large")

etapas = pd.DataFrame({
    "etapa": ["Apresentadas na Câmara", "Enviadas à Prefeitura", "Com resposta registrada"],
    "n": [len(ind), enviadas, respondidas],
})
etapas["pct"] = etapas["n"] / len(ind) * 100
etapas["rotulo"] = etapas.apply(lambda r: f"{metricas.numero(r['n'])} ({metricas.porcentagem(r['pct'])})", axis=1)
funil = alt.Chart(etapas).encode(
    y=alt.Y("etapa:N", sort=list(etapas["etapa"]), title=None, axis=alt.Axis(labelLimit=200, labelOverlap=False)),
    x=alt.X("n:Q", axis=eixo_numero("indicações"), scale=alt.Scale(domain=[0, len(ind) * 1.6])),
    tooltip=[alt.Tooltip("etapa:N", title="Etapa"), alt.Tooltip("rotulo:N", title="Indicações")],
)
barras = funil.mark_bar(height=34).encode(
    color=alt.Color("etapa:N", scale=alt.Scale(domain=list(etapas["etapa"]), range=[AZUL40, AZUL, NAVY]), legend=None))
with c1:
    st.markdown("**Funil das indicações**")
    st.altair_chart((barras + funil.mark_text(align="left", dx=6, fontSize=12, color=TEXTO).encode(text="rotulo:N"))
                    .properties(height=200), width="stretch")
    leitura("Quase tudo sai da Câmara em poucos dias. A queda acontece dentro da Prefeitura, no caminho de volta: "
            "é a retaguarda descrita no desafio do Banco de Oportunidades.")

CANAL_CURTO = {"OFICIO": "ofício", "PROTOCOLO NA PREFEITURA": "protocolo", "LOTE JSON SISTEMA PCR": "lote JSON",
               "SISTEMA SEGOV": "sistema SEGOV", "ENVIADO AO EXECUTIVO": "enviado ao Executivo", "E-MAIL": "e-mail"}
por_ano = ind.groupby("ano").agg(indicacoes=("respondida", "size"), respondidas=("respondida", "sum"),
                                  canal=("canal_envio", lambda s: s.mode().iat[0] if s.notna().any() else "—"))
por_ano = por_ano.reset_index()
por_ano["pct"] = por_ano["respondidas"] / por_ano["indicacoes"] * 100
por_ano["canal_curto"] = por_ano["canal"].map(lambda c: CANAL_CURTO.get(c, str(c).lower()))
por_ano["rotulo"] = por_ano["pct"].map(lambda v: metricas.porcentagem(v, 1))
por_ano["eixo"] = por_ano["ano"].astype(str) + " · " + por_ano["canal_curto"]
canal = alt.Chart(por_ano).encode(
    x=alt.X("eixo:N", title="ano · canal de envio mais usado", sort=list(por_ano["eixo"]),
            axis=alt.Axis(labelAngle=0, labelExpr="split(datum.value, ' · ')")),
    y=alt.Y("pct:Q", title="% com resposta registrada", scale=alt.Scale(domain=[0, 60])),
    tooltip=[alt.Tooltip("ano:O", title="Ano"), alt.Tooltip("canal:N", title="Canal mais usado"),
             alt.Tooltip("rotulo:N", title="Com resposta")],
)
with c2:
    st.markdown("**Quando o envio vira sistema, a resposta aparece**")
    st.altair_chart((canal.mark_bar(size=46, color=AZUL) + canal.mark_text(dy=-8, color=TEXTO).encode(text="rotulo:N"))
                    .properties(height=260), width="stretch")
    leitura("De ofício e protocolo em papel para lote e sistema da SEGOV, a parte com resposta registrada sobe de "
            "menos de 1% para cerca de 45%. É o indício mais forte (H9) de que o encaminhamento digital e integrado "
            "reduz a perda. Anos recentes ainda podem receber resposta.")

# --- Para quem vai cada tipo de pedido --------------------------------------------------------------
st.subheader("O mesmo tipo de pedido vai para órgãos diferentes")
x = ind.dropna(subset=["categoria", "orgao"])
top_cat = x["categoria"].value_counts().head(9).index
top_org = x["orgao"].value_counts().head(7).index
x = x[x["categoria"].isin(top_cat)].assign(orgao=lambda d: d["orgao"].where(d["orgao"].isin(top_org), "OUTROS"))
tab = x.groupby(["categoria", "orgao"]).size().rename("n").reset_index()
tab["pct"] = tab["n"] / tab.groupby("categoria")["n"].transform("sum") * 100
tab["rotulo"] = tab["pct"].map(lambda v: f"{v:.0f}")
tab["categoria_nome"] = tab["categoria"].map(nome_categoria)
tab["orgao_nome"] = tab["orgao"].map(nome_orgao)
disp = (tab.sort_values("pct", ascending=False).groupby("categoria")
        .agg(principal=("orgao", "first"), pct_principal=("pct", "first")).reset_index())
orgaos_por_cat = ind.dropna(subset=["categoria", "orgao"]).groupby("categoria")["orgao"].nunique()
disp["orgaos"] = disp["categoria"].map(orgaos_por_cat)
ordem_cat = disp.sort_values("pct_principal")["categoria"].tolist()       # as mais espalhadas no topo
ordem_org = [nome_orgao(o) for o in top_org] + ["Outros"]
ordem_cat_nome = [nome_categoria(c) for c in ordem_cat]

c1, c2 = st.columns([1.6, 1], gap="large")
clique = alt.selection_point(fields=["categoria"], name="cat", empty=True)
calor = alt.Chart(tab).encode(
    x=alt.X("orgao_nome:N", sort=ordem_org, title=None,
            axis=alt.Axis(labelAngle=-35, orient="top", labelLimit=160, labelOverlap=False, labelAlign="left")),
    y=alt.Y("categoria_nome:N", sort=ordem_cat_nome, title=None, axis=alt.Axis(labelLimit=180, labelOverlap=False)),
    tooltip=[alt.Tooltip("categoria_nome:N", title="Categoria"), alt.Tooltip("orgao:N", title="Órgão"),
             alt.Tooltip("rotulo:N", title="% da categoria"), alt.Tooltip("n:Q", title="Indicações")],
)
celulas = calor.mark_rect(stroke="white", strokeWidth=2).encode(
    color=alt.Color("pct:Q", scale=alt.Scale(range=RAMPA, domain=[0, 100]), legend=None),
    opacity=alt.condition(clique, alt.value(1), alt.value(0.35)),
).add_params(clique)
textos = calor.mark_text(fontSize=11).encode(
    text="rotulo:N", color=alt.condition("datum.pct > 55", alt.value("white"), alt.value(TEXTO)))
with c1:
    evento = st.altair_chart((celulas + textos).properties(height=360), width="stretch",
                             on_select="rerun", key="calor_destino")
    leitura("Cada linha soma 100%: para onde vão as indicações de cada categoria. Clique numa linha para ver o "
            "caminho dela até o desfecho ao lado. Categoria e órgão vêm da ementa (rótulo fraco).")

selecionadas = [p["categoria"] for p in evento.selection.get("cat", [])] if evento else []
foco = selecionadas[0] if selecionadas else ordem_cat[0]
with c2:
    sub = ind[ind["categoria"] == foco].dropna(subset=["orgao"])
    org_top = sub["orgao"].value_counts().head(5).index
    sub = sub.assign(orgao=sub["orgao"].where(sub["orgao"].isin(org_top), "OUTROS"))
    DESFECHO = {"ENVIADO E COM RESPOSTA REGISTRADA": "com resposta", "ENVIADO, SEM RESPOSTA REGISTRADA": "sem resposta",
                "SEM ENVIO REGISTRADO": "sem envio", "RETIRADO/PREJUDICADO/REJEITADO": "retirada"}
    sub = sub.assign(desfecho=sub["desfecho"].map(DESFECHO).fillna("sem envio"))
    fluxo = sub.groupby(["orgao", "desfecho"]).size().rename("n").reset_index()
    orgs = fluxo.groupby("orgao")["n"].sum().sort_values(ascending=False).index.tolist()
    desf = [d for d in ["com resposta", "sem resposta", "sem envio", "retirada"] if d in set(fluxo["desfecho"])]
    curto = nome_orgao
    nos = [nome_categoria(foco)] + [curto(o) for o in orgs] + desf
    idx = {n: i for i, n in enumerate(nos)}
    cor_desf = {"com resposta": NAVY, "sem resposta": AZUL25, "sem envio": CINZA, "retirada": CINZA}
    origem, destino, valor, cor = [], [], [], []
    for o in orgs:
        nome = curto(o)
        origem.append(0); destino.append(idx[nome]); valor.append(int(fluxo.loc[fluxo.orgao == o, "n"].sum()))
        cor.append("rgba(15,98,254,0.25)")
    for _, r in fluxo.iterrows():
        nome = curto(r.orgao)
        origem.append(idx[nome]); destino.append(idx[r.desfecho]); valor.append(int(r.n))
        cor.append("rgba(6,42,95,0.45)" if r.desfecho == "com resposta" else "rgba(159,192,255,0.45)")
    cores_nos = [AZUL] + [AZUL70] * len(orgs) + [cor_desf[d] for d in desf]
    sankey = go.Figure(go.Sankey(
        node=dict(label=nos, color=cores_nos, pad=22, thickness=14, line=dict(width=0)),
        link=dict(source=origem, target=destino, value=valor, color=cor,
                  hovertemplate="%{source.label} → %{target.label}: %{value:,.0f}<extra></extra>"),
        valueformat=",.0f",
    ))
    sankey.update_layout(height=420, margin=dict(l=4, r=4, t=36, b=4), font=dict(family=FONTE, size=12, color=TEXTO),
                         title=dict(text=f"{nome_categoria(foco)}: órgão → desfecho", font=dict(size=14), x=0),
                         separators=",.")
    st.plotly_chart(sankey, width="stretch", config={"displayModeBar": False})
    linha = disp.set_index("categoria").loc[foco]
    leitura(f"<b>{nome_categoria(foco)}</b> vai para {int(linha['orgaos'])} órgãos; o principal "
            f"({nome_orgao(linha['principal'])}) recebe {metricas.porcentagem(linha['pct_principal'])}. "
            "Manutenção (limpeza, iluminação, drenagem) tem um destino dominante; pavimentação, escadaria, praças e "
            "risco se espalham.")

# --- Ouvidoria ----------------------------------------------------------------------------------------
st.subheader("Ouvidoria: por onde a manifestação entra")
ouv = f.aplicar(tabela("ouvidoria"), territorio=False, categoria=False)
ouv = ouv[ouv["canal_entrada"].notna()]
if ouv.empty:
    st.caption("A Ouvidoria publica o canal de entrada de 2018 a 2024; ajuste o período para ver este bloco.")
else:
    PRINCIPAIS = ["0800", "SITE", "E-MAIL", "ATENDIMENTO PESSOAL", "APP CONECTA RECIFE"]
    o = ouv.assign(canal=ouv["canal_entrada"].where(ouv["canal_entrada"].isin(PRINCIPAIS), "OUTROS"))
    o = o.groupby(["ano", "canal"])["n"].sum().reset_index()
    o["pct"] = o["n"] / o.groupby("ano")["n"].transform("sum") * 100
    o["rotulo"] = o["pct"].map(lambda v: metricas.porcentagem(v, 1))
    nomes = {"0800": "0800 (telefone)", "SITE": "site", "E-MAIL": "e-mail", "ATENDIMENTO PESSOAL": "presencial",
             "APP CONECTA RECIFE": "app Conecta Recife", "OUTROS": "outros"}
    o["canal_nome"] = o["canal"].map(nomes)
    ordem = [nomes[c] for c in PRINCIPAIS + ["OUTROS"]]
    cores = [AZUL40, AZUL70, AZUL, NAVY, DESTAQUE, AZUL25]     # o app é o único em laranja: é a ênfase do bloco
    c1, c2 = st.columns([1.6, 1], gap="large")
    with c1:
        g = alt.Chart(o).mark_bar(size=34, stroke="white", strokeWidth=1).encode(
            x=alt.X("ano:O", title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("pct:Q", title="% das manifestações", stack="normalize", axis=alt.Axis(format="%")),
            color=alt.Color("canal_nome:N", title="Canal", scale=alt.Scale(domain=ordem, range=cores), sort=ordem),
            order=alt.Order("ordem:Q"),
            tooltip=[alt.Tooltip("ano:O", title="Ano"), alt.Tooltip("canal_nome:N", title="Canal"),
                     alt.Tooltip("rotulo:N", title="Participação")],
        ).transform_calculate(ordem=f"indexof({ordem}, datum.canal_nome)").properties(height=280)
        st.altair_chart(g, width="stretch")
    with c2:
        app = o[o["canal"] == "APP CONECTA RECIFE"]
        ultimo = app[app["ano"] == app["ano"].max()] if not app.empty else app
        st.metric("App Conecta Recife na Ouvidoria",
                  metricas.porcentagem(ultimo["pct"].iat[0], 1) if not ultimo.empty else "—",
                  delta=f"em {int(ultimo['ano'].iat[0])}" if not ultimo.empty else None,
                  delta_color="off", delta_arrow="off", border=True)
        no_prazo = f.aplicar(tabela("ouvidoria"), territorio=False, categoria=False)
        pct_prazo = no_prazo.loc[no_prazo["no_prazo"] == "True", "n"].sum() / no_prazo["n"].sum() * 100
        st.metric("Respondidas no prazo", metricas.porcentagem(pct_prazo), delta="Ouvidoria, no período",
                  delta_color="off", delta_arrow="off", border=True)
        leitura("O telefone virou o canal dominante, e o app só aparece em 2023, com cerca de 3%. O problema não é "
                "falta de canal digital para o cidadão: é o que acontece depois que o pedido entra.")
