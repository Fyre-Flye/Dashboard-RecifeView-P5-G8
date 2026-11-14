"""Peças de interface repetidas em todas as páginas."""

import re
import unicodedata

import altair as alt
import streamlit as st

from src.config import AZUL, CINZA, DESTAQUE, rotulo_fonte

# Placas: borda esquerda grossa na cor do estado (azul neutro, laranja atenção); o link do rodapé fica dentro
# da moldura, com o hover contido. Vale em todas as páginas: o app.py injeta este CSS uma vez.
CSS_PLACAS = f"""<style>
div[class*="st-key-placa-"] {{border-left-width: 5px !important; padding: .8rem .9rem .7rem !important;}}
div[class*="st-key-placa-"][class*="-estica"] {{flex: 1 0 auto !important;}}
div[class*="st-key-placa-alerta"] {{border-color: {DESTAQUE}66 !important; border-left-color: {DESTAQUE} !important;}}
div[class*="st-key-placa-azul"] {{border-color: {AZUL}55 !important; border-left-color: {AZUL} !important;}}
div[class*="st-key-bloco-"] {{padding: 1.1rem 1.25rem 1rem !important; flex: 1 0 auto !important;}}
[data-testid="stLayoutWrapper"]:has(> div[class*="st-key-placa-"][class*="-estica"]),
[data-testid="stLayoutWrapper"]:has(> div[class*="st-key-bloco-"]) {{flex: 1 0 auto !important; height: auto !important;}}
</style>"""


def _chave(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-")


def placa(onde, rotulo: str, valor: str, detalhe: str = "", alerta: bool = False, ajuda: str = "",
          link: tuple[str, str, str] | None = None, chave: str | None = None, esticar: bool = False) -> None:
    """Placa de indicador, igual em todas as páginas: rótulo, número, uma linha de contexto e, se houver, o link
    para a página de detalhe no rodapé. Borda laranja = atenção. `ajuda` aparece ao passar o mouse.

    `esticar`: numa faixa de placas lado a lado, todas ficam com a altura da mais alta (Painel Geral). Fora de
    faixa fica desligado, senão a placa cresce até a altura da coluna vizinha.

    O texto vai em st.html: o st.markdown come 1rem do fim do bloco e a linha de baixo vazava a borda."""
    dica = (ajuda or "").replace("'", "&#39;")
    with onde.container(border=True, gap="xxsmall",
                        key=f"placa-{'alerta' if alerta else 'azul'}-{chave or _chave(rotulo)}{'-estica' if esticar else ''}"):
        st.html(f"<div title='{dica}' style='cursor:{'help' if dica else 'default'}'>"
                f"<div style='font-size:.8rem;opacity:.75;line-height:1.25'>{rotulo}</div>"
                f"<div style='font-size:clamp(1.5rem,2.2vw,2.1rem);font-weight:700;line-height:1.15;margin:2px 0'>{valor}</div>"
                f"<div style='font-size:.8rem;opacity:.8;line-height:1.3'>{detalhe}</div></div>")
        if link:
            st.space("stretch")
            st.page_link(link[0], label=link[1], icon=link[2], width="content")


def kpi(coluna, rotulo: str, valor: str, contexto: str | None = None, ajuda: str | None = None) -> None:
    """Cartão de indicador das páginas de detalhe: a mesma placa do Painel Geral, em azul."""
    placa(coluna, rotulo, valor, contexto or "", ajuda=ajuda or "")


def leitura(texto: str) -> None:
    """Bloco "Como ler / o que ver" abaixo de um gráfico, no mesmo formato da EDA."""
    st.markdown(f"<div style='font-size:0.9rem;color:inherit;opacity:.78'>{texto}</div>", unsafe_allow_html=True)


def fontes(codigos: list[str]) -> None:
    """Linha discreta com as fontes usadas na página e quantos registros cada uma tem."""
    st.caption("Fontes nesta página: " + " · ".join(rotulo_fonte(c) for c in codigos) + ".")


def cursor_vertical(dados, x, campo: str, dicas: list) -> alt.Chart:
    """Régua tracejada que acompanha o mouse em gráficos densos (séries no tempo, linhas com muitos pontos).

    Uma linha vertical invisível por valor de x, com a altura toda do gráfico; o mouse escolhe a mais próxima, que
    aparece tracejada e mostra a dica. Assim ninguém precisa mirar num ponto ou numa barra fina para ler o valor.
    """
    sel = alt.selection_point(fields=[campo], nearest=True, on="pointerover", clear="pointerout", empty=False)
    return alt.Chart(dados).mark_rule(strokeDash=[5, 4], color=CINZA, strokeWidth=1.3).encode(
        x=x, opacity=alt.condition(sel, alt.value(0.9), alt.value(0)), tooltip=dicas).add_params(sel)
