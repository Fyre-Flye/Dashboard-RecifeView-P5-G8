"""Peças de interface repetidas em todas as páginas."""

import streamlit as st

from src.config import rotulo_fonte


def kpi(coluna, rotulo: str, valor: str, contexto: str | None = None, ajuda: str | None = None) -> None:
    """Cartão de indicador: rótulo curto, número grande e uma linha de contexto (sem seta de variação)."""
    coluna.metric(rotulo, valor, delta=contexto, delta_color="off", delta_arrow="off", help=ajuda, border=True)


def leitura(texto: str) -> None:
    """Bloco "Como ler / o que ver" abaixo de um gráfico, no mesmo formato da EDA."""
    st.markdown(f"<div style='font-size:0.9rem;color:inherit;opacity:.78'>{texto}</div>", unsafe_allow_html=True)


def fontes(codigos: list[str]) -> None:
    """Linha discreta com as fontes usadas na página e quantos registros cada uma tem."""
    st.caption("Fontes nesta página: " + " · ".join(rotulo_fonte(c) for c in codigos) + ".")
