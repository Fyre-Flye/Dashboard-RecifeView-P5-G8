import numpy as np
import pandas as pd

from pipeline import correcoes


def test_normalizar_tira_acento_caixa_e_espacos():
    assert correcoes.normalizar("  Várzea   do  Capibaribe ") == "VARZEA DO CAPIBARIBE"


def test_anular_prazos_negativos_marca_e_anula_so_os_negativos():
    df = pd.DataFrame({"dias_ate_movimento": [5, -3, 0, np.nan]})
    corrigido, n = correcoes.anular_prazos_negativos(df)
    assert n == 1
    assert corrigido["prazo_negativo"].tolist() == [False, True, False, False]
    assert corrigido["dias_ate_movimento"].isna().tolist() == [False, True, False, True]
    assert df["dias_ate_movimento"].iloc[1] == -3  # não altera o original


def test_unificar_categorias_156_nao_mexe_em_outras_fontes():
    df = pd.DataFrame({
        "fonte": ["156_EMLURB", "156_EMLURB", "CAMARA_REQUERIMENTOS"],
        "categoria": ["TERRAPLANAGEN", "DRENAGEM", "TERRAPLANAGEM"],
    })
    corrigido, n = correcoes.unificar_categorias_156(df)
    assert n == 1
    assert corrigido["categoria"].tolist() == ["TERRAPLENAGEM", "DRENAGEM", "TERRAPLANAGEM"]


def test_harmonizar_orgaos_ouvidoria():
    df = pd.DataFrame({
        "fonte": ["OUVIDORIA", "OUVIDORIA", "156_EMLURB"],
        "orgao": ["AUTARQUIA DE URBANIZACAO DO RECIFE-URB", "URB", "AUTARQUIA DE URBANIZACAO DO RECIFE-URB"],
    })
    corrigido, n = correcoes.harmonizar_orgaos_ouvidoria(df)
    assert n == 1
    assert corrigido["orgao"].tolist() == ["URB", "URB", "AUTARQUIA DE URBANIZACAO DO RECIFE-URB"]


def _camara(textos, bairros):
    n = len(textos)
    return pd.DataFrame({"fonte": ["CAMARA_REQUERIMENTOS"] * n, "texto": textos, "bairro_oficial": bairros})


def test_recuperar_bairro_camara_so_aceita_nome_depois_de_bairro_ou_comunidade():
    df = pd.concat([
        _camara(
            ["Indica a pavimentação da rua X, no bairro da Várzea.",
             "Indica limpeza na Rua Zumbi dos Palmares.",          # nome solto: não recupera
             "Indica poda na comunidade do Sítio dos Pintos.",     # apelido -> bairro oficial
             "Indica drenagem no bairro de Afogados."],            # já tinha bairro: não mexe
            [None, None, None, "AFOGADOS"]),
        pd.DataFrame({"fonte": ["156_EMLURB"], "texto": [None], "bairro_oficial": ["ZUMBI"]}),
        pd.DataFrame({"fonte": ["156_EMLURB"] * 2, "texto": [None, None],
                      "bairro_oficial": ["VARZEA", "SITIO DOS PINTOS - SAO BRAS"]}),
    ], ignore_index=True)

    corrigido, n = correcoes.recuperar_bairro_camara(df)

    assert n == 2
    assert corrigido.loc[0, "bairro_oficial"] == "VARZEA"
    assert pd.isna(corrigido.loc[1, "bairro_oficial"])
    assert corrigido.loc[2, "bairro_oficial"] == "SITIO DOS PINTOS - SAO BRAS"
    assert corrigido.loc[3, "bairro_oficial"] == "AFOGADOS"
    assert corrigido["bairro_recuperado"].tolist() == [True, False, True, False, False, False, False]


def test_completar_territorio_leva_rpa_e_populacao_ao_bairro_recuperado():
    df = pd.DataFrame({
        "bairro_oficial": ["VARZEA", "VARZEA", "IBURA"],
        "rpa": ["4", None, "Não informada"],
        "bairro_populacao_2022": [70000.0, np.nan, np.nan],
        "bairro_pct_pop_favela_2022": [30.0, np.nan, np.nan],
    })
    completo = correcoes.completar_territorio(df)
    assert completo.loc[1, "rpa"] == "4"
    assert completo.loc[1, "bairro_populacao_2022"] == 70000
    assert pd.isna(completo.loc[2, "rpa"])  # "Não informada" vira vazio e não há outra fonte


def test_marcar_fechado_no_dia():
    df = pd.DataFrame({"dias_ate_movimento": [0, 3, np.nan]})
    corrigido, n = correcoes.marcar_fechado_no_dia(df)
    assert n == 1
    assert corrigido["fechado_no_dia"].tolist() == [True, False, False]
