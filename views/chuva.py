"""Chuva e Carga de Trabalho (estudo em andamento): a chuva antecipa a carga da Defesa Civil e do 156?

Chuva: pluviômetros do Cemaden em Recife (mediana diária das estações com o dia completo), abril a agosto de
2022 a 2025 e abril a maio de 2026. Fora desses meses, a reanálise ERA5 (Open-Meteo) só aparece no gráfico, marcada:
ela acompanha o ritmo semanal, mas mede menos da metade da chuva e quase não vê os temporais.
"""

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from src import metricas
from src.componentes import cursor_vertical, kpi, leitura
from src.config import AZUL, CINZA, DESTAQUE
from src.dados import tabela

SEMANA = "W-SUN"
DEFASAGENS = range(0, 11)
TEMPORAL_DIA = 50       # mm em um dia
TEMPORAL_SEMANA = 110   # mm em uma semana (cerca do percentil 90 das semanas de abril a agosto)
num = metricas.numero

SERIES = ["Defesa Civil", "156 · Pavimentação", "156 · Drenagem", "156 · Arborização", "156 · Limpeza urbana"]
CORES = [DESTAQUE, AZUL, "#5B93FE", "#9FC0FF", CINZA]


@st.cache_data(show_spinner=False)
def chuva_diaria() -> pd.DataFrame:
    cem = pd.read_csv("data/clean/chuva_recife_cemaden_diaria.csv", parse_dates=["data"]).set_index("data")["mm"]
    era = pd.read_csv("data/clean/chuva_recife_era5_diaria.csv", parse_dates=["data"]).set_index("data")["mm"]
    return pd.concat({"cemaden": cem, "era5": era}, axis=1)


@st.cache_data(show_spinner=False)
def semanas() -> pd.DataFrame:
    """Chuva e demanda por semana. A semana do Cemaden só vale com os 7 dias medidos."""
    d = chuva_diaria()
    cem = d["cemaden"].resample(SEMANA).agg(["sum", "count"])
    fluxo = tabela("fluxo_diario_156")
    por_cat = fluxo.pivot_table(index="data", columns="categoria", values="entradas", aggfunc="sum").fillna(0)
    dc = tabela("entradas_diarias").query("fonte == 'DEFESA_CIVIL'").set_index("data")["n"]
    s = pd.DataFrame({
        "Defesa Civil": dc.resample(SEMANA).sum(),
        "156 · Pavimentação": por_cat["PAVIMENTACAO"].resample(SEMANA).sum(),
        "156 · Drenagem": por_cat["DRENAGEM"].resample(SEMANA).sum(),
        "156 · Arborização": por_cat["ARBORIZACAO"].resample(SEMANA).sum(),
        "156 · Limpeza urbana": por_cat["LIMPEZA URBANA"].resample(SEMANA).sum(),
    }).iloc[1:-1]
    s.loc[s.index > "2024-12-29", "Defesa Civil"] = np.nan          # a Defesa Civil não publicou 2025
    s["chuva"] = cem["sum"].where(cem["count"] == 7).reindex(s.index)
    s["chuva_era5"] = d["era5"].resample(SEMANA).sum().reindex(s.index)
    s["chuva_4sem"] = s["chuva"].rolling(4).sum()                    # vazia se faltar qualquer semana
    return s


def correlacoes(s: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for nome in SERIES:
        for lag in DEFASAGENS:
            x = s["chuva_4sem"].shift(lag)
            ok = x.notna() & s[nome].notna()
            if ok.sum() >= 20:
                linhas.append({"serie": nome, "defasagem": lag, "r": np.corrcoef(x[ok], s.loc[ok, nome])[0, 1],
                               "semanas": int(ok.sum())})
    return pd.DataFrame(linhas)


def temporais(s: pd.DataFrame) -> pd.Series:
    """Semanas com chuva forte; de duas semanas fortes seguidas fica a primeira."""
    ev = s["chuva"][s["chuva"] >= TEMPORAL_SEMANA]
    return ev[~(ev.index.to_series().diff() <= pd.Timedelta(days=14))]


s = semanas()
d = chuva_diaria()
corr = correlacoes(s)
pico = corr.loc[corr.groupby("serie")["r"].idxmax()].set_index("serie")
ambos = d.dropna()
razao = ambos["era5"].sum() / ambos["cemaden"].sum()
fortes_cem, fortes_era = int((ambos["cemaden"] >= TEMPORAL_DIA).sum()), int((ambos["era5"] >= TEMPORAL_DIA).sum())

st.title("Chuva e Carga de Trabalho")
st.warning("**Estudo em andamento, não é resultado.** A chuva agora vem dos pluviômetros do Cemaden em Recife, mas só "
           "de abril a agosto (2022 a 2025) e de abril e maio de 2026. A demanda é dado aberto. Poucos temporais "
           "na amostra: o padrão é indício, não previsão.", icon=":material/science:")
st.markdown("Recife é frágil na chuva. A pergunta: **dá para avisar a gestão antes que o trabalho chegue?** A Defesa "
            "Civil atende a emergência; o 156 recolhe o depois (buraco, drenagem, árvore). Se a carga segue a chuva "
            "com um atraso previsível, a previsão do tempo vira um aviso de carga de trabalho.")
st.caption("Filtros nesta página: nenhum. Cidade inteira, por semana. Chuva: mediana diária das estações do Cemaden "
           f"em Recife ({len(ambos)} dias). Demanda: 156 (2022 a maio de 2026) e Defesa Civil (até 2024).")

k = st.columns(4)
kpi(k[0], "A Reanálise Subestimava", f"{num((1 - razao) * 100)}%",
    "menos chuva na ERA5 que nas estações, nos mesmos dias",
    "A primeira versão do estudo usava a ERA5. No mesmo período, ela soma menos da metade da chuva medida.")
kpi(k[1], f"Dias com {TEMPORAL_DIA} mm ou Mais", f"{fortes_cem} × {fortes_era}",
    "nas estações × na ERA5",
    "Os temporais são o que importa para o aviso, e é onde a reanálise mais erra. Em 28/05/2022 as estações "
    "marcaram 171 mm (mediana); a ERA5, 92 mm.")
kpi(k[2], "Pavimentação no 156", f"{pico.loc['156 · Pavimentação', 'defasagem']:.0f} sem.",
    f"depois da chuva · r = {num(pico.loc['156 · Pavimentação', 'r'], 2)}",
    "Semanas entre a chuva acumulada (4 semanas) e o pico de correlação, só dentro da época de chuva.")
lag_dc = int(pico.loc["Defesa Civil", "defasagem"])
kpi(k[3], "Defesa Civil", "na hora" if lag_dc == 0 else f"{lag_dc} sem.",
    f"mesma semana · r = {num(pico.loc['Defesa Civil', 'r'], 2)}" if lag_dc == 0
    else f"depois da chuva · r = {num(pico.loc['Defesa Civil', 'r'], 2)}",
    "A Defesa Civil reage na mesma semana, mas fraco: ela já está alta em toda a época de chuva.")

st.space("small")
c1, c2 = st.columns([1.35, 1], gap="medium")
with c1:
    st.subheader("A Chuva e o Trabalho Semana a Semana",
                 help="Barras: chuva da semana. Azul = estações do Cemaden; cinza = ERA5, onde não há estação (mede "
                      "menos da metade). Linha: pedidos por semana, em índice (média do período = 100).")
    base = s.reset_index().rename(columns={"data": "semana"})
    barras_df = pd.concat([
        base[["semana", "chuva"]].dropna().rename(columns={"chuva": "mm"}).assign(fonte="Estações Cemaden"),
        base.loc[base["chuva"].isna(), ["semana", "chuva_era5"]].rename(columns={"chuva_era5": "mm"})
            .assign(fonte="ERA5 (sem estação)"),
    ])
    eixo_x = alt.X("semana:T", title=None, axis=alt.Axis(format="%Y", tickCount="year"),
                   scale=alt.Scale(domain=[base["semana"].min().isoformat(), base["semana"].max().isoformat()]))
    barras = alt.Chart(barras_df).mark_bar().encode(
        x=eixo_x, y=alt.Y("mm:Q", title="chuva (mm/semana)"),
        color=alt.Color("fonte:N", title=None, scale=alt.Scale(domain=["Estações Cemaden", "ERA5 (sem estação)"],
                                                               range=[AZUL, "#C9CED6"]),
                        legend=alt.Legend(orient="top", direction="horizontal")),
        tooltip=[alt.Tooltip("semana:T", title="Semana", format="%d/%m/%Y"), alt.Tooltip("fonte:N", title="Fonte"),
                 alt.Tooltip("mm:Q", title="mm", format=".0f")]).properties(height=140)
    escolha = st.segmented_control("Série", SERIES[:3] + SERIES[4:], default="156 · Pavimentação",
                                   format_func=lambda x: x.replace("156 · ", ""), label_visibility="collapsed")
    escolha = escolha or "156 · Pavimentação"
    linha = base[["semana", escolha]].dropna().assign(indice=lambda x: x[escolha] / x[escolha].mean() * 100)
    cor = DESTAQUE if escolha == "Defesa Civil" else (CINZA if "Limpeza" in escolha else AZUL)
    linhas = alt.Chart(linha).mark_line(color=cor, strokeWidth=1.6).encode(
        x=eixo_x, y=alt.Y("indice:Q", title="pedidos (média = 100)"),
        tooltip=[alt.Tooltip("semana:T", title="Semana", format="%d/%m/%Y"),
                 alt.Tooltip(f"{escolha}:Q", title="Pedidos", format=",.0f")]).properties(height=200)
    maio = alt.Chart(pd.DataFrame({"ini": [pd.Timestamp("2022-05-23")], "fim": [pd.Timestamp("2022-06-05")]})).mark_rect(
        color=DESTAQUE, opacity=.12).encode(x="ini:T", x2="fim:T")
    # Uma régua por semana, nos dois gráficos, com a chuva e os pedidos na mesma dica.
    dica_df = base[["semana"]].merge(barras_df, on="semana", how="left").merge(
        linha[["semana", escolha]].rename(columns={escolha: "pedidos"}), on="semana", how="left")
    dica_df["mm_txt"] = dica_df["mm"].map(lambda v: "" if pd.isna(v) else num(v))
    dica_df["pedidos_txt"] = dica_df["pedidos"].map(lambda v: "" if pd.isna(v) else num(v))
    dica = [alt.Tooltip("semana:T", title="Semana", format="%d/%m/%Y"), alt.Tooltip("mm_txt:N", title="Chuva (mm)"),
            alt.Tooltip("fonte:N", title="Fonte da chuva"), alt.Tooltip("pedidos_txt:N", title=f"{escolha} (pedidos)")]
    st.altair_chart((barras + maio + cursor_vertical(dica_df, eixo_x, "semana", dica)).properties(height=210),
                    width="stretch")
    st.altair_chart((linhas + maio + cursor_vertical(dica_df, eixo_x, "semana", dica)).properties(height=190),
                    width="stretch")
    leitura("Faixa laranja: as chuvas de maio de 2022 (506 mm numa semana, pela mediana das estações). As barras "
            "cinza são só referência: a correlação usa apenas as semanas com estação.")
with c2:
    st.subheader("Quanto Tempo Depois",
                 help="Correlação entre a chuva acumulada em 4 semanas (estações) e os pedidos, com a chuva deslocada "
                      "de 0 a 10 semanas. Só semanas de abril a agosto: a diferença entre época seca e chuvosa fica "
                      "de fora.")
    eixo_lag = alt.X("defasagem:O", title="semanas depois da chuva", axis=alt.Axis(labelAngle=0))
    corr_largo = corr.pivot(index="defasagem", columns="serie", values="r").reset_index()
    corr_largo.columns = ["defasagem"] + [f"s{i}" for i in range(len(corr_largo.columns) - 1)]
    nomes_corr = corr.pivot(index="defasagem", columns="serie", values="r").columns
    for c in corr_largo.columns[1:]:
        corr_largo[c] = corr_largo[c].map(lambda v: num(v, 2))
    dica_lag = [alt.Tooltip("defasagem:O", title="Semanas depois")] + [
        alt.Tooltip(f"s{i}:N", title=n) for i, n in enumerate(nomes_corr)]
    st.altair_chart((alt.Chart(corr).mark_line(point=True).encode(
        x=eixo_lag,
        y=alt.Y("r:Q", title="correlação", scale=alt.Scale(domain=[-0.4, 0.7])),
        color=alt.Color("serie:N", title=None, scale=alt.Scale(domain=SERIES, range=CORES),
                        legend=alt.Legend(orient="top", columns=2, labelExpr="replace(datum.label, '156 · ', '156 ')")),
        tooltip=[alt.Tooltip("serie:N", title="Série"), alt.Tooltip("defasagem:O", title="Semanas depois"),
                 alt.Tooltip("r:Q", title="Correlação", format=".2f"),
                 alt.Tooltip("semanas:Q", title="Semanas usadas")])
        + cursor_vertical(corr_largo, eixo_lag, "defasagem", dica_lag)).properties(height=430), width="stretch")
    leitura("Mesmo só dentro da época de chuva, a pavimentação e a drenagem sobem umas 5 semanas depois da chuva. "
            "A limpeza urbana, que serve de controle, não acompanha.")

st.space("small")
st.subheader("Depois de Cada Temporal",
             help=f"Semanas com {TEMPORAL_SEMANA} mm ou mais nas estações (de duas seguidas, fica a primeira). "
                  "Índice: média das 4 semanas antes do temporal = 100.")
ev = temporais(s)
rotulo = {f"{t:%d/%m/%Y} · {num(v)} mm": t for t, v in ev.items()}
c3, c4 = st.columns([1, 2.2], gap="medium")
with c3:
    qual = st.radio("Temporal", list(rotulo), index=0, label_visibility="collapsed")
    leitura("Cada temporal conta uma história diferente: em 2022 e 2025 a pavimentação sobe semanas depois; em "
            "2023, quase nada. Com tão poucos casos, ainda não dá para dizer quanto trabalho a mais esperar.")
with c4:
    t = rotulo[qual]
    janela = s.loc[t - pd.Timedelta(weeks=4): t + pd.Timedelta(weeks=8)]
    antes = s.loc[t - pd.Timedelta(weeks=4): t - pd.Timedelta(weeks=1)]
    longo = []
    for nome in ["Defesa Civil", "156 · Pavimentação", "156 · Drenagem", "156 · Limpeza urbana"]:
        if janela[nome].notna().any() and antes[nome].mean() > 0:
            longo.append(pd.DataFrame({"semanas": ((janela.index - t).days // 7), "serie": nome,
                                       "indice": janela[nome] / antes[nome].mean() * 100, "pedidos": janela[nome]}))
    longo = pd.concat(longo)
    regua = alt.Chart(pd.DataFrame({"y": [100]})).mark_rule(color=CINZA, strokeDash=[4, 3]).encode(y="y:Q")
    marco = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color=DESTAQUE, strokeWidth=2).encode(x="x:Q")
    eixo_ev = alt.X("semanas:Q", title="semanas em relação ao temporal", scale=alt.Scale(domain=[-4, 8]))
    largo = longo.pivot(index="semanas", columns="serie", values="pedidos")
    nomes_ev = list(largo.columns)
    largo = largo.reset_index()
    largo.columns = ["semanas"] + [f"s{i}" for i in range(len(nomes_ev))]
    for c in largo.columns[1:]:
        largo[c] = largo[c].map(lambda v: "" if pd.isna(v) else num(v))
    dica_ev = [alt.Tooltip("semanas:Q", title="Semanas depois do temporal")] + [
        alt.Tooltip(f"s{i}:N", title=f"{n} (pedidos)") for i, n in enumerate(nomes_ev)]
    st.altair_chart((alt.Chart(longo).mark_line(point=True).encode(
        x=eixo_ev,
        y=alt.Y("indice:Q", title="índice (antes = 100)"),
        color=alt.Color("serie:N", title=None, scale=alt.Scale(domain=SERIES, range=CORES),
                        legend=alt.Legend(orient="bottom", columns=3)),
        tooltip=[alt.Tooltip("serie:N", title="Série"), alt.Tooltip("semanas:Q", title="Semanas depois"),
                 alt.Tooltip("pedidos:Q", title="Pedidos", format=",.0f"),
                 alt.Tooltip("indice:Q", title="Índice", format=".0f")]) + regua + marco
         + cursor_vertical(largo, eixo_ev, "semanas", dica_ev)).properties(height=300),
        width="stretch")

st.space("small")
st.subheader("O Que Já Dá Para Dizer")
st.html(f"""<div style='font-size:1rem;line-height:1.65'>
<b>Dá:</b> a pavimentação e a drenagem no 156 tendem a subir 4 a 7 semanas depois de chuva forte, mesmo comparando
só semanas da época de chuva. Um aviso no formato <i>"choveu {TEMPORAL_SEMANA} mm ou mais esta semana: espere mais pedidos de
pavimentação daqui a um mês"</i> tem base.<br>
<b>Ainda não dá:</b> dizer quantos pedidos a mais. São {len(ev)} temporais na amostra, e a resposta varia muito de um
para outro. A Defesa Civil reage na mesma semana, mas fraco no dado aberto, e não publicou 2025.<br>
<b>Para avançar:</b> os meses secos (setembro a março) do Cemaden, para usar o ano inteiro; e a previsão da Apac, para
transformar o aviso de "choveu" em "vai chover".</div>""")
