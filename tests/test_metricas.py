import numpy as np
import pandas as pd
import pytest

from src import metricas


def test_quantil_ponderado_igual_ao_de_uma_linha_por_pedido():
    linhas = pd.Series([0, 0, 0, 2, 3, 3, 10, 40, 40, 100, 365])
    contagem = linhas.value_counts()
    for q in (0.5, 0.9):
        esperado = np.quantile(linhas, q, method="inverted_cdf")
        assert metricas.quantil_ponderado(pd.Series(contagem.index), pd.Series(contagem.values), q) == esperado


def test_quantil_ponderado_vazio_devolve_nan():
    assert np.isnan(metricas.quantil_ponderado(pd.Series([], dtype=float), pd.Series([], dtype=float), 0.5))


def test_percentis_por_grupo():
    df = pd.DataFrame({"categoria": ["A", "A", "A", "B"], "dias": [0, 2, 30, 5], "n": [2, 1, 1, 4]})
    r = metricas.percentis_por_grupo(df, ["categoria"]).set_index("categoria")
    assert r.loc["A", "pedidos"] == 4
    assert r.loc["A", "mediana"] == 0
    assert r.loc["A", "p90"] == 30
    assert r.loc["A", "pct_mesmo_dia"] == pytest.approx(50)
    assert r.loc["B", "mediana"] == 5


def test_formatacao_brasileira():
    assert metricas.numero(1234567) == "1.234.567"
    assert metricas.numero(53.25, 1) == "53,2" or metricas.numero(53.25, 1) == "53,3"
    assert metricas.porcentagem(20.5, 1) == "20,5%"
    assert metricas.dias(1) == "1 dia"
    assert metricas.dias(241) == "241 dias"
    assert metricas.numero(float("nan")) == "—"
