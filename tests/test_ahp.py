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
    assert r["indice"].between(0, ahp.NOTA_MAXIMA).all()
    assert r.loc["SEM_ESTOQUE", "contrib_atraso"] == 0     # sem dado no critério = nota 0


def test_sensibilidade_sem_mudanca_mantem_todo_o_top():
    w = dict(zip(CHAVES, [0.4, 0.3, 0.2, 0.1]))
    s = ahp.sensibilidade(_indicadores(), w, top=2, fatores=(1.0,))
    assert (s["mantidos_no_top"] == 2).all()
    assert len(s) == len(CHAVES)


def _ocorrencias(**colunas):
    base = {"bairro_oficial": ["A", "A", "B"], "idade_dias": [10, 40, 10], "prazo_tipico_dias": [20.0, 20.0, 20.0],
            "pedidos_anteriores": [0, 0, 0]}
    base.update(colunas)
    return pd.DataFrame(base).astype({"pedidos_anteriores": "Int64"})


def _indicadores_dois_bairros():
    return pd.DataFrame({"taxa_defesa_civil": [1.0, 5.0], "pct_favela": [10.0, 50.0], "pct_atraso_156": [20.0, 40.0],
                         "pct_reincidencia_156": [30.0, 50.0]}, index=pd.Index(["A", "B"], name="bairro_oficial"))


def test_nota_de_atraso_e_meia_no_prazo_tipico_e_cheia_no_dobro():
    notas = ahp.notas_ocorrencias(_ocorrencias(idade_dias=[20, 40, 999]), _indicadores_dois_bairros())
    assert notas["atraso"].tolist() == [0.5, 1.0, 1.0]


def test_reincidencia_sem_numero_no_endereco_vale_zero_e_tem_teto():
    anteriores = pd.array([pd.NA, 1, 50], dtype="Int64")
    notas = ahp.notas_ocorrencias(_ocorrencias(pedidos_anteriores=anteriores), _indicadores_dois_bairros())
    assert notas.loc[0, "reincidencia"] == 0
    assert 0 < notas.loc[1, "reincidencia"] < 1
    assert notas.loc[2, "reincidencia"] == 1


def test_pedido_herda_risco_e_vulnerabilidade_do_bairro():
    notas = ahp.notas_ocorrencias(_ocorrencias(), _indicadores_dois_bairros())
    assert notas.loc[0, "risco"] == notas.loc[1, "risco"] < notas.loc[2, "risco"]


def test_indice_de_ocorrencias_vai_de_0_a_10_e_ignora_bairro_fora_do_indice():
    w = {"risco": 0.4, "vulnerabilidade": 0.3, "atraso": 0.2, "reincidencia": 0.1}
    oc = _ocorrencias(bairro_oficial=["A", "A", "FORA"])
    r = ahp.indice_ocorrencias(oc, _indicadores_dois_bairros(), w)
    assert set(r["bairro_oficial"]) == {"A"}
    assert r["indice"].between(0, ahp.NOTA_MAXIMA).all()
    assert r.iloc[0]["idade_dias"] == 40           # mesmo bairro: o mais atrasado vem primeiro
    soma = r[[f"contrib_{c.chave}" for c in ahp.CRITERIOS]].sum(axis=1)
    assert np.allclose(soma, r["indice"])


def test_indice_so_atraso_ordena_pelo_atraso_e_zera_os_outros_criterios():
    r = ahp.indice_so_atraso(pd.DataFrame({"dias_alem_do_prazo": [10, 500, 100]}))
    assert r["dias_alem_do_prazo"].tolist() == [500, 100, 10]
    assert r["indice"].iloc[0] == ahp.NOTA_MAXIMA
    assert (r["contrib_risco"] == 0).all() and r["nota_risco"].isna().all()
    assert np.allclose(r["indice"], r["contrib_atraso"])
