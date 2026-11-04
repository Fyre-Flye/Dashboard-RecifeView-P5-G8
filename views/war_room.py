"""War Room: protótipo de tela de sala de operações, para bater o olho.

Junta o que as outras páginas detalham num só quadro: o estoque aberto, a fila por nota, o que não voltou,
onde o atraso se concentra e o ritmo de entrada. Usa o último retrato das bases (não é tempo real) e a
cidade inteira, com os pesos padrão do AHP.
"""

import altair as alt
import pandas as pd
import streamlit as st

from src import ahp, metricas
from src.componentes import fontes, leitura
from src.config import AZUL, DESTAQUE, RAMPA, SEM_DADO, TEXTO_TEMA, eixo_numero, formato_br, nome_categoria
from src.dados import malha, resumo_preparacao, tabela

NOTA_ALTA = 7
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
num = metricas.numero

data_ref = pd.Timestamp(resumo_preparacao()["data_referencia_estoque"])
chaves = [c.chave for c in ahp.CRITERIOS]
pesos = dict(zip(chaves, ahp.pesos(ahp.matriz_de_comparacao(ahp.JULGAMENTOS_PADRAO, chaves))))
ind = tabela("indicadores_bairro").set_index("bairro_oficial")
estoque = tabela("estoque_156")
fila = ahp.indice_ocorrencias(tabela("ocorrencias_abertas_156"), ind, pesos)
camara = tabela("indicacoes_sem_resposta")
ouvidoria = tabela("manifestacoes_abertas_ouvidoria")


def painel(rotulo: str, valor: str, detalhe: str, alerta: bool = False) -> None:
    """Placa grande de sala de operações: rótulo, número e uma linha de contexto. Borda laranja = atenção."""
    cor = DESTAQUE if alerta else AZUL
    st.markdown(
        f"<div style='border:1px solid {cor}55;border-left:6px solid {cor};border-radius:10px;padding:14px 16px;"
        f"height:100%'><div style='font-size:.85rem;opacity:.75'>{rotulo}</div>"
        f"<div style='font-size:2.6rem;font-weight:700;line-height:1.1'>{valor}</div>"
        f"<div style='font-size:.85rem;opacity:.8'>{detalhe}</div></div>", unsafe_allow_html=True)


# --- Cabeçalho -------------------------------------------------------------------------------------------
st.title("War Room")
st.markdown(f"**Retrato de {data_ref:%d/%m/%Y}** · protótipo de tela de operações: o que está parado, o que não "
            "voltou e onde agir primeiro, num só quadro.")
st.caption("Cidade inteira (os filtros da barra lateral não valem aqui) e pesos padrão do AHP. Não é tempo real: o 156 vai "
           "até junho de 2026; a Câmara e a Ouvidoria, até dezembro de 2025. Para a sala, recolha a barra lateral e use "
           "o navegador em tela cheia (F11).")
fontes(["156_EMLURB", "DEFESA_CIVIL", "CAMARA_REQUERIMENTOS", "OUVIDORIA"])

# --- Placas ----------------------------------------------------------------------------------------------
abertos, atrasados = int(estoque["abertos"].sum()), int(estoque["acima_prazo_tipico"].sum())
prioritarios = int((fila["indice"] >= NOTA_ALTA).sum())
entrada = (tabela("demanda").query("fonte == '156_EMLURB'").groupby(["ano", "mes"])["n"].sum()
           .reset_index().sort_values(["ano", "mes"]))
completos = entrada.iloc[:-1]                      # o último mês do arquivo está incompleto
ultimo, media12 = completos.iloc[-1], completos.tail(12)["n"].mean()
variacao = (ultimo["n"] / media12 - 1) * 100

p = st.columns(5, gap="small")
with p[0]:
    painel("Pedidos abertos no 156", num(abertos),
           f"<b>{metricas.porcentagem(atrasados / abertos * 100)}</b> já passaram do prazo típico", alerta=True)
with p[1]:
    painel(f"Fila prioritária (nota ≥ {NOTA_ALTA})", num(prioritarios),
           f"{metricas.porcentagem(prioritarios / len(fila) * 100, 1)} dos abertos classificáveis")
with p[2]:
    painel("Indicações sem resposta", num(len(camara)),
           f"mediana de <b>{num(camara['idade_dias'].median())} dias</b> desde o envio", alerta=True)
with p[3]:
    painel("Ouvidoria além do prazo", num(len(ouvidoria)),
           f"mediana de {num(ouvidoria['dias_alem_do_prazo'].median())} dias além do prazo legal", alerta=True)
with p[4]:
    painel(f"Entrada no 156 · {MESES[int(ultimo['mes']) - 1]}/{int(ultimo['ano']) % 100}", num(ultimo["n"]),
           f"{'+' if variacao >= 0 else ''}{metricas.porcentagem(variacao)} sobre a média de 12 meses",
           alerta=variacao > 10)

st.write("")

# --- Mapa do atraso e fila do dia ----------------------------------------------------------------------
c1, c2 = st.columns([1, 1.25], gap="large")
with c1:
    st.markdown("**Onde o Estoque Atrasado Está** · pedidos do 156 abertos além do prazo típico")
    por_bairro = estoque.groupby("bairro_oficial")[["abertos", "acima_prazo_tipico"]].sum().reset_index()
    por_bairro["nome"] = por_bairro["bairro_oficial"].map(tabela("bairros").set_index("bairro_oficial")["nome"])
    por_bairro["atraso_txt"] = por_bairro["acima_prazo_tipico"].map(num)
    mapa = alt.Chart(alt.Data(values=malha()["features"])).mark_geoshape(stroke="white", strokeWidth=0.6).transform_lookup(
        lookup="properties.bairro_oficial",
        from_=alt.LookupData(por_bairro, "bairro_oficial", ["nome", "acima_prazo_tipico", "atraso_txt"]),
    ).encode(
        color=alt.condition("isValid(datum.acima_prazo_tipico)", alt.Color(
            "acima_prazo_tipico:Q", title="pedidos atrasados", scale=alt.Scale(range=RAMPA, type="sqrt"),
            legend=alt.Legend(orient="bottom", direction="horizontal", gradientLength=240, tickCount=4,
                              labelExpr=formato_br(), labelOverlap=True)),
            alt.value(SEM_DADO)),
        tooltip=[alt.Tooltip("nome:N", title="Bairro"), alt.Tooltip("atraso_txt:N", title="Abertos além do prazo")],
    ).project(type="mercator").properties(height=470)
    st.altair_chart(mapa, width="stretch")

with c2:
    st.markdown(f"**Fila do Dia** · os 12 pedidos abertos de maior nota (de {num(len(fila))})")
    topo = fila.head(12)
    st.dataframe(pd.DataFrame({
        "Nota": topo["indice"].round(1),
        "Serviço": topo["servico"].map(nome_categoria),
        "Bairro": topo["bairro_oficial"].map(ind["nome"]),
        "Aberto há": topo["idade_dias"].map(lambda v: f"{num(v)} dias"),
        "Anteriores no local": topo["pedidos_anteriores"].map(lambda v: "—" if pd.isna(v) else num(v)),
    }), hide_index=True, width="stretch", height=460, column_config={
        "Nota": st.column_config.ProgressColumn("Nota", min_value=0, max_value=10, format="localized")})

# --- Categorias, ritmo e bairros -------------------------------------------------------------------------
c1, c2, c3 = st.columns(3, gap="large")
with c1:
    st.markdown("**Categorias com Mais Atraso** · abertos no 156")
    cat = estoque.groupby("categoria")[["abertos", "acima_prazo_tipico"]].sum().nlargest(8, "acima_prazo_tipico").reset_index()
    cat["nome"] = cat["categoria"].map(nome_categoria)
    cat["pct"] = cat["acima_prazo_tipico"] / cat["abertos"] * 100
    cat["rotulo"] = cat["acima_prazo_tipico"].map(num) + " · " + cat["pct"].map(metricas.porcentagem)
    base = alt.Chart(cat).encode(y=alt.Y("nome:N", sort="-x", title=None, axis=alt.Axis(labelLimit=150)),
                                 x=alt.X("acima_prazo_tipico:Q", axis=None, scale=alt.Scale(domain=[0, cat["acima_prazo_tipico"].max() * 1.6])))
    st.altair_chart((base.mark_bar(color=DESTAQUE) + base.mark_text(align="left", dx=4, color=TEXTO_TEMA, fontSize=11)
                     .encode(text="rotulo:N")).properties(height=280), width="stretch")
    leitura("Pedidos além do prazo típico · % dos abertos da categoria.")

with c2:
    st.markdown("**Ritmo de Entrada no 156** · pedidos por mês, 12 meses")
    serie = entrada.tail(13).copy()
    serie["mes_txt"] = serie["mes"].map(lambda m: MESES[int(m) - 1]) + "/" + (serie["ano"] % 100).astype(str)
    serie["situacao"] = ["mês completo"] * (len(serie) - 1) + ["parcial"]
    serie["n_txt"] = serie["n"].map(num)
    ordem = serie["mes_txt"].tolist()
    barras = alt.Chart(serie).mark_bar().encode(
        x=alt.X("mes_txt:N", sort=ordem, title=None, axis=alt.Axis(labelAngle=-45)),
        y=alt.Y("n:Q", axis=eixo_numero(None)),
        color=alt.Color("situacao:N", scale=alt.Scale(domain=["mês completo", "parcial"], range=[AZUL, SEM_DADO]),
                        legend=alt.Legend(orient="top", title=None)),
        tooltip=[alt.Tooltip("mes_txt:N", title="Mês"), alt.Tooltip("n_txt:N", title="Pedidos")])
    media = alt.Chart(pd.DataFrame({"m": [media12]})).mark_rule(color=DESTAQUE, strokeDash=[4, 3]).encode(y="m:Q")
    st.altair_chart((barras + media).properties(height=280), width="stretch")
    leitura(f"Linha tracejada: média dos 12 meses completos ({num(media12)}).")

with c3:
    st.markdown("**Bairros Prioritários** · índice AHP (0 a 10)")
    top = ahp.indice_prioridade(ind, pesos).head(8).reset_index()
    top["rotulo"] = top["indice"].map(lambda v: num(v, 1))
    base = alt.Chart(top).encode(y=alt.Y("nome:N", sort="-x", title=None, axis=alt.Axis(labelLimit=150)),
                                 x=alt.X("indice:Q", axis=None, scale=alt.Scale(domain=[0, ahp.NOTA_MAXIMA * 1.15])))
    st.altair_chart((base.mark_bar(color=AZUL) + base.mark_text(align="left", dx=4, color=TEXTO_TEMA, fontSize=11)
                     .encode(text="rotulo:N")).properties(height=280), width="stretch")
    leitura("Risco, vulnerabilidade, atraso e reincidência, com os pesos padrão.")

# --- Alertas ---------------------------------------------------------------------------------------------
st.markdown("**Alertas do Retrato**")
cronicos = tabela("locais_cronicos_156")
recente = cronicos[cronicos["ultimo_ano"] >= 2025].iloc[0]
pior_cat = cat.iloc[0]
tema_camara = camara["categoria"].value_counts()
orgao_ouv = ouvidoria["orgao"].value_counts()
alertas = [
    f"<b>{pior_cat['nome']}</b> tem {num(pior_cat['acima_prazo_tipico'])} pedidos abertos além do prazo típico, o maior "
    "estoque atrasado da cidade.",
    f"<b>{len(fila[fila['indice'] >= 9])}</b> pedidos têm nota 9 ou mais; o primeiro da fila é "
    f"{nome_categoria(fila.iloc[0]['servico']).lower()} em {ind['nome'].get(fila.iloc[0]['bairro_oficial'])}, "
    f"aberto há {num(fila.iloc[0]['idade_dias'])} dias.",
    f"Um endereço em <b>{ind['nome'].get(recente['bairro_oficial'], recente['bairro_oficial'].title())}</b> já teve "
    f"{num(recente['pedidos'])} pedidos de {nome_categoria(recente['servico']).lower()} ({recente['primeiro_ano']}–"
    f"{recente['ultimo_ano']}): ponto crônico pedindo solução definitiva.",
    f"Na Câmara, <b>{nome_categoria(tema_camara.index[0]).lower()}</b> lidera as indicações sem resposta "
    f"({num(tema_camara.iloc[0])}).",
    f"Na Ouvidoria, <b>{nome_categoria(orgao_ouv.index[0])}</b> concentra {num(orgao_ouv.iloc[0])} das "
    f"{num(len(ouvidoria))} manifestações além do prazo.",
]
st.markdown("<ul style='margin-top:0'>" + "".join(f"<li>{a}</li>" for a in alertas) + "</ul>", unsafe_allow_html=True)
