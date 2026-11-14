"""Chuva e Carga de Trabalho (estudo em andamento): a chuva antecipa a carga da Defesa Civil e do 156?

Prova de conceito. A chuva é da reanálise ERA5 (Open-Meteo), ponto do Recife: não é dado de estação oficial e
subestima os extremos. A estação automática do INMET no Recife (A301) não tem dado de 2022 em diante.
"""

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from src import metricas
from src.componentes import kpi, leitura
from src.config import AZUL, CINZA, DESTAQUE
from src.dados import tabela

SEMANA = "W-SUN"
DEFASAGENS = range(0, 13)
num = metricas.numero


@st.cache_data(show_spinner=False)
def semanas() -> pd.DataFrame:
    """Chuva e demanda por semana. Tira a primeira e a última semana, que podem estar incompletas."""
    chuva = pd.read_csv("data/clean/chuva_recife_era5_diaria.csv", parse_dates=["data"]).set_index("data")["mm"]
    fluxo = tabela("fluxo_diario_156")
    por_cat = fluxo.pivot_table(index="data", columns="categoria", values="entradas", aggfunc="sum").fillna(0)
    dc = tabela("entradas_diarias").query("fonte == 'DEFESA_CIVIL'").set_index("data")["n"]
    s = pd.DataFrame({
        "chuva": chuva.resample(SEMANA).sum(),
        "Defesa Civil": dc.resample(SEMANA).sum(),
        "156 · Pavimentação": por_cat["PAVIMENTACAO"].resample(SEMANA).sum(),
        "156 · Drenagem": por_cat["DRENAGEM"].resample(SEMANA).sum(),
        "156 · Arborização": por_cat["ARBORIZACAO"].resample(SEMANA).sum(),
        "156 · Limpeza urbana": por_cat["LIMPEZA URBANA"].resample(SEMANA).sum(),
    }).iloc[1:-1]
    s.loc[s.index > "2024-12-29", "Defesa Civil"] = np.nan          # a Defesa Civil não publicou 2025
    s["chuva_4sem"] = s["chuva"].rolling(4).sum()
    return s


s = semanas()
SERIES = ["Defesa Civil", "156 · Pavimentação", "156 · Drenagem", "156 · Arborização", "156 · Limpeza urbana"]
CORES = [DESTAQUE, AZUL, "#5B93FE", "#9FC0FF", CINZA]


def correlacoes() -> pd.DataFrame:
    linhas = []
    for nome in SERIES:
        for d in DEFASAGENS:
            x = s["chuva_4sem"].shift(d)
            ok = x.notna() & s[nome].notna()
            linhas.append({"serie": nome, "defasagem": d, "r": np.corrcoef(x[ok], s.loc[ok, nome])[0, 1]})
    return pd.DataFrame(linhas)


st.title("Chuva e Carga de Trabalho")
st.warning("**Estudo em andamento, não é resultado.** A chuva aqui é de reanálise (ERA5, via Open-Meteo), não de "
           "estação oficial, e subestima os temporais: em 28/05/2022 ela marca 92 mm, abaixo do que os pluviômetros "
           "registraram. O próximo passo é trocar pela série da Apac ou do Cemaden.", icon=":material/science:")
st.markdown("Recife é frágil na chuva. A pergunta: **dá para avisar a gestão antes que o trabalho chegue?** A Defesa "
            "Civil atende a emergência; o 156 recolhe o depois (buraco, drenagem, árvore). Se a carga segue a chuva "
            "com um atraso previsível, a previsão do tempo vira um aviso de carga de trabalho.")
st.caption("Filtros nesta página: nenhum. Cidade inteira, por semana, de 2022 a maio de 2026 (Defesa Civil até 2024). "
           "Chuva: ERA5, ponto do Recife; demanda: dados abertos do 156 e da Defesa Civil.")

corr = correlacoes()
pico = corr.loc[corr.groupby("serie")["r"].idxmax()].set_index("serie")
k = st.columns(4)
kpi(k[0], "Defesa Civil reage", f"{pico.loc['Defesa Civil', 'defasagem']:.0f} sem.",
    f"depois da chuva · r = {metricas.numero(pico.loc['Defesa Civil', 'r'], 2)}",
    "Semanas entre a chuva acumulada (4 semanas) e o pico de correlação com as ações da Defesa Civil.")
kpi(k[1], "Pavimentação no 156", f"{pico.loc['156 · Pavimentação', 'defasagem']:.0f} sem.",
    f"depois da chuva · r = {metricas.numero(pico.loc['156 · Pavimentação', 'r'], 2)}",
    "O buraco aparece depois: a correlação com a chuva é máxima algumas semanas mais tarde.")
kpi(k[2], "Drenagem no 156", "por semanas",
    f"r perto de {metricas.numero(pico.loc['156 · Drenagem', 'r'], 1)} de 0 a 8 semanas depois",
    "A drenagem acompanha a chuva por um período longo, sem um pico claro.")
kpi(k[3], "Limpeza urbana", "não reage",
    f"r máx. = {metricas.numero(pico.loc['156 · Limpeza urbana', 'r'], 2)} · serve de controle",
    "Uma categoria grande que não acompanha a chuva: mostra que o efeito não é só 'mais gente ligando'.")

st.space("small")
c1, c2 = st.columns([1.35, 1], gap="medium")
with c1:
    st.subheader("A Chuva e o Trabalho Semana a Semana",
                 help="Barras: chuva da semana (mm, ERA5). Linhas: pedidos por semana, em índice (média do período = 100).")
    base = s.reset_index().rename(columns={"data": "semana"})
    barras = alt.Chart(base).mark_bar(color="#9FC0FF", opacity=.9).encode(
        x=alt.X("semana:T", title=None, axis=alt.Axis(format="%Y", tickCount="year")), y=alt.Y("chuva:Q", title="chuva (mm/semana)"),
        tooltip=[alt.Tooltip("semana:T", title="Semana", format="%d/%m/%Y"), alt.Tooltip("chuva:Q", title="mm", format=".0f")]
    ).properties(height=120)
    escolha = st.segmented_control("Série", ["Defesa Civil", "156 · Pavimentação", "156 · Drenagem", "156 · Limpeza urbana"],
                                   default="Defesa Civil", label_visibility="collapsed")
    linha = base[["semana", escolha]].dropna().assign(indice=lambda d: d[escolha] / d[escolha].mean() * 100)
    cor = DESTAQUE if escolha == "Defesa Civil" else (CINZA if "Limpeza" in escolha else AZUL)
    linhas = alt.Chart(linha).mark_line(color=cor, strokeWidth=1.6).encode(
        x=alt.X("semana:T", title=None, axis=alt.Axis(format="%Y", tickCount="year")),
        y=alt.Y("indice:Q", title="pedidos (média = 100)"),
        tooltip=[alt.Tooltip("semana:T", title="Semana", format="%d/%m/%Y"),
                 alt.Tooltip(f"{escolha}:Q", title="Pedidos", format=",.0f")]).properties(height=200)
    maio = alt.Chart(pd.DataFrame({"ini": [pd.Timestamp("2022-05-25")], "fim": [pd.Timestamp("2022-06-05")]})).mark_rect(
        color=DESTAQUE, opacity=.12).encode(x="ini:T", x2="fim:T")
    st.altair_chart(alt.vconcat(barras + maio, linhas + maio, spacing=4).resolve_scale(x="shared"), width="stretch")
    leitura("Faixa laranja: as chuvas de 25 a 28/05/2022. A Defesa Civil sobe junto com a chuva; a pavimentação no "
            "156 sobe nas semanas seguintes. Limpeza urbana segue outro ritmo (mais alta na época seca).")
with c2:
    st.subheader("Quanto Tempo Depois",
                 help="Correlação entre a chuva acumulada em 4 semanas e os pedidos, com a chuva deslocada de 0 a 12 semanas.")
    st.altair_chart(alt.Chart(corr).mark_line(point=True).encode(
        x=alt.X("defasagem:O", title="semanas depois da chuva", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("r:Q", title="correlação com a chuva", scale=alt.Scale(domain=[-0.4, 0.7])),
        color=alt.Color("serie:N", title=None, scale=alt.Scale(domain=SERIES, range=CORES),
                        legend=alt.Legend(orient="bottom", columns=2)),
        tooltip=[alt.Tooltip("serie:N", title="Série"), alt.Tooltip("defasagem:O", title="Semanas depois"),
                 alt.Tooltip("r:Q", title="Correlação", format=".2f")]).properties(height=330), width="stretch")
    leitura("Cada linha mostra quando a demanda mais acompanha a chuva. A Defesa Civil reage na mesma semana; "
            "a pavimentação, semanas depois. Boa parte disso é a estação do ano: tirando o calendário, a "
            "correlação cai para cerca de 0,2 na Defesa Civil e na pavimentação.")

st.space("small")
st.subheader("Como Seria o Aviso",
             help="Regressão simples, só para ilustrar: pedidos de pavimentação por semana em função da chuva "
                  "acumulada 4 semanas antes. Não é previsão validada.")
ok = s["chuva_4sem"].shift(4).notna()
b, a = np.polyfit(s["chuva_4sem"].shift(4)[ok], s.loc[ok, "156 · Pavimentação"], 1)
okd = s["chuva_4sem"].notna() & s["Defesa Civil"].notna()
bd, ad = np.polyfit(s.loc[okd, "chuva_4sem"], s.loc[okd, "Defesa Civil"], 1)
c3, c4 = st.columns([1, 1.6], gap="medium")
with c3:
    mm = st.slider("Chuva prevista para as próximas 4 semanas (mm)", 0, 400, 200, 10)
with c4:
    pav, dcv = a + b * mm, ad + bd * mm
    st.html(f"<div style='font-size:1.05rem;line-height:1.6'>Com <b>{mm} mm</b> previstos para o mês:<br>"
            f"• <b>Defesa Civil</b>, nas mesmas semanas: cerca de <b>{num(dcv)}</b> ações por semana "
            f"(média do período: {num(s['Defesa Civil'].mean())}).<br>"
            f"• <b>156 · Pavimentação</b>, umas 4 semanas depois: cerca de <b>{num(pav)}</b> pedidos por semana "
            f"(média: {num(s['156 · Pavimentação'].mean())}).</div>")
leitura("É o formato do aviso, não o número final: o modelo usa só a chuva e ainda mistura o efeito da estação. Com "
        "a série oficial e a previsão da Apac, o aviso viraria \"espere mais trabalho de pavimentação a partir de tal "
        "semana\".")
