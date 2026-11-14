"""Simulação dos dois avisos de carga de trabalho em torno de um temporal.

Aviso 1 (antes): a previsão de chuva forte avisa a Defesa Civil e o 156 para se prepararem.
Aviso 2 (depois): a chuva medida avisa que a pavimentação vai subir semanas depois.

Cada série é mostrada como "vezes o normal": média móvel de 7 dias dividida pela mediana dessa média no ano anterior
ao temporal. Assim, chamados da Defesa Civil (dezenas por dia) e pedidos do 156 (centenas) cabem na mesma régua.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.config import AZUL, AZUL40, CINZA, DESTAQUE, FONTE, NAVY

ANTES, DEPOIS = 10, 63            # dias mostrados antes e depois do pico de chuva
JANELA_AVISO2 = (28, 49)          # 4 a 7 semanas depois: onde o estudo achou o pico da pavimentação
AMARELO = "#F2A900"


@dataclass(frozen=True)
class Evento:
    pico: str                     # dia de mais chuva
    nome: str
    avisos: tuple = field(default_factory=tuple)   # (dias antes do pico, texto) dos avisos reais; vazio = simulado


EVENTOS = [
    Evento("2022-05-28", "Maio de 2022 · a catástrofe", (
        (-5, "23/05 · Apac: alerta laranja de chuva"),
        (-3, "25/05 · Cemaden: risco alto de deslizamento"),
        (-2, "26/05 · Inmet: 150 a 200 mm por dia no fim de semana"),
        (-1, "27/05 · Prefeitura aciona o plano, só na véspera"),
    )),
    Evento("2023-05-24", "Maio de 2023"),
    Evento("2024-06-15", "Junho de 2024"),
    Evento("2025-05-14", "Maio de 2025"),
]

SERIES = {  # coluna: (rótulo, cor, linha do gráfico)
    "sedec": ("Defesa Civil · chamados", DESTAQUE, 2),
    "acoes": ("Defesa Civil · ações em campo", "#F4A26B", 2),
    "imediato": ("156 · drenagem e árvores", AZUL, 3),
    "pav": ("156 · pavimentação", NAVY, 3),
}


def series_diarias(fluxo: pd.DataFrame, entradas: pd.DataFrame, chuva: pd.Series) -> pd.DataFrame:
    por_cat = fluxo.pivot_table(index="data", columns="categoria", values="entradas", aggfunc="sum")
    dias = pd.date_range(por_cat.index.min(), por_cat.index.max(), freq="D")
    por_cat = por_cat.reindex(dias).fillna(0)
    fonte = lambda f: entradas.query("fonte == @f").set_index("data")["n"].reindex(dias)  # noqa: E731
    return pd.DataFrame({
        "chuva": chuva.reindex(dias),
        "sedec": fonte("SEDEC_CHAMADOS"),
        "acoes": fonte("DEFESA_CIVIL"),
        "imediato": por_cat["DRENAGEM"] + por_cat["ARBORIZACAO"],
        "pav": por_cat["PAVIMENTACAO"],
    }, index=dias)


def recorte(d: pd.DataFrame, ev: Evento) -> pd.DataFrame:
    """Dias de -ANTES a +DEPOIS em torno do pico, cada série em "vezes o normal"."""
    t = pd.Timestamp(ev.pico)
    media7 = d.drop(columns="chuva").rolling(7, min_periods=5).mean()
    normal = media7.loc[t - pd.Timedelta(days=365): t - pd.Timedelta(days=8)].median()
    janela = media7.loc[t - pd.Timedelta(days=ANTES): t + pd.Timedelta(days=DEPOIS)] / normal
    janela.loc[:, normal.isna() | (janela.notna().sum() == 0)] = np.nan
    janela["chuva"] = d["chuva"].reindex(janela.index)
    janela["dia"] = (janela.index - t).days
    return janela


def _picos(r: pd.DataFrame) -> dict:
    out = {}
    for c in SERIES:
        s = r.loc[r["dia"] >= 0, c].dropna()
        if len(s):
            out[c] = (float(s.max()), int(r.loc[s.idxmax(), "dia"]))
    return out


def _fase(dia: int, ev: Evento, r: pd.DataFrame, p: dict) -> str:
    mm = r.loc[r["dia"] == 0, "chuva"].iloc[0]
    if dia < 0:
        reais = [txt for d, txt in ev.avisos if d <= dia]
        if reais:
            return "<b>AVISO 1 · a chuva estava prevista</b><br>" + reais[-1]
        if not ev.avisos and dia >= -3:
            return ("<b>AVISO 1 (simulado) · previsão de chuva forte</b><br>"
                    "Defesa Civil e 156: reforcem plantão e equipes")
        return "Dias normais"
    if dia <= 3:
        txt = f"<b>Chuva: {mm:.0f} mm no dia</b>".replace(".", ",")
        if "sedec" in p:
            txt += f"<br>Chamados da Defesa Civil chegam a {p['sedec'][0]:.0f}× o normal".replace(".", ",")
        return txt
    if dia <= 21:
        v, d = p.get("imediato", (np.nan, 0))
        return ("<b>AVISO 2 · choveu forte: a pavimentação vai subir em 4 a 7 semanas</b><br>"
                f"Agora, o 156 recebe drenagem e árvores (até {v:.1f}× o normal)").replace(".", ",")
    v, d = p.get("pav", (np.nan, 0))
    return (f"<b>A segunda onda chega</b><br>Pavimentação no 156: {v:.1f}× o normal, "
            f"{d // 7} semanas depois da chuva").replace(".", ",")


def figura(d: pd.DataFrame, ev: Evento, escuro: bool = False) -> go.Figure:
    r = recorte(d, ev)
    p = _picos(r)
    texto = "#E6E6E6" if escuro else "#262730"
    grade = "rgba(140,140,140,.18)"
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06, row_heights=[0.26, 0.37, 0.37],
                        subplot_titles=("Chuva (mm por dia, estações do Cemaden)",
                                        "Defesa Civil (vezes o normal)", "156 (vezes o normal)"))
    teto = {2: max(2.5, np.nanmax([p.get(c, (0,))[0] for c in ("sedec", "acoes")]) * 1.12),
            3: max(2.5, np.nanmax([p.get(c, (0,))[0] for c in ("imediato", "pav")]) * 1.12)}

    def tracos(ate: int) -> list:
        v = r[r["dia"] <= ate]
        tr = [go.Bar(x=v["dia"], y=v["chuva"], marker_color=AZUL40, name="Chuva", showlegend=False,
                     hovertemplate="dia %{x}: %{y:.0f} mm<extra></extra>")]
        for c, (rot, cor, _) in SERIES.items():
            tr.append(go.Scatter(x=v["dia"], y=v[c], mode="lines", line=dict(color=cor, width=3), name=rot,
                                 hovertemplate=f"{rot}<br>dia %{{x}}: %{{y:.1f}}× o normal<extra></extra>"))
        return tr

    def enfeites(ate: int) -> dict:
        formas = [dict(type="line", xref="x", yref="paper", x0=ate, x1=ate, y0=0, y1=1,
                       line=dict(color=CINZA, width=1.5, dash="dash"))]
        if ate >= -3 or any(dd <= ate for dd, _ in ev.avisos):
            ini = min([dd for dd, _ in ev.avisos] + [-3])
            formas.append(dict(type="rect", xref="x", yref="paper", x0=ini - .5, x1=-.5, y0=0, y1=1,
                               fillcolor=AMARELO, opacity=.13, line_width=0, layer="below"))
        if ate >= 1:
            formas.append(dict(type="rect", xref="x", yref="paper", x0=JANELA_AVISO2[0], x1=JANELA_AVISO2[1],
                               y0=0, y1=1, fillcolor=AZUL, opacity=.10, line_width=0, layer="below"))
        notas = [dict(text=_fase(ate, ev, r, p), x=0, y=1.25, xref="paper", yref="paper", xanchor="left", yanchor="top",
                      showarrow=False, align="left", font=dict(size=15, color=texto))]
        if ate >= 1:
            notas.append(dict(text="janela do aviso 2", x=sum(JANELA_AVISO2) / 2, y=1.0, xref="x", yref="paper",
                              showarrow=False, font=dict(size=11, color=AZUL), yanchor="bottom"))
        return dict(shapes=formas, annotations=notas)

    dias = list(range(-ANTES, DEPOIS + 1))
    for t in tracos(dias[0]):
        linha = 1 if isinstance(t, go.Bar) else SERIES[[k for k, v in SERIES.items() if v[0] == t.name][0]][2]
        fig.add_trace(t, row=linha, col=1)
    titulos = list(fig.layout.annotations)  # os títulos dos três painéis ficam em todos os quadros
    for a in titulos:
        a.font = dict(size=12, color=texto)
        a.x, a.xanchor = 0, "left"
    fig.frames = [go.Frame(name=str(t), data=tracos(t), layout=dict(
        shapes=enfeites(t)["shapes"], annotations=titulos + enfeites(t)["annotations"])) for t in dias]
    fig.update_layout(shapes=enfeites(dias[0])["shapes"], annotations=titulos + enfeites(dias[0])["annotations"])

    fig.update_xaxes(range=[-ANTES - .5, DEPOIS + .5], gridcolor=grade, zeroline=False, color=texto)
    fig.update_xaxes(title_text="dias em relação ao dia de mais chuva", row=3, col=1)
    fig.update_yaxes(gridcolor=grade, zeroline=False, color=texto)
    fig.update_yaxes(range=[0, max(60, np.nanmax(r["chuva"]) * 1.1)], row=1, col=1)
    for linha in (2, 3):
        fig.update_yaxes(range=[0, teto[linha]], row=linha, col=1)
    passo = [dict(args=[[str(t)], dict(mode="immediate", frame=dict(duration=0, redraw=True), transition=dict(duration=0))],
                  label=str(t), method="animate") for t in dias]
    fig.update_layout(
        height=680, margin=dict(l=10, r=10, t=150, b=10), font=dict(family=FONTE, color=texto),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", bargap=.15,
        legend=dict(orientation="h", y=-0.12, x=0, font=dict(size=12)), hovermode="x unified",
        updatemenus=[dict(type="buttons", direction="left", x=1, xanchor="right", y=1.27, yanchor="top", showactive=False,
                          buttons=[dict(label="▶ Rodar", method="animate", args=[None, dict(
                                        frame=dict(duration=140, redraw=True), transition=dict(duration=0),
                                        fromcurrent=True, mode="immediate")]),
                                   dict(label="❚❚ Pausar", method="animate", args=[[None], dict(
                                        frame=dict(duration=0, redraw=False), mode="immediate")])])],
        sliders=[dict(active=0, steps=passo, x=0, len=1, y=-0.2, pad=dict(t=30),
                      currentvalue=dict(prefix="dia ", font=dict(size=12, color=texto)), font=dict(color=texto))],
    )
    return fig
