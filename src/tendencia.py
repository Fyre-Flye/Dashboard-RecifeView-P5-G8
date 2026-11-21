"""Tendência da demanda de cada bairro em relação à cidade (prévia de critério, sugestão da Profª Maíra, 17/11).

A demanda cresce na cidade inteira também porque ficou mais fácil pedir (aplicativo, 156). Para não confundir isso
com piora do bairro, a tendência é medida na **parcela do bairro no total da cidade**, ano a ano:

    parcela(b, t) = pedidos do bairro b no ano t ÷ pedidos da cidade no ano t
    tendência(b)  = inclinação da reta de parcela(b, t) ao longo dos anos ÷ parcela média de b

O resultado é a variação relativa por ano: +0,10 = a fatia do bairro na cidade cresce 10% ao ano; 0 = acompanha a
cidade; negativo = cresce menos que a cidade (ou cai).
"""

import numpy as np
import pandas as pd


def parcela_anual(demanda: pd.DataFrame, fonte: str, anos: tuple[int, int]) -> pd.DataFrame:
    """Parcela de cada bairro no total da cidade, por ano (linhas: bairros; colunas: anos)."""
    a0, a1 = anos
    d = demanda[(demanda["fonte"] == fonte) & demanda["ano"].between(a0, a1) & demanda["bairro_oficial"].notna()]
    n = d.groupby([d["bairro_oficial"].astype(str), "ano"])["n"].sum().unstack("ano", fill_value=0)
    n = n.reindex(columns=range(a0, a1 + 1), fill_value=0)
    return n / n.sum(axis=0)


def tendencia_relativa(parcelas: pd.DataFrame) -> pd.Series:
    """Inclinação da parcela no tempo ÷ parcela média: variação relativa por ano em relação à cidade."""
    anos = np.asarray(parcelas.columns, dtype=float)
    centrado = anos - anos.mean()
    inclinacao = (parcelas.to_numpy() * centrado).sum(axis=1) / (centrado ** 2).sum()
    media = parcelas.mean(axis=1).to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        relativa = np.where(media > 0, inclinacao / media, np.nan)
    return pd.Series(relativa, index=parcelas.index, name="tendencia_relativa")
