"""Tabelas agregadas que o painel lê (pasta data/clean).

Regra de privacidade: nenhuma tabela daqui leva texto livre (SEDEC ou ementa), `id_local`,
coordenadas, autoria de vereador ou identificador de registro. O que sai é contagem ou indicador
por ano, bairro, RPA, categoria e órgão, a partir de dados abertos da Prefeitura e da Câmara.
"""

import numpy as np
import pandas as pd

ANOS = (2012, 2026)
JANELA_INDICADORES = (2021, 2025)      # mesmo recorte da EDA (N3) para os indicadores por bairro
JANELA_REINCIDENCIA = (2015, 2025)     # definição padronizada de reincidência da N3 (seção 4.4)
POPULACAO_MINIMA = 1000                # bairros menores distorcem a taxa por habitante (N3, 3.8)
DUPLICIDADE_MAX_DIAS = 7
REINCIDENCIA_MIN_DIAS = 30


def _texto(serie: pd.Series) -> pd.Series:
    return serie.astype("object")


def tabela_bairros(df: pd.DataFrame, nomes_oficiais: dict[str, str]) -> pd.DataFrame:
    """Um registro por bairro oficial: nome com acento, RPA, população, domicílios e % em favela."""
    com_bairro = df.dropna(subset=["bairro_oficial"])
    t = com_bairro.groupby(_texto(com_bairro["bairro_oficial"])).agg(
        rpa=("rpa", lambda s: s.dropna().mode().iat[0] if s.notna().any() else None),
        populacao=("bairro_populacao_2022", "first"),
        domicilios=("bairro_domicilios_2022", "first"),
        pct_favela=("bairro_pct_pop_favela_2022", "first"),
    )
    t.index.name = "bairro_oficial"
    t = t.reset_index()
    t["nome"] = t["bairro_oficial"].map(nomes_oficiais).fillna(t["bairro_oficial"].str.title())
    t["rpa"] = t["rpa"].astype(str)
    t["taxa_confiavel"] = t["populacao"] >= POPULACAO_MINIMA
    return t[["bairro_oficial", "nome", "rpa", "populacao", "domicilios", "pct_favela", "taxa_confiavel"]]


def demanda(df: pd.DataFrame) -> pd.DataFrame:
    """Contagem de registros por fonte, ano, mês, território, categoria e iniciativa."""
    base = df[df["ano"].between(*ANOS)]
    chaves = {
        "fonte": _texto(base["fonte"]),
        "ano": base["ano"].astype(int),
        "mes": base["data_abertura"].dt.month.fillna(0).astype(int),
        "rpa": _texto(base["rpa"]),
        "bairro_oficial": _texto(base["bairro_oficial"]),
        "categoria": _texto(base["categoria"]),
        "iniciativa": _texto(base["iniciativa"]),
    }
    t = base.groupby(list(chaves.values()), dropna=False).size().rename("n").reset_index()
    t.columns = list(chaves) + ["n"]
    return t


def prazos_156(df: pd.DataFrame) -> pd.DataFrame:
    """Dias até a última movimentação dos pedidos ATENDIDOS do 156, contados por valor de dias.

    Guardar a contagem por valor (em vez de uma linha por pedido) mantém os percentis exatos
    e deixa o arquivo pequeno. Pedidos abertos ficam fora: não têm tempo final (censura, N2).
    """
    at = df[(df["fonte"] == "156_EMLURB") & df["ano"].between(*ANOS)
            & (df["situacao"] == "ATENDIDA") & df["dias_ate_movimento"].notna()]
    t = at.groupby([at["ano"].astype(int), _texto(at["rpa"]), _texto(at["bairro_oficial"]),
                    _texto(at["categoria"]), at["dias_ate_movimento"].astype(int)], dropna=False).size()
    t = t.rename("n").reset_index()
    t.columns = ["ano", "rpa", "bairro_oficial", "categoria", "dias", "n"]
    return t


def _base_reincidencia(df: pd.DataFrame) -> pd.DataFrame:
    """156 com número no endereço, na janela padronizada, com o tamanho e o intervalo de cada chave."""
    rr = df[(df["fonte"] == "156_EMLURB") & df["ano"].between(*JANELA_REINCIDENCIA)
            & (df["numero_informado"].astype(str) == "True")].sort_values("data_abertura")
    chave = rr.groupby([rr["id_local"], _texto(rr["servico_codigo"])], dropna=False)
    rr = rr.assign(
        pedidos_no_local=chave["id_local"].transform("size"),
        intervalo=chave["data_abertura"].diff().dt.days,
    )
    return rr


def limite_local_generico(pedidos_por_chave: pd.Series) -> float:
    """Acima do p99 de pedidos por local + serviço, o 'local' quase certamente é um endereço genérico (N3, 6.4)."""
    return float(pedidos_por_chave.quantile(0.99))


def reincidencia_156(df: pd.DataFrame) -> pd.DataFrame:
    """Por ano, território e categoria: quantos pedidos caem num local + serviço repetido e como se repetem.

    Um pedido é "repetido" quando a chave local + serviço aparece 2+ vezes na janela 2015–2025.
    O intervalo até o pedido anterior da mesma chave separa duplicidade (até 7 dias) de
    reincidência (30 dias ou mais). `repetidos_local_generico` conta os repetidos em chaves acima
    do p99, para o painel poder tirá-los da conta.
    """
    rr = _base_reincidencia(df)
    pedidos_por_chave = rr.groupby([rr["id_local"], _texto(rr["servico_codigo"])], dropna=False).size()
    limite = limite_local_generico(pedidos_por_chave)
    repetido = rr["pedidos_no_local"] >= 2
    generico = rr["pedidos_no_local"] > limite
    t = pd.DataFrame({
        "ano": rr["ano"].astype(int),
        "rpa": _texto(rr["rpa"]),
        "bairro_oficial": _texto(rr["bairro_oficial"]),
        "categoria": _texto(rr["categoria"]),
        "registros": 1,
        "repetidos": repetido.astype(int),
        "repetidos_local_generico": (repetido & generico).astype(int),
        "intervalo_duplicidade": (rr["intervalo"] <= DUPLICIDADE_MAX_DIAS).astype(int),
        "intervalo_intermediario": rr["intervalo"].between(DUPLICIDADE_MAX_DIAS + 1, REINCIDENCIA_MIN_DIAS - 1).astype(int),
        "intervalo_reincidencia": (rr["intervalo"] >= REINCIDENCIA_MIN_DIAS).astype(int),
    })
    return t.groupby(["ano", "rpa", "bairro_oficial", "categoria"], dropna=False).sum().reset_index()


def locais_cronicos(df: pd.DataFrame, minimo: int = 5) -> pd.DataFrame:
    """Locais + serviço com `minimo` pedidos ou mais, SEM o identificador do local.

    Cada linha diz apenas "um endereço do bairro X teve N pedidos do serviço Y entre os anos A e B".
    """
    rr = _base_reincidencia(df)
    rr = rr[rr["pedidos_no_local"] >= minimo]
    g = rr.groupby([rr["id_local"], _texto(rr["servico_codigo"])], dropna=False)
    t = g.agg(
        bairro_oficial=("bairro_oficial", "first"),
        rpa=("rpa", "first"),
        categoria=("categoria", "first"),
        servico=("servico", "first"),
        pedidos=("ano", "size"),
        primeiro_ano=("ano", "min"),
        ultimo_ano=("ano", "max"),
        dias_distintos=("data_abertura", "nunique"),
    ).reset_index(drop=True)
    for c in ["bairro_oficial", "rpa", "categoria", "servico"]:
        t[c] = _texto(t[c])
    return t.sort_values("pedidos", ascending=False).reset_index(drop=True)


def camara_indicacoes(df: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por indicação de vereador, só com o caminho até a Prefeitura (sem ementa nem autoria)."""
    ind = df[(df["fonte"] == "CAMARA_REQUERIMENTOS") & (df["tipo_registro"] == "INDICACAO")]
    return pd.DataFrame({
        "ano": ind["ano"].astype(int),
        "rpa": _texto(ind["rpa"]),
        "bairro_oficial": _texto(ind["bairro_oficial"]),
        "bairro_recuperado": ind["bairro_recuperado"].astype(bool),
        "categoria": _texto(ind["categoria"]),
        "orgao": _texto(ind["orgao"]),
        "canal_envio": _texto(ind["camara_canal_envio"]),
        "desfecho": _texto(ind["camara_desfecho"]),
        "enviada": ind["camara_data_envio_prefeitura"].notna(),
        "respondida": ind["camara_data_resposta"].notna(),
        "dias_ate_envio": pd.to_numeric(ind["camara_dias_ate_envio"], errors="coerce"),
        "dias_ate_resposta": pd.to_numeric(ind["camara_dias_ate_resposta"], errors="coerce"),
    }).reset_index(drop=True)


def ouvidoria(df: pd.DataFrame) -> pd.DataFrame:
    """Manifestações por ano, órgão, natureza, canal de entrada e cumprimento do prazo."""
    o = df[df["fonte"] == "OUVIDORIA"]
    chaves = [o["ano"].astype(int), _texto(o["orgao"]), _texto(o["tipo_registro"]),
              _texto(o["canal_entrada"]), _texto(o["ouv_no_prazo"])]
    t = o.groupby(chaves, dropna=False).size().rename("n").reset_index()
    t.columns = ["ano", "orgao", "natureza", "canal_entrada", "no_prazo", "n"]
    return t


def estoque_156(df: pd.DataFrame, data_referencia: pd.Timestamp) -> pd.DataFrame:
    """Pedidos ainda abertos nos arquivos recentes do 156 (2025 e 2026) e quantos passaram do prazo típico.

    Cada arquivo anual é um retrato; pedidos antigos "abertos" podem só ter congelado no retrato do
    seu ano (N3, seção 7, item 6). Por isso o estoque usa só os dois arquivos mais recentes.
    "Prazo típico" = p90 dos dias até atender da mesma categoria (atendidos de 2021 a 2025).
    """
    s = df[df["fonte"] == "156_EMLURB"]
    atendidos = s[s["ano"].between(*JANELA_INDICADORES) & (s["situacao"] == "ATENDIDA")]
    p90 = atendidos.groupby(_texto(atendidos["categoria"]))["dias_ate_movimento"].quantile(0.9)

    abertos = s[_texto(s["arquivo_origem"]).isin(["156_2025", "156_2026"]) & (s["situacao"] != "ATENDIDA")]
    idade = (data_referencia - abertos["data_abertura"]).dt.days
    limite = _texto(abertos["categoria"]).map(p90)
    t = pd.DataFrame({
        "rpa": _texto(abertos["rpa"]),
        "bairro_oficial": _texto(abertos["bairro_oficial"]),
        "categoria": _texto(abertos["categoria"]),
        "situacao": _texto(abertos["situacao"]),
        "abertos": 1,
        "acima_prazo_tipico": (idade > limite).astype(int),
    })
    return t.groupby(["rpa", "bairro_oficial", "categoria", "situacao"], dropna=False).sum().reset_index()


def _taxa_por_mil(base: pd.DataFrame, anos: int, populacao: pd.Series, por: int = 1000) -> pd.Series:
    n = base.groupby(_texto(base["bairro_oficial"])).size()
    return (n / anos / populacao * por).reindex(populacao.index)


def indicadores_bairro(df: pd.DataFrame, bairros: pd.DataFrame, estoque: pd.DataFrame) -> pd.DataFrame:
    """Indicadores por bairro na janela da N3 (2021–2025), base do índice de prioridade (AHP).

    Bairros com menos de 1.000 moradores ficam fora, como na EDA.
    """
    b = bairros[bairros["taxa_confiavel"]].set_index("bairro_oficial")
    pop = b["populacao"]
    a0, a1 = JANELA_INDICADORES
    s156 = df[(df["fonte"] == "156_EMLURB") & df["ano"].between(a0, a1)]
    dc = df[(df["fonte"] == "DEFESA_CIVIL") & (df["iniciativa"] == "CIDADAO") & df["ano"].between(a0, 2024)]
    sedec = df[(df["fonte"] == "SEDEC_CHAMADOS") & df["ano"].between(a0, 2023)]
    ind = df[(df["fonte"] == "CAMARA_REQUERIMENTOS") & (df["tipo_registro"] == "INDICACAO") & df["ano"].between(a0, a1)]

    t = pd.DataFrame(index=b.index)
    t["nome"] = b["nome"]
    t["rpa"] = b["rpa"]
    t["populacao"] = pop
    t["pct_favela"] = b["pct_favela"]
    t["taxa_156"] = _taxa_por_mil(s156, a1 - a0 + 1, pop)
    t["taxa_defesa_civil"] = _taxa_por_mil(dc, 2024 - a0 + 1, pop).fillna(0)
    t["taxa_sedec"] = _taxa_por_mil(sedec, 2023 - a0 + 1, pop).fillna(0)
    t["taxa_indicacoes"] = _taxa_por_mil(ind, a1 - a0 + 1, pop, por=10000).fillna(0)

    fechou = s156[(s156["situacao"] == "ATENDIDA") & (s156["dias_ate_movimento"] > 0)]
    t["mediana_dias_156"] = fechou.groupby(_texto(fechou["bairro_oficial"]))["dias_ate_movimento"].median()

    com_numero = s156[s156["numero_informado"].astype(str) == "True"]
    repetido = com_numero.groupby([com_numero["id_local"], _texto(com_numero["servico_codigo"])],
                                  dropna=False)["id_local"].transform("size") >= 2
    t["pct_reincidencia_156"] = repetido.groupby(_texto(com_numero["bairro_oficial"])).mean() * 100

    e = estoque.groupby("bairro_oficial")[["abertos", "acima_prazo_tipico"]].sum()
    t["abertos_156"] = e["abertos"]
    t["pct_atraso_156"] = e["acima_prazo_tipico"] / e["abertos"] * 100
    return t.reset_index()
