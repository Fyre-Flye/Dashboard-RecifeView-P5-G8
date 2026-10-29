import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pipeline import agregados

COLUNAS_PROIBIDAS = {"texto", "id_local", "lat", "lon", "camara_autoria", "id_registro", "id", "localidade"}
CLEAN = Path(__file__).resolve().parents[1] / "data" / "clean"


def _pedido_156(id_local, data, servico="1", numero=True, situacao="ATENDIDA", dias=3, bairro="VARZEA",
                categoria="ILUMINACAO PUBLICA"):
    data = pd.Timestamp(data)
    return {"fonte": "156_EMLURB", "ano": data.year, "data_abertura": data, "id_local": id_local,
            "servico_codigo": servico, "servico": f"SERVICO {servico}", "numero_informado": str(numero),
            "situacao": situacao, "dias_ate_movimento": dias, "bairro_oficial": bairro, "rpa": "4",
            "categoria": categoria, "iniciativa": "CIDADAO", "arquivo_origem": f"156_{data.year}"}


def test_reincidencia_separa_duplicidade_de_reincidencia():
    df = pd.DataFrame([
        _pedido_156("A", "2020-01-01"),
        _pedido_156("A", "2020-01-05"),                  # 4 dias depois: duplicidade
        _pedido_156("A", "2020-03-01"),                  # 56 dias depois: reincidência
        _pedido_156("B", "2020-01-01"),                  # local único: não repete
        _pedido_156("A", "2020-01-02", servico="2"),     # mesmo local, outro serviço: chave diferente
        _pedido_156("C", "2020-01-01", numero=False),    # sem número: fora da conta
        _pedido_156("C", "2020-01-02", numero=False),
    ])
    t = agregados.reincidencia_156(df).sum(numeric_only=True)
    assert t["registros"] == 5
    assert t["repetidos"] == 3
    assert t["intervalo_duplicidade"] == 1
    assert t["intervalo_reincidencia"] == 1
    assert t["intervalo_intermediario"] == 0


def test_reincidencia_respeita_a_janela_2015_2025():
    df = pd.DataFrame([_pedido_156("A", "2014-06-01"), _pedido_156("A", "2015-06-01"), _pedido_156("A", "2026-01-01")])
    t = agregados.reincidencia_156(df).sum(numeric_only=True)
    assert t["registros"] == 1
    assert t["repetidos"] == 0


def test_locais_cronicos_nao_expoe_o_local():
    df = pd.DataFrame([_pedido_156("X", f"2020-01-{d:02d}") for d in range(1, 7)] + [_pedido_156("Y", "2020-01-01")])
    t = agregados.locais_cronicos(df, minimo=5)
    assert len(t) == 1
    assert t.loc[0, "pedidos"] == 6
    assert t.loc[0, "dias_distintos"] == 6
    assert not COLUNAS_PROIBIDAS & set(t.columns)


def test_prazos_conta_so_atendidos_por_valor_de_dias():
    df = pd.DataFrame([
        _pedido_156("A", "2020-01-01", dias=3),
        _pedido_156("B", "2020-01-01", dias=3),
        _pedido_156("C", "2020-01-01", dias=10),
        _pedido_156("D", "2020-01-01", dias=np.nan),
        _pedido_156("E", "2020-01-01", situacao="CADASTRADA", dias=50),
    ])
    t = agregados.prazos_156(df)
    assert dict(zip(t["dias"], t["n"])) == {3: 2, 10: 1}


def test_estoque_usa_so_arquivos_recentes_e_compara_com_o_p90_da_categoria():
    atendidos = [_pedido_156(str(i), "2022-01-01", dias=d) for i, d in enumerate([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])]
    abertos = [
        _pedido_156("v", "2026-09-30", situacao="CADASTRADA"),   # 7 dias de idade: dentro do p90 (~9 d)
        _pedido_156("w", "2026-01-10", situacao="EXECUCAO"),     # muito acima
        _pedido_156("z", "2019-01-10", situacao="CADASTRADA"),   # arquivo antigo: retrato congelado, fica fora
    ]
    t = agregados.estoque_156(pd.DataFrame(atendidos + abertos), pd.Timestamp("2026-10-07"))
    assert t["abertos"].sum() == 2
    assert t["acima_prazo_tipico"].sum() == 1


def test_camara_indicacoes_nao_leva_texto_nem_autoria():
    df = pd.DataFrame([{
        "fonte": "CAMARA_REQUERIMENTOS", "tipo_registro": "INDICACAO", "ano": 2024, "rpa": "1",
        "bairro_oficial": "RECIFE", "bairro_recuperado": False, "categoria": "PAVIMENTACAO", "orgao": "URB",
        "camara_canal_envio": "LOTE JSON SISTEMA PCR", "camara_desfecho": "ENVIADO, SEM RESPOSTA REGISTRADA",
        "camara_data_envio_prefeitura": pd.Timestamp("2024-02-01"), "camara_data_resposta": pd.NaT,
        "camara_dias_ate_envio": 9, "camara_dias_ate_resposta": np.nan,
        "texto": "Indica ...", "camara_autoria": "Vereador(a) X",
    }])
    t = agregados.camara_indicacoes(df)
    assert t.loc[0, "enviada"] and not t.loc[0, "respondida"]
    assert not COLUNAS_PROIBIDAS & set(t.columns)


@pytest.mark.skipif(not (CLEAN / "bairros.parquet").exists(), reason="dados do painel ainda não gerados")
def test_nenhum_arquivo_publicado_tem_coluna_sensivel():
    for arquivo in CLEAN.glob("*.parquet"):
        colunas = set(pd.read_parquet(arquivo).columns)
        assert not COLUNAS_PROIBIDAS & colunas, f"{arquivo.name} tem coluna sensível: {COLUNAS_PROIBIDAS & colunas}"
    geo = json.loads((CLEAN / "bairros.geojson").read_text(encoding="utf-8"))
    assert set(geo["features"][0]["properties"]) == {"bairro_oficial", "nome"}
