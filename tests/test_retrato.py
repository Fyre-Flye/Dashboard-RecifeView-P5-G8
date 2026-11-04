"""O estado reconstruído na data do download bate com as tabelas do retrato publicadas."""

from pathlib import Path

import pandas as pd

from src import retrato

CLEAN = Path(__file__).resolve().parents[1] / "data" / "clean"
DIA_DO_RETRATO = pd.Timestamp("2026-10-07")


def _ler(nome: str) -> pd.DataFrame:
    return pd.read_parquet(CLEAN / f"{nome}.parquet")


def test_estoque_do_156_na_data_do_retrato_bate_com_o_estoque_publicado():
    abertos = retrato.abertos_156(_ler("linha_do_tempo_156"), DIA_DO_RETRATO)
    estoque = _ler("estoque_156")
    assert len(abertos) == estoque["abertos"].sum()
    assert abertos["atrasado"].sum() == estoque["acima_prazo_tipico"].sum()


def test_camara_e_ouvidoria_na_data_do_retrato_batem_com_as_tabelas_publicadas():
    assert len(retrato.camara_sem_resposta(_ler("linha_do_tempo_camara"), DIA_DO_RETRATO)) == \
        len(_ler("indicacoes_sem_resposta"))
    assert len(retrato.ouvidoria_alem_do_prazo(_ler("linha_do_tempo_ouvidoria"), DIA_DO_RETRATO)) == \
        len(_ler("manifestacoes_abertas_ouvidoria"))


def test_pedido_conta_como_aberto_so_entre_a_entrada_e_a_saida():
    t = pd.DataFrame({"data_abertura": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-03-01"]),
                      "data_fim": pd.to_datetime(["2024-01-10", None, None]), "prazo_tipico_dias": [5.0, 5.0, 5.0]})
    dia = pd.Timestamp("2024-02-01")
    abertos = retrato.abertos_156(t, dia)
    assert len(abertos) == 1                       # o 1º já saiu; o 3º ainda não entrou
    assert abertos["idade_dias"].item() == 31 and abertos["atrasado"].item()
    assert len(retrato.abertos_156(t, pd.Timestamp("2024-01-05"))) == 2
