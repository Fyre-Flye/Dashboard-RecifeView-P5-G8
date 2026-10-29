"""Cálculos e formatação usados pelas páginas (sem Streamlit, para poderem ser testados)."""

import numpy as np
import pandas as pd


def quantil_ponderado(valores: pd.Series, pesos: pd.Series, q: float) -> float:
    """Quantil de uma distribuição guardada como (valor, contagem), igual ao de uma linha por pedido.

    Usa a regra do valor mais baixo cuja frequência acumulada alcança q (a mesma da mediana de
    uma lista ordenada quando o total é ímpar).
    """
    if len(valores) == 0 or pesos.sum() == 0:
        return float("nan")
    ordem = np.argsort(valores.to_numpy(), kind="stable")
    v = valores.to_numpy()[ordem]
    acumulado = np.cumsum(pesos.to_numpy()[ordem])
    return float(v[np.searchsorted(acumulado, q * acumulado[-1])])


def percentis_por_grupo(df: pd.DataFrame, grupo: list[str], valor: str = "dias", peso: str = "n") -> pd.DataFrame:
    """Mediana, p90, total e % de prazo zero por grupo, a partir de (valor, contagem)."""
    def resumo(g: pd.DataFrame) -> pd.Series:
        total = g[peso].sum()
        return pd.Series({
            "pedidos": total,
            "mediana": quantil_ponderado(g[valor], g[peso], 0.5),
            "p90": quantil_ponderado(g[valor], g[peso], 0.9),
            "pct_mesmo_dia": g.loc[g[valor] == 0, peso].sum() / total * 100 if total else np.nan,
        })
    return df.groupby(grupo, observed=True).apply(resumo, include_groups=False).reset_index()


def numero(x: float, casas: int = 0) -> str:
    """Número no formato brasileiro: 1.234,5."""
    if x is None or pd.isna(x):
        return "—"
    texto = f"{x:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def porcentagem(x: float, casas: int = 0) -> str:
    return "—" if x is None or pd.isna(x) else f"{numero(x, casas)}%"


def dias(x: float) -> str:
    if x is None or pd.isna(x):
        return "—"
    return f"{numero(x)} dia" if round(x) == 1 else f"{numero(x)} dias"
