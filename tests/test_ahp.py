import numpy as np
import pandas as pd
import pytest

from src import ahp

CHAVES = [c.chave for c in ahp.CRITERIOS]


def test_matriz_e_reciproca():
    m = ahp.matriz_de_comparacao({("a", "b"): 3, ("a", "c"): 5, ("b", "c"): 2}, ["a", "b", "c"])
    assert m[0, 1] == 3 and m[1, 0] == pytest.approx(1 / 3)
    assert np.allclose(np.diag(m), 1)
    assert np.allclose(m * m.T, 1)


def test_matriz_perfeitamente_consistente_recupera_os_pesos():
    w = np.array([0.5, 0.3, 0.2])
    m = w[:, None] / w[None, :]       # a[i, j] = w_i / w_j
    assert ahp.pesos(m) == pytest.approx(w)
    assert ahp.razao_consistencia(m) == pytest.approx(0, abs=1e-9)


def test_julgamentos_contraditorios_passam_do_limite_de_consistencia():
    # a > b, b > c, mas c > a: incoerente
    m = ahp.matriz_de_comparacao({("a", "b"): 5, ("b", "c"): 5, ("a", "c"): 1 / 5}, ["a", "b", "c"])
    assert ahp.razao_consistencia(m) > ahp.RC_ACEITAVEL


def test_julgamentos_padrao_sao_consistentes_e_somam_um():
    m = ahp.matriz_de_comparacao(ahp.JULGAMENTOS_PADRAO, CHAVES)
    w = ahp.pesos(m)
    assert w.sum() == pytest.approx(1)
    assert ahp.razao_consistencia(m) <= ahp.RC_ACEITAVEL
    assert w[0] == w.max()            # risco é o critério de maior peso na proposta inicial


def _indicadores():
    return pd.DataFrame({
        "taxa_defesa_civil": [100.0, 1.0, 50.0, 2.0],
        "pct_favela": [80.0, 0.0, 40.0, 5.0],
        "pct_atraso_156": [60.0, 50.0, 55.0, np.nan],
        "pct_reincidencia_156": [40.0, 50.0, 45.0, 30.0],
    }, index=["MORRO", "CENTRO", "MEIO", "SEM_ESTOQUE"])


def test_indice_ordena_e_soma_as_contribuicoes():
    w = dict(zip(CHAVES, [0.4, 0.3, 0.2, 0.1]))
    r = ahp.indice_prioridade(_indicadores(), w)
    assert r.index[0] == "MORRO"
    contrib = r[[f"contrib_{c}" for c in CHAVES]].sum(axis=1)
    assert np.allclose(contrib, r["indice"])
    assert r["indice"].between(0, 100).all()
    assert r.loc["SEM_ESTOQUE", "contrib_atraso"] == 0     # sem dado no critério = nota 0


def test_sensibilidade_sem_mudanca_mantem_todo_o_top():
    w = dict(zip(CHAVES, [0.4, 0.3, 0.2, 0.1]))
    s = ahp.sensibilidade(_indicadores(), w, top=2, fatores=(1.0,))
    assert (s["mantidos_no_top"] == 2).all()
    assert len(s) == len(CHAVES)
