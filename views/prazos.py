import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from src import filtros, metricas
from src.componentes import kpi, leitura
from src.config import AZUL, AZUL25, AZUL40, AZUL70, NAVY, TEXTO, eixo_numero, nome_categoria
from src.dados import tabela

f = filtros.atuais()

st.title("Prazos")
st.markdown("**Quem demora está demorando mais.** A maioria dos pedidos do 156 é atendida em poucos dias, mas a "
            "cauda longa cresceu. Por isso o prazo aparece em percentis e por categoria: a média engana "
            "(no 156 ela é cerca de dez vezes a mediana).")
filtros.legenda(f, {"Base": "pedidos ATENDIDOS do 156; os abertos não têm tempo final e entram só no estoque, no fim da página."})

praz = f.aplicar(tabela("prazos_156"))
sem_mesmo_dia = st.toggle(
    "Tirar os pedidos fechados no mesmo dia", value=False,
    help="Prazo de zero dias costuma ser encerramento administrativo (pedido cancelado, repassado ou fechado na "
         "triagem), não execução. Em pavimentação e drenagem, isso chegou a 70–80% dos fechamentos em alguns anos.")
if sem_mesmo_dia:
    praz = praz[praz["dias"] > 0]
if praz.empty:
    st.info("Sem pedidos atendidos do 156 para os filtros escolhidos.")
    st.stop()

total = praz["n"].sum()
mediana = metricas.quantil_ponderado(praz["dias"], praz["n"], 0.5)
p90 = metricas.quantil_ponderado(praz["dias"], praz["n"], 0.9)
mesmo_dia = praz.loc[praz["dias"] == 0, "n"].sum() / total * 100
acima_90 = praz.loc[praz["dias"] > 90, "n"].sum() / total * 100

k1, k2, k3, k4 = st.columns(4)
kpi(k1, "Metade sai em até", metricas.dias(mediana), "mediana",
    f"Mediana dos dias até a última movimentação, em {metricas.numero(total)} pedidos atendidos.")
kpi(k2, "1 em cada 10 leva mais de", metricas.dias(p90), "p90",
    "Percentil 90: o limite da cauda longa. É o número que mais piorou nos últimos anos.")
kpi(k3, "Fechados no mesmo dia", metricas.porcentagem(mesmo_dia), "prazo de zero dias",
    "Use o botão acima para tirá-los da conta e ver só os prazos de execução.")
kpi(k4, "Mais de 90 dias", metricas.porcentagem(acima_90, 1), "dos pedidos atendidos",
    "Parcela dos atendidos que levou mais de três meses.")

# --- Evolução por ano --------------------------------------------------------------------------------
c1, c2 = st.columns([1.15, 1], gap="large")
por_ano = metricas.percentis_por_grupo(praz, ["ano"])
linhas = por_ano.melt(id_vars="ano", value_vars=["mediana", "p90"], var_name="medida", value_name="dias")
linhas["medida"] = linhas["medida"].map({"mediana": "mediana", "p90": "p90 (1 em cada 10 leva mais)"})
linhas["rotulo"] = linhas["dias"].map(metricas.dias)
with c1:
    st.markdown("**O Prazo Piorou na Cauda (H4)**")
    base = alt.Chart(linhas).encode(
        x=alt.X("ano:O", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("dias:Q", title="dias até atender"),
        color=alt.Color("medida:N", title=None, scale=alt.Scale(range=[AZUL40, NAVY])),
        tooltip=[alt.Tooltip("ano:O", title="Ano"), alt.Tooltip("medida:N", title="Medida"),
                 alt.Tooltip("rotulo:N", title="Prazo")],
    )
    st.altair_chart((base.mark_line() + base.mark_point(size=55)).properties(height=300), width="stretch")
    leitura("A mediana quase não se move; o p90 sobe a partir de 2021. Em 2024–2026 a cauda ainda está incompleta: "
            "pedidos abertos há muito tempo só entram aqui quando forem atendidos.")

FAIXAS = [(-1, 0, "mesmo dia"), (0, 7, "1–7 d"), (7, 30, "8–30 d"), (30, 90, "31–90 d"),
          (90, 365, "91–365 d"), (365, np.inf, "> 1 ano")]
faixa = pd.cut(praz["dias"], [a for a, _, _ in FAIXAS] + [np.inf], labels=[r for _, _, r in FAIXAS])
dist = praz.groupby(faixa, observed=False)["n"].sum().reset_index()
dist.columns = ["faixa", "n"]
dist["pct"] = dist["n"] / dist["n"].sum() * 100
dist["rotulo"] = dist["pct"].map(lambda v: metricas.porcentagem(v, 1))
ordem = [r for _, _, r in FAIXAS]
with c2:
    st.markdown("**Em Quanto Tempo os Pedidos São Atendidos**")
    b = alt.Chart(dist).encode(
        x=alt.X("faixa:N", sort=ordem, title=None, axis=alt.Axis(labelAngle=0, labelLimit=90, labelOverlap=False)),
        y=alt.Y("pct:Q", title="% dos atendidos"),
        tooltip=[alt.Tooltip("faixa:N", title="Faixa"), alt.Tooltip("rotulo:N", title="Pedidos")],
    )
    cores = alt.Scale(domain=ordem, range=[AZUL25, AZUL40, AZUL70, AZUL, NAVY, NAVY])
    st.altair_chart((b.mark_bar(size=40).encode(color=alt.Color("faixa:N", scale=cores, legend=None))
                     + b.mark_text(dy=-8, color=TEXTO, fontSize=11).encode(text="rotulo:N")).properties(height=300),
                    width="stretch")
    leitura("A distribuição é muito assimétrica: a maior parte se resolve em uma semana, e uma fatia pequena leva "
            "meses ou anos (obras como escadaria e macrodrenagem).")

# --- Por categoria ------------------------------------------------------------------------------------
st.subheader("Cada Categoria Tem o Seu Prazo")
por_cat = metricas.percentis_por_grupo(praz, ["categoria"])
minimo = 1000 if total > 200_000 else 30
por_cat = por_cat[por_cat["pedidos"] >= minimo].copy()
por_cat["nome"] = por_cat["categoria"].map(nome_categoria)
for c in ("mediana", "p90"):
    por_cat[f"{c}_txt"] = por_cat[c].map(metricas.dias)
    por_cat[f"{c}_plot"] = por_cat[c] + 1          # escala log não aceita zero: desenha dias + 1
por_cat["pedidos_txt"] = por_cat["pedidos"].map(metricas.numero)
por_cat["mesmo_dia_txt"] = por_cat["pct_mesmo_dia"].map(metricas.porcentagem)
ordem_cat = por_cat.sort_values("p90", ascending=False)["nome"].tolist()
dica = [alt.Tooltip("nome:N", title="Categoria"), alt.Tooltip("mediana_txt:N", title="Mediana"),
        alt.Tooltip("p90_txt:N", title="p90"), alt.Tooltip("mesmo_dia_txt:N", title="No mesmo dia"),
        alt.Tooltip("pedidos_txt:N", title="Pedidos")]
eixo_y = alt.Y("nome:N", sort=ordem_cat, title=None, axis=alt.Axis(labelLimit=220, labelOverlap=False))
escala = alt.Scale(type="log", domain=[1, 4000])
eixo_x = alt.Axis(values=[1, 2, 8, 31, 91, 366, 1096, 3651], labelExpr="datum.value - 1", title="dias até atender (escala log)")
faixa_cat = alt.Chart(por_cat).mark_rule(strokeWidth=3, color=AZUL25).encode(
    y=eixo_y, x=alt.X("mediana_plot:Q", scale=escala, axis=eixo_x), x2="p90_plot:Q", tooltip=dica)
pontos_med = alt.Chart(por_cat).mark_point(filled=True, size=90, color=AZUL40).encode(
    y=eixo_y, x="mediana_plot:Q", tooltip=dica)
pontos_p90 = alt.Chart(por_cat).mark_point(filled=True, size=90, color=NAVY).encode(
    y=eixo_y, x="p90_plot:Q", tooltip=dica)
st.altair_chart((faixa_cat + pontos_med + pontos_p90).properties(height=alt.Step(28)), width="stretch")
leitura(f"Ponto claro = mediana; ponto escuro = p90; a linha entre eles é onde fica a maior parte dos pedidos. "
        f"Categorias com {metricas.numero(minimo)} pedidos atendidos ou mais, da mais lenta para a mais rápida. Um "
        "semáforo de prazo precisa de referência por categoria: 10 dias é atraso em iluminação e é rápido em drenagem.")

# --- Estoque aberto -----------------------------------------------------------------------------------
st.subheader("A Fila de Hoje: Pedidos Abertos que Já Passaram do Prazo Típico")
estoque = f.aplicar(tabela("estoque_156"), ano=False)
if estoque.empty:
    st.caption("Sem pedidos abertos para o território ou a categoria escolhidos.")
else:
    e = estoque.groupby("categoria")[["abertos", "acima_prazo_tipico"]].sum().reset_index()
    e = e[e["abertos"] >= 20].copy()
    e["no_prazo"] = e["abertos"] - e["acima_prazo_tipico"]
    e["nome"] = e["categoria"].map(nome_categoria)
    e = e.nlargest(12, "acima_prazo_tipico")
    longo = e.melt(id_vars=["nome", "abertos"], value_vars=["acima_prazo_tipico", "no_prazo"],
                   var_name="situacao", value_name="n")
    longo["situacao"] = longo["situacao"].map({"acima_prazo_tipico": "passou do prazo típico",
                                                "no_prazo": "ainda dentro do prazo típico"})
    longo["n_txt"] = longo["n"].map(metricas.numero)
    c1, c2 = st.columns([1.6, 1], gap="large")
    with c1:
        barras = alt.Chart(longo).mark_bar(stroke="white", strokeWidth=1).encode(
            y=alt.Y("nome:N", sort=e.sort_values("acima_prazo_tipico", ascending=False)["nome"].tolist(), title=None,
                    axis=alt.Axis(labelLimit=200, labelOverlap=False)),
            x=alt.X("n:Q", axis=eixo_numero("pedidos abertos")),
            color=alt.Color("situacao:N", title=None, scale=alt.Scale(
                domain=["passou do prazo típico", "ainda dentro do prazo típico"], range=[NAVY, AZUL25])),
            order=alt.Order("situacao:N", sort="descending"),
            tooltip=[alt.Tooltip("nome:N", title="Categoria"), alt.Tooltip("situacao:N", title="Situação"),
                     alt.Tooltip("n_txt:N", title="Pedidos")],
        ).properties(height=alt.Step(26))
        st.altair_chart(barras, width="stretch")
        leitura("O prazo típico é o da própria categoria. Onde ele é curto (iluminação, limpeza), quase todo pedido "
                "ainda aberto já passou dele; em drenagem, cujo p90 chega perto de três anos, quase nenhum passou. "
                "As 12 categorias com mais pedidos atrasados.")
    with c2:
        tot_abertos, tot_atraso = estoque["abertos"].sum(), estoque["acima_prazo_tipico"].sum()
        kpi(st, "Pedidos abertos", metricas.numero(tot_abertos), "arquivos 2025 e 2026 do 156")
        kpi(st, "Passaram do prazo típico", metricas.porcentagem(tot_atraso / tot_abertos * 100),
            f"{metricas.numero(tot_atraso)} pedidos",
            "Idade do pedido em 07/10/2026 maior que o p90 dos atendidos da mesma categoria (2021–2025).")
        leitura("Só os arquivos de 2025 e 2026 entram: em arquivos antigos, o pedido 'aberto' pode ter só congelado "
                "no retrato do ano (N3). Este estoque alimenta o critério Atraso do índice de prioridade.")
