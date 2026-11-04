"""War Room: protótipo de tela de sala de operações, para bater o olho.

Junta o que as outras páginas detalham num só quadro: o estoque aberto, a fila por nota, o que não voltou,
onde o atraso se concentra e o ritmo de entrada. Usa o último retrato das bases (não é tempo real) e a
cidade inteira, com os pesos padrão do AHP.
"""

import random
import time

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

# --- Simulação: uma semana em tempo acelerado ---------------------------------------------------------
SEGUNDOS_POR_DIA = 7
DIAS_SIMULADOS = 7
DIAS_SEMANA = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
MESES_LONGOS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
                "novembro", "dezembro"]
OUTRAS_PORTAS = {"CAMARA_REQUERIMENTOS": "Câmara", "OUVIDORIA": "Ouvidoria", "DEFESA_CIVIL": "Defesa Civil"}
fluxo = tabela("fluxo_diario_156")
por_dia = fluxo.groupby("data")[["entradas", "atendidos"]].sum()
entradas_fontes = tabela("entradas_diarias").pivot_table(index="data", columns="fonte", values="n", fill_value=0)


def iniciar_simulacao() -> None:
    dias = por_dia.index[:-DIAS_SIMULADOS]
    st.session_state["sim_inicio"] = pd.Timestamp(random.choice(list(dias)))
    st.session_state["sim_dia"] = 0
    st.session_state["sim_ultimo_passo"] = time.time()
    st.session_state["sim_rodando"] = True


def parar_simulacao() -> None:
    st.session_state["sim_rodando"] = False


def data_longa(d: pd.Timestamp) -> str:
    return f"{DIAS_SEMANA[d.weekday()].capitalize()}, {d.day} de {MESES_LONGOS[d.month - 1]} de {d.year}"


def quadro_simulacao() -> None:
    estado = st.session_state
    if estado.get("sim_rodando") and time.time() - estado.get("sim_ultimo_passo", 0) >= SEGUNDOS_POR_DIA - 0.5:
        if estado["sim_dia"] < DIAS_SIMULADOS - 1:
            estado["sim_dia"] += 1
            estado["sim_ultimo_passo"] = time.time()
        else:
            estado["sim_rodando"] = False
            st.rerun()                                   # para o relógio da página
    inicio, dia = pd.Timestamp(estado["sim_inicio"]), int(estado["sim_dia"])
    hoje = inicio + pd.to_timedelta(dia, unit="D")
    semana = por_dia.loc[inicio:inicio + pd.to_timedelta(DIAS_SIMULADOS - 1, unit="D")].copy()
    hoje_156 = por_dia.loc[hoje] if hoje in por_dia.index else pd.Series({"entradas": 0, "atendidos": 0})
    media_dia = por_dia[por_dia.index.weekday == hoje.weekday()]["entradas"].mean()

    situacao = "em andamento" if estado.get("sim_rodando") else "encerrada"
    st.markdown(f"<div style='font-size:1.9rem;font-weight:700;line-height:1.2'>{data_longa(hoje)}</div>"
                f"<div style='opacity:.75'>Dia {dia + 1} de {DIAS_SIMULADOS} da simulação ({situacao}) · semana de "
                f"{inicio:%d/%m/%Y} a {inicio + pd.to_timedelta(DIAS_SIMULADOS - 1, unit='D'):%d/%m/%Y}</div>",
                unsafe_allow_html=True)
    st.progress((dia + 1) / DIAS_SIMULADOS)

    saldo = int(hoje_156["entradas"] - hoje_156["atendidos"])
    outras = entradas_fontes.loc[hoje] if hoje in entradas_fontes.index else pd.Series(dtype=float)
    q = st.columns(4, gap="small")
    with q[0]:
        diferenca = (hoje_156["entradas"] / media_dia - 1) * 100 if media_dia else 0
        painel("Entraram no 156 hoje", num(hoje_156["entradas"]),
               f"{'+' if diferenca >= 0 else ''}{metricas.porcentagem(diferenca)} sobre a média de "
               f"{DIAS_SEMANA[hoje.weekday()]}", alerta=diferenca > 25)
    with q[1]:
        painel("Atendidos no 156 hoje", num(hoje_156["atendidos"]), "pela data do último movimento")
    with q[2]:
        painel("Saldo do dia", f"{'+' if saldo > 0 else ''}{num(saldo)}",
               "a fila cresceu" if saldo > 0 else "a fila diminuiu", alerta=saldo > 0)
    with q[3]:
        painel("Outras portas hoje", num(sum(outras.get(c, 0) for c in OUTRAS_PORTAS)),
               " · ".join(f"{nome} {num(outras.get(c, 0))}" for c, nome in OUTRAS_PORTAS.items()))

    c1, c2, c3 = st.columns([1.3, 1, 1], gap="large")
    with c1:
        st.markdown("**A Semana até Agora** · 156, entradas e atendimentos por dia")
        semana = semana.reset_index().melt(id_vars="data", var_name="tipo", value_name="n")
        semana["dia"] = semana["data"].map(lambda d: f"{DIAS_SEMANA[d.weekday()][:3]} {d:%d/%m}")
        semana.loc[semana["data"] > hoje, "n"] = 0                     # o futuro ainda não aconteceu
        semana["tipo"] = semana["tipo"].map({"entradas": "entraram", "atendidos": "atendidos"})
        ordem = semana.drop_duplicates("data")["dia"].tolist()
        st.altair_chart(alt.Chart(semana).mark_bar().encode(
            x=alt.X("dia:N", sort=ordem, title=None, axis=alt.Axis(labelAngle=0)),
            xOffset=alt.XOffset("tipo:N", sort=["entraram", "atendidos"]),
            y=alt.Y("n:Q", axis=eixo_numero(None)),
            color=alt.Color("tipo:N", scale=alt.Scale(domain=["entraram", "atendidos"], range=[AZUL, DESTAQUE]),
                            legend=alt.Legend(orient="top", title=None)),
            tooltip=[alt.Tooltip("dia:N", title="Dia"), alt.Tooltip("tipo:N", title=" "), alt.Tooltip("n:Q", title="Pedidos")],
        ).properties(height=250), width="stretch")
    do_dia = fluxo[fluxo["data"] == hoje]
    with c2:
        st.markdown("**O que Mais Entrou Hoje** · categorias")
        cats = do_dia.groupby("categoria")["entradas"].sum().nlargest(6)
        st.dataframe(pd.DataFrame({"Categoria": cats.index.map(nome_categoria), "Pedidos": cats.map(num).values}),
                     hide_index=True, width="stretch")
    with c3:
        st.markdown("**Onde Mais Entrou Hoje** · bairros")
        bairros_dia = do_dia.groupby("bairro_oficial")["entradas"].sum().nlargest(6)
        nomes = tabela("bairros").set_index("bairro_oficial")["nome"]
        st.dataframe(pd.DataFrame({"Bairro": bairros_dia.index.map(lambda b: nomes.get(b, b)),
                                   "Pedidos": bairros_dia.map(num).values}), hide_index=True, width="stretch")


st.subheader("Simulação: Uma Semana em Tempo Acelerado")
st.caption(f"Sorteia um dia real entre {por_dia.index.min():%d/%m/%Y} e {por_dia.index.max():%d/%m/%Y} e avança "
           f"um dia a cada {SEGUNDOS_POR_DIA} segundos, por {DIAS_SIMULADOS} dias, com o que de fato entrou e foi "
           "atendido em cada um. As bases só têm a data, sem horário, por isso a simulação anda de dia em dia.")
b1, b2, _ = st.columns([1.4, 0.8, 3])
b1.button("Iniciar Simulação com Dia Aleatório", icon=":material/play_arrow:", on_click=iniciar_simulacao,
          type="primary", width="stretch")
b2.button("Parar", icon=":material/stop:", on_click=parar_simulacao, width="stretch",
          disabled=not st.session_state.get("sim_rodando"))
if "sim_inicio" in st.session_state:
    with st.container(border=True):
        intervalo = SEGUNDOS_POR_DIA if st.session_state.get("sim_rodando") else None
        st.fragment(quadro_simulacao, run_every=intervalo)()
st.divider()
st.subheader(f"Retrato de {data_ref:%d/%m/%Y}")

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
