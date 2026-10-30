import altair as alt
import pandas as pd
import streamlit as st

from src import filtros, metricas
from src.componentes import kpi, leitura
from src.config import AZUL, AZUL40, CINZA, NAVY, TEXTO, nome_categoria, titulo
from src.dados import tabela

f = filtros.atuais()

st.title("Reincidência")
st.markdown("**Repetir não é duplicar.** Boa parte dos pedidos do 156 cai num local + serviço que já teve pedido, "
            "e na maioria das vezes o problema **voltou** semanas ou meses depois. Um ponto com 100 pedidos é um "
            "problema, não cem.")
filtros.legenda(f, {"Definição": "156 de 2015 a 2025, só endereços com número; chave = local + serviço "
                                 "(o local é um pseudônimo do endereço, que não aparece no painel)."})

rep = f.aplicar(tabela("reincidencia_156"))
if rep.empty:
    st.info("Sem pedidos do 156 para os filtros escolhidos. A reincidência é medida de 2015 a 2025.")
    st.stop()

sem_generico = st.toggle(
    "Tirar da conta os endereços genéricos", value=False,
    help="Alguns 'locais' somam centenas de pedidos do mesmo serviço em vários anos (por exemplo, 1.277 pedidos de "
         "lâmpada apagada). Quase certamente é um endereço genérico ou um circuito inteiro. Ligado, os pedidos "
         "em locais acima do p99 de pedidos por local deixam de contar como repetidos.")
rep = rep.assign(rep_contados=rep["repetidos"] - (rep["repetidos_local_generico"] if sem_generico else 0))

total = rep["registros"].sum()
intervalos = rep[["intervalo_duplicidade", "intervalo_intermediario", "intervalo_reincidencia"]].sum()
cron = f.aplicar(tabela("locais_cronicos_156"), ano=False)
cron = cron[(cron["ultimo_ano"] >= f.anos[0]) & (cron["primeiro_ano"] <= f.anos[1])]

k1, k2, k3, k4 = st.columns(4)
kpi(k1, "Em local repetido", metricas.porcentagem(rep["rep_contados"].sum() / total * 100, 1),
    f"de {metricas.numero(total)} pedidos",
    "Pedidos cujo local + serviço aparece 2 ou mais vezes entre 2015 e 2025.")
kpi(k2, "O problema voltou", metricas.porcentagem(intervalos["intervalo_reincidencia"] / intervalos.sum() * 100),
    "30 dias ou mais depois",
    "Entre os pedidos que repetem um anterior, a parte em que o intervalo foi de 30 dias ou mais: reincidência.")
kpi(k3, "Pedido em dobro", metricas.porcentagem(intervalos["intervalo_duplicidade"] / intervalos.sum() * 100),
    "até 7 dias depois",
    "Repetições em até 7 dias: provável duplicidade (o mesmo problema registrado de novo antes de ser resolvido).")
kpi(k4, "Pontos crônicos", metricas.numero((cron["pedidos"] >= 10).sum()), "locais com 10+ pedidos",
    "Locais + serviço com 10 pedidos ou mais na janela 2015–2025, ativos no período escolhido.")

# --- Por categoria (clique) e tipo de repetição ------------------------------------------------------
st.subheader("Onde Mais se Repete, e Como")
por_cat = rep.groupby("categoria").agg(pedidos=("registros", "sum"), repetidos=("rep_contados", "sum"),
                                       dup=("intervalo_duplicidade", "sum"), inter=("intervalo_intermediario", "sum"),
                                       reinc=("intervalo_reincidencia", "sum")).reset_index()
minimo = 2000 if total > 100_000 else 50
por_cat = por_cat[por_cat["pedidos"] >= minimo].copy()
por_cat["pct"] = por_cat["repetidos"] / por_cat["pedidos"] * 100
por_cat["nome"] = por_cat["categoria"].map(nome_categoria)
por_cat["rotulo"] = por_cat["pct"].map(lambda v: metricas.porcentagem(v))
por_cat["pedidos_txt"] = por_cat["pedidos"].map(metricas.numero)

c1, c2 = st.columns([1.25, 1], gap="large")
with c1:
    st.markdown("**% dos Pedidos em Local Repetido, por Categoria**")
    clique = alt.selection_point(fields=["nome"], name="cat")
    base = alt.Chart(por_cat).encode(
        y=alt.Y("nome:N", sort="-x", title=None, axis=alt.Axis(labelLimit=200, labelOverlap=False)),
        x=alt.X("pct:Q", title="% em local repetido", scale=alt.Scale(domain=[0, 100])),
        tooltip=[alt.Tooltip("nome:N", title="Categoria"), alt.Tooltip("rotulo:N", title="Em local repetido"),
                 alt.Tooltip("pedidos_txt:N", title="Pedidos")],
    )
    barras = base.mark_bar().encode(
        color=alt.condition(clique, alt.value(AZUL), alt.value(AZUL40))).add_params(clique)
    grafico = (barras + base.mark_text(align="left", dx=4, color=TEXTO, fontSize=11).encode(text="rotulo:N"))
    evento = st.altair_chart(grafico.properties(height=alt.Step(24)), width="stretch",
                             on_select="rerun", key="rep_cat")
    leitura(f"Categorias com {metricas.numero(minimo)} pedidos ou mais no recorte. Clique numa barra para ver, ao lado, "
            "como os pedidos dela se repetem.")

escolhidas = [p["nome"] for p in evento.selection.get("cat", [])] if evento else []
alvo = por_cat[por_cat["nome"].isin(escolhidas)] if escolhidas else por_cat
recorte_cat = escolhidas[0] if escolhidas else "todas as categorias"
faixas = pd.DataFrame({
    "tipo": ["Duplicidade · até 7 dias", "Intermediário · 8 a 29 dias", "Reincidência · 30 dias ou mais"],
    "n": [alvo["dup"].sum(), alvo["inter"].sum(), alvo["reinc"].sum()],
})
faixas["pct"] = faixas["n"] / faixas["n"].sum() * 100 if faixas["n"].sum() else 0
faixas["rotulo"] = faixas["pct"].map(lambda v: metricas.porcentagem(v))
with c2:
    st.markdown(f"**{titulo('Intervalo até o pedido anterior no mesmo local · ' + recorte_cat)}**")
    b = alt.Chart(faixas).encode(
        x=alt.X("tipo:N", sort=list(faixas["tipo"]), title=None,
                axis=alt.Axis(labelAngle=0, labelExpr="split(datum.value, ' · ')")),
        y=alt.Y("pct:Q", title="% das repetições", scale=alt.Scale(domain=[0, 100])),
        tooltip=[alt.Tooltip("tipo:N", title="Tipo"), alt.Tooltip("rotulo:N", title="Participação")],
    )
    st.altair_chart((b.mark_bar(size=56).encode(color=alt.Color(
        "tipo:N", scale=alt.Scale(domain=list(faixas["tipo"]), range=[AZUL40, CINZA, NAVY]), legend=None))
        + b.mark_text(dy=-8, color=TEXTO).encode(text="rotulo:N")).properties(height=300), width="stretch")
    leitura("Duplicidade se resolve na triagem (juntar pedidos). Reincidência é outro problema: o serviço foi feito "
            "e não durou, ou não foi feito. Em quase todas as categorias, a reincidência é a maior parte.")

# --- Pontos crônicos ----------------------------------------------------------------------------------
st.subheader("Pontos Crônicos")
nomes = dict(zip(tabela("bairros")["bairro_oficial"], tabela("bairros")["nome"]))
lista = cron.head(300).assign(
    bairro=lambda d: d["bairro_oficial"].map(nomes),
    categoria_nome=lambda d: d["categoria"].map(nome_categoria),
    servico_nome=lambda d: d["servico"].map(nome_categoria),
    anos=lambda d: d["primeiro_ano"].astype(str) + "–" + d["ultimo_ano"].astype(str),
)
st.dataframe(
    lista[["bairro", "categoria_nome", "servico_nome", "pedidos", "dias_distintos", "anos"]].head(50),
    hide_index=True, width="stretch", height=380,
    column_config={
        "bairro": "Bairro", "categoria_nome": "Categoria", "servico_nome": "Serviço",
        "pedidos": st.column_config.ProgressColumn("Pedidos", format="%d", min_value=0,
                                                   max_value=int(lista["pedidos"].max()) if len(lista) else 1),
        "dias_distintos": st.column_config.NumberColumn("Dias com pedido", format="%d"),
        "anos": "Período",
    },
)
leitura("Cada linha é um endereço com muitos pedidos do mesmo serviço; o endereço não é mostrado (privacidade: no "
        "dataset ele é um pseudônimo). Para a operação, isso vira uma lista de locais para vistoria: um ponto com "
        "dezenas de pedidos pede uma solução definitiva, não mais um atendimento. Os primeiros da lista, com "
        "centenas de pedidos, provavelmente são endereços genéricos ou circuitos inteiros de iluminação (N3, 6.4).")
