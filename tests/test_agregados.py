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


def test_ocorrencias_abertas_contam_pedidos_anteriores_sem_expor_o_local():
    df = pd.DataFrame([
        _pedido_156("A", "2023-01-01"),
        _pedido_156("A", "2024-01-01"),
        _pedido_156("A", "2025-03-01", situacao="CADASTRADA", dias=None),     # aberto: 2 anteriores
        _pedido_156("A", "2025-03-01", situacao="CADASTRADA", dias=None),     # mesmo dia: não conta como anterior
        _pedido_156("B", "2025-05-01", situacao="EXECUCAO", dias=None),       # aberto, local novo: 0
        _pedido_156("C", "2025-05-01", situacao="CADASTRADA", dias=None, numero=False),  # sem número: vazio
        _pedido_156("D", "2024-05-01", situacao="CADASTRADA", dias=None),     # arquivo antigo: fora
    ])
    t = agregados.ocorrencias_abertas_156(df, pd.Timestamp("2025-06-01"))
    assert len(t) == 4
    assert not COLUNAS_PROIBIDAS & set(t.columns)
    assert t["pedidos_anteriores"].tolist()[:2] == [2, 2]
    assert t["pedidos_anteriores"].isna().sum() == 1
    assert t.loc[t["situacao"] == "EXECUCAO", "pedidos_anteriores"].item() == 0
    assert t["idade_dias"].tolist()[:2] == [92, 92]


def _indicacao(data, envio, resposta=None, bairro="VARZEA", categoria="DRENAGEM", dias_resposta=None):
    return {"fonte": "CAMARA_REQUERIMENTOS", "tipo_registro": "INDICACAO", "ano": pd.Timestamp(data).year,
            "data_abertura": pd.Timestamp(data), "camara_data_envio_prefeitura": pd.Timestamp(envio) if envio else pd.NaT,
            "camara_data_resposta": pd.Timestamp(resposta) if resposta else pd.NaT,
            "camara_dias_ate_resposta": dias_resposta, "camara_canal_envio": "OFICIO", "orgao": "EMLURB",
            "camara_desfecho": "ENVIADO E COM RESPOSTA REGISTRADA" if resposta else "ENVIADO, SEM RESPOSTA REGISTRADA",
            "bairro_oficial": bairro, "rpa": "4", "categoria": categoria, "texto": "ementa", "camara_autoria": "vereador"}


def test_indicacoes_sem_resposta_contam_repeticao_no_bairro_e_nao_levam_ementa():
    df = pd.DataFrame([
        _indicacao("2024-01-01", "2024-01-05", "2024-03-01", dias_resposta=60),
        _indicacao("2024-02-01", "2024-02-03"),                       # sem resposta; 1 anterior no bairro (31 dias)
        _indicacao("2024-09-01", "2024-09-02"),                       # sem resposta; anteriores fora da janela de 90 dias
        _indicacao("2024-02-01", "2024-02-03", bairro="IPUTINGA"),    # outro bairro
    ])
    t = agregados.indicacoes_sem_resposta(df, pd.Timestamp("2025-01-01"))
    assert len(t) == 3
    assert not COLUNAS_PROIBIDAS & set(t.columns) and "camara_autoria" not in t.columns
    varzea = t[t["bairro_oficial"] == "VARZEA"].sort_values("data_envio")
    assert varzea["pedidos_anteriores"].tolist() == [1, 0]
    assert t.loc[t["bairro_oficial"] == "IPUTINGA", "pedidos_anteriores"].item() == 0
    assert varzea["idade_dias"].iloc[0] == (pd.Timestamp("2025-01-01") - pd.Timestamp("2024-02-03")).days


def test_manifestacoes_abertas_usam_so_arquivos_recentes_e_situacao_aberta():
    base = {"fonte": "OUVIDORIA", "servico": "OBRA", "tipo_registro": "RECLAMACAO", "orgao": "URB",
            "canal_entrada": "0800", "texto": None}
    df = pd.DataFrame([
        base | {"arquivo_origem": "ouvidoria_2025", "situacao": "ABERTO", "data_abertura": pd.Timestamp("2025-08-01"),
                "ouv_data_prazo": pd.Timestamp("2025-08-15")},
        base | {"arquivo_origem": "ouvidoria_2025", "situacao": "CONCLUIDO", "data_abertura": pd.Timestamp("2025-08-01"),
                "ouv_data_prazo": pd.Timestamp("2025-08-15")},
        base | {"arquivo_origem": "ouvidoria_2021", "situacao": "ABERTO", "data_abertura": pd.Timestamp("2021-08-01"),
                "ouv_data_prazo": pd.Timestamp("2021-08-15")},
        base | {"arquivo_origem": "ouvidoria_2025", "situacao": "texto quebrado com nome", "data_abertura": pd.Timestamp("2025-08-01"),
                "ouv_data_prazo": pd.Timestamp("2025-08-15")},
    ])
    t = agregados.manifestacoes_abertas_ouvidoria(df, pd.Timestamp("2025-09-14"))
    assert len(t) == 1
    assert t["dias_alem_do_prazo"].item() == 30
    assert not COLUNAS_PROIBIDAS & set(t.columns)


def test_coordenada_aproximada_arredonda_e_descarta_fora_do_recife():
    lon, lat = agregados.coordenada_aproximada(pd.Series([-34.912345, -40.0, None]), pd.Series([-8.054321, -8.05, -8.05]))
    assert lon.iloc[0] == -34.912 and lat.iloc[0] == -8.054
    assert lon.iloc[1:].isna().all() and lat.iloc[1:].isna().all()


def test_coordenada_publicada_tem_no_maximo_tres_casas():
    t = pd.read_parquet(CLEAN / "ocorrencias_abertas_156.parquet")
    for coluna in ["lon_aprox", "lat_aprox"]:
        valores = t[coluna].dropna()
        assert ((valores * 1000).round() - valores * 1000).abs().max() < 1e-6


def test_dicionario_cobre_o_dataset_sem_expor_dado_pessoal():
    dic = pd.read_parquet(Path(__file__).resolve().parents[1] / "data" / "clean" / "dicionario_dataset.parquet")
    assert len(dic) == 45 and dic["coluna"].is_unique
    assert dic[["descricao", "grupo", "papel_em_modelo"]].notna().all().all()
    sensiveis = dic[dic["coluna"].isin(COLUNAS_PROIBIDAS | {"camara_autoria", "mes"})]
    assert (sensiveis["exemplos"] == "").all()
