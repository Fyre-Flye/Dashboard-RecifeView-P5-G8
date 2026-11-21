import pandas as pd
import pytest

from src import tendencia


def _demanda(linhas):
    return pd.DataFrame(linhas, columns=["fonte", "ano", "bairro_oficial", "n"])


def test_bairro_que_acompanha_a_cidade_tem_tendencia_zero_mesmo_com_a_cidade_crescendo():
    # A cidade dobra de 2021 a 2023; os dois bairros dobram junto: nenhum piorou em relação à cidade.
    d = _demanda([("156", a, b, n * k) for a, k in [(2021, 1), (2022, 1.5), (2023, 2)] for b, n in [("A", 10), ("B", 30)]])
    t = tendencia.tendencia_relativa(tendencia.parcela_anual(d, "156", (2021, 2023)))
    assert t["A"] == pytest.approx(0) and t["B"] == pytest.approx(0)


def test_bairro_que_ganha_fatia_tem_tendencia_positiva_e_o_outro_negativa():
    d = _demanda([("156", 2021, "A", 10), ("156", 2021, "B", 90),
                  ("156", 2022, "A", 20), ("156", 2022, "B", 80),
                  ("156", 2023, "A", 30), ("156", 2023, "B", 70)])
    t = tendencia.tendencia_relativa(tendencia.parcela_anual(d, "156", (2021, 2023)))
    assert t["A"] == pytest.approx(0.10 / 0.20)      # parcela sobe 0,10 por ano sobre média de 0,20
    assert t["B"] < 0


def test_ano_sem_pedido_conta_como_zero_e_outra_fonte_fica_de_fora():
    d = _demanda([("156", 2021, "A", 10), ("156", 2023, "A", 10), ("156", 2021, "B", 10), ("156", 2022, "B", 10),
                  ("156", 2023, "B", 10), ("OUTRA", 2022, "A", 999)])
    p = tendencia.parcela_anual(d, "156", (2021, 2023))
    assert p.loc["A", 2022] == 0
    assert p.sum(axis=0).tolist() == pytest.approx([1, 1, 1])
