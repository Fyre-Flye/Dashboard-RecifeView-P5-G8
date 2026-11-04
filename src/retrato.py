"""Estado das filas num dia qualquer, a partir das linhas do tempo (base da War Room).

Um registro está "aberto" num dia quando já tinha entrado e ainda não tinha saído: atendido, respondido
ou concluído depois daquele dia, ou ainda sem desfecho. Em 07/10/2026 (data do download das bases) o
resultado bate com as tabelas do retrato (`estoque_156`, `indicacoes_sem_resposta` e
`manifestacoes_abertas_ouvidoria`); em datas antigas é um piso, porque pedidos de destino desconhecido
ficam de fora (ver `pipeline.agregados.linha_do_tempo_156`).
"""

import pandas as pd


def _aberto_em(entrada: pd.Series, saida: pd.Series, dia: pd.Timestamp) -> pd.Series:
    return (entrada <= dia) & (saida.isna() | (saida > dia))


def abertos_156(linha_do_tempo: pd.DataFrame, dia: pd.Timestamp) -> pd.DataFrame:
    """Pedidos do 156 abertos no dia, com a idade e a marca de "além do prazo típico" naquele dia."""
    t = linha_do_tempo[_aberto_em(linha_do_tempo["data_abertura"], linha_do_tempo["data_fim"], dia)].copy()
    t["idade_dias"] = (dia - t["data_abertura"]).dt.days
    t["atrasado"] = t["idade_dias"] > t["prazo_tipico_dias"]
    return t


def camara_sem_resposta(linha_do_tempo: pd.DataFrame, dia: pd.Timestamp) -> pd.DataFrame:
    """Indicações já enviadas à Prefeitura e ainda sem resposta no dia; a idade conta desde o envio."""
    t = linha_do_tempo[_aberto_em(linha_do_tempo["data_envio"], linha_do_tempo["data_resposta"], dia)].copy()
    t["idade_dias"] = (dia - t["data_envio"]).dt.days
    return t


def ouvidoria_alem_do_prazo(linha_do_tempo: pd.DataFrame, dia: pd.Timestamp) -> pd.DataFrame:
    """Manifestações abertas no dia cujo prazo legal já tinha passado."""
    t = linha_do_tempo[_aberto_em(linha_do_tempo["data_abertura"], linha_do_tempo["data_fim"], dia)
                       & (linha_do_tempo["data_prazo"] < dia)].copy()
    t["dias_alem_do_prazo"] = (dia - t["data_prazo"]).dt.days
    return t
