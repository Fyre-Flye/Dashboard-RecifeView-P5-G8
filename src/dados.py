"""Leitura das tabelas do painel (data/clean), com cache: cada arquivo é lido uma vez por sessão do servidor."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.config import NOMES_FONTE

PASTA = Path(__file__).resolve().parents[1] / "data" / "clean"


@st.cache_data
def tabela(nome: str) -> pd.DataFrame:
    df = pd.read_parquet(PASTA / f"{nome}.parquet")
    if "fonte" in df.columns:
        df["fonte_nome"] = df["fonte"].map(NOMES_FONTE)
    return df


@st.cache_data
def malha() -> dict:
    return json.loads((PASTA / "bairros.geojson").read_text(encoding="utf-8"))


@st.cache_data
def resumo_preparacao() -> dict:
    return json.loads((PASTA / "resumo_preparacao.json").read_text(encoding="utf-8"))


@st.cache_data
def categorias_156() -> list[str]:
    """Categorias do 156 ordenadas por volume (as maiores primeiro), para o filtro."""
    d = tabela("demanda")
    vol = d[d["fonte"] == "156_EMLURB"].groupby("categoria")["n"].sum().sort_values(ascending=False)
    return [c for c in vol.index if c]
