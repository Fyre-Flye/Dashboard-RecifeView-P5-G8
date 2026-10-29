"""Correções aplicadas ao dataset do grupo antes de agregar para o painel.

São as mesmas da EDA (N3, seção 1 e seção 7 do notebook), trazidas para cá para que o painel
não dependa de correções escondidas num notebook. Cada função recebe o DataFrame, devolve uma
cópia corrigida e o número de linhas afetadas, para o log da preparação.

As coordenadas (lat/lon) não entram no painel (o recorte territorial é o bairro), por isso a
anulação de coordenadas fora do Recife da N3 não aparece aqui.
"""

import re
import unicodedata

import numpy as np
import pandas as pd

# 156: grafias diferentes da mesma categoria (N3, 1.4)
CATEGORIAS_156 = {"TERRAPLANAGEN": "TERRAPLENAGEM", "TERRAPLANAGEM": "TERRAPLENAGEM"}

# Ouvidoria: o mesmo órgão com dois nomes, porque o formato mudou em 2023 (nome longo -> sigla)
# e em 2024 (hífen). Sem isso, a série de cada órgão "some" num ano e "nasce" em outro (N3, 1.5).
ORGAOS_OUVIDORIA = {
    "AUTARQUIA DE MANUTENCAO E LIMPEZA URBANA DO RECIFE-EMLURB": "EMLURB",
    "AUTARQUIA DE TRANSITO E TRANSPORTE URBANO DO RECIFE-CTTU": "CTTU",
    "AUTARQUIA DE URBANIZACAO DO RECIFE-URB": "URB",
    "EMPRESA MUNICIPAL DE INFORMATICA-EMPREL": "EMPREL",
    "MERCADOS E FEIRAS - AUTARQUIA MUNICIPAL-CONVIVA": "CONVIVA",
    "SAUDE RECIFE-RECIPREV": "RECIPREV",
    "CONSELHO MUNICIPAL DE DEFESA E PROMOCAO DOS DIREITOS DA CRIANCA E DO ADOLESCENTE-COMDICA": "COMDICA",
    "SECRETARIA-EXECUTIVA DE DEFESA CIVIL": "SECRETARIA EXECUTIVA DE DEFESA CIVIL",
    "CONTROLADORIA-GERAL DO MUNICIPIO": "CONTROLADORIA GERAL DO MUNICIPIO",
    "PROCURADORIA-GERAL DO MUNICIPIO": "PROCURADORIA GERAL DO MUNICIPIO",
    "SECRETARIA PLANEJAMENTO, GESTAO E TRANSFORMACAO DIGITAL": "SECRETARIA DE PLANEJAMENTO, GESTAO E TRANSFORMACAO DIGITAL",
}

# Câmara: nomes populares que a ementa usa para bairros oficiais (N3, 1.6)
APELIDOS_BAIRRO = {
    "SITIO DOS PINTOS": "SITIO DOS PINTOS - SAO BRAS",
    "SAO BRAS": "SITIO DOS PINTOS - SAO BRAS",
    "COHAB IBURA DE CIMA": "COHAB",
    "IBURA DE BAIXO": "IBURA",
    "BAIRRO DO RECIFE": "RECIFE",
    "RECIFE ANTIGO": "RECIFE",
    "POCO DA PANELA": "POCO",
    "ZUMBI DO PACHECO": "ZUMBI",
}


def normalizar(texto) -> str:
    """Maiúsculas, sem acento e sem espaço duplo (a mesma chave usada no pipeline do grupo)."""
    sem_acento = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento.upper()).strip()


def _substituir(serie: pd.Series, mapa: dict, mascara: pd.Series) -> pd.Series:
    """Troca valores segundo o mapa só nas linhas da máscara, preservando vazios."""
    nova = serie.astype("object").copy()
    nova[mascara] = nova[mascara].replace(mapa)
    return nova


def anular_prazos_negativos(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Movimento antes da abertura é defeito da fonte: o prazo vira vazio e a marca fica em `prazo_negativo`."""
    df = df.copy()
    negativo = df["dias_ate_movimento"] < 0
    df["prazo_negativo"] = negativo
    df.loc[negativo, "dias_ate_movimento"] = np.nan
    return df, int(negativo.sum())


def unificar_categorias_156(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    df = df.copy()
    alvo = (df["fonte"] == "156_EMLURB") & df["categoria"].isin(list(CATEGORIAS_156))
    df["categoria"] = _substituir(df["categoria"], CATEGORIAS_156, alvo)
    return df, int(alvo.sum())


def harmonizar_orgaos_ouvidoria(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    df = df.copy()
    alvo = (df["fonte"] == "OUVIDORIA") & df["orgao"].isin(list(ORGAOS_OUVIDORIA))
    df["orgao"] = _substituir(df["orgao"], ORGAOS_OUVIDORIA, alvo)
    return df, int(alvo.sum())


def _padrao_bairro(bairros_oficiais) -> re.Pattern:
    # Só aceita o nome de bairro que vem depois de "bairro", "comunidade" ou "localidade": na N3, o nome
    # solto no texto era nome de rua em cerca de 1 a cada 4 casos ("Rua Zumbi dos Palmares").
    chaves = sorted(set(bairros_oficiais) | set(APELIDOS_BAIRRO), key=len, reverse=True)
    return re.compile(
        r"\b(?:BAIRRO|COMUNIDADE|LOCALIDADE)\s+(?:D[OAE]S?\s+|EM\s+)?(" + "|".join(map(re.escape, chaves)) + r")\b"
    )


def bairro_no_texto(texto, padrao: re.Pattern):
    achado = padrao.search(normalizar(texto))
    if achado is None:
        return None
    return APELIDOS_BAIRRO.get(achado.group(1), achado.group(1))


def recuperar_bairro_camara(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Preenche o bairro das matérias da Câmara que vieram sem, lendo a ementa (coluna `texto`).

    Marca as linhas preenchidas em `bairro_recuperado`. Não altera quem já tinha bairro.
    """
    df = df.copy()
    oficiais = df["bairro_oficial"].dropna().astype(str).unique()
    padrao = _padrao_bairro(oficiais)
    sem_bairro = (df["fonte"] == "CAMARA_REQUERIMENTOS") & df["bairro_oficial"].isna() & df["texto"].notna()
    achados = df.loc[sem_bairro, "texto"].map(lambda t: bairro_no_texto(t, padrao)).dropna()

    df["bairro_oficial"] = df["bairro_oficial"].astype("object")
    df.loc[achados.index, "bairro_oficial"] = achados
    df["bairro_recuperado"] = False
    df.loc[achados.index, "bairro_recuperado"] = True
    return df, len(achados)


def completar_territorio(df: pd.DataFrame) -> pd.DataFrame:
    """Leva RPA e dados do Censo às linhas cujo bairro foi recuperado (o bairro oficial define os dois)."""
    df = df.copy()
    df["rpa"] = df["rpa"].astype("object").where(df["rpa"].astype("object") != "Não informada")
    por_bairro = df.dropna(subset=["bairro_oficial", "rpa"]).groupby("bairro_oficial", observed=True).agg(
        rpa=("rpa", lambda s: s.mode().iat[0]),
        bairro_populacao_2022=("bairro_populacao_2022", "first"),
        bairro_pct_pop_favela_2022=("bairro_pct_pop_favela_2022", "first"),
    )
    df["rpa"] = df["rpa"].astype("object")
    for coluna in por_bairro.columns:
        faltando = df[coluna].isna() & df["bairro_oficial"].notna()
        df.loc[faltando, coluna] = df.loc[faltando, "bairro_oficial"].map(por_bairro[coluna])
    return df


def marcar_fechado_no_dia(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Prazo de zero dias costuma ser encerramento administrativo, não execução (N3, seção 7, item 4)."""
    df = df.copy()
    df["fechado_no_dia"] = df["dias_ate_movimento"] == 0
    return df, int(df["fechado_no_dia"].sum())
