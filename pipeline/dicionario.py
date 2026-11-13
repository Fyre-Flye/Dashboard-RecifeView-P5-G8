"""Gera o dicionário do dataset do grupo (data/clean/dicionario_dataset.parquet) para a página Sobre os Dados.

Uso, na raiz do repositório:

    python -m pipeline.dicionario

Junta a descrição de cada coluna, escrita pelo grupo (data/referencia/dicionario_de_colunas.csv, cópia do Drive),
com medidas tiradas do próprio dataset: tipo lido, % preenchido no total e em cada fonte, valores distintos e,
só para colunas sem dado pessoal, os valores mais comuns. Lê o arquivo em partes para caber na memória.
"""

from collections import Counter
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
DATASET = RAIZ / "data" / "raw" / "recifeview_demandas_recife_2012_2026.csv.xz"
DESCRICOES = RAIZ / "data" / "referencia" / "dicionario_de_colunas.csv"
SAIDA = RAIZ / "data" / "clean" / "dicionario_dataset.parquet"
FONTES = ["156_EMLURB", "DEFESA_CIVIL", "OUVIDORIA", "SEDEC_CHAMADOS", "CAMARA_REQUERIMENTOS"]
TAMANHO_PARTE = 300_000
MAX_DISTINTOS_CONTADOS = 3_000_000

# Colunas que nunca têm exemplo publicado: identificam pessoa, endereço ou processo, ou são texto livre.
SEM_EXEMPLO = {"id", "id_registro", "id_local", "lat", "lon", "texto", "camara_autoria", "localidade",
               "data_abertura", "data_ult_movimento", "ouv_data_prazo", "camara_data_envio_prefeitura",
               "camara_data_resposta", "mes"}
MAX_EXEMPLOS = 4
COM_INTERVALO = {"ano", "data_abertura", "data_ult_movimento", "dias_ate_movimento", "ouv_data_prazo",
                 "camara_data_envio_prefeitura", "camara_dias_ate_envio", "camara_data_resposta",
                 "camara_dias_ate_resposta", "bairro_populacao_2022", "bairro_domicilios_2022",
                 "bairro_pct_pop_favela_2022", "sedec_n_pedidos_vistoria", "sedec_n_pedidos_lona"}

GRUPO = {
    "Identificação": ["id", "fonte", "id_registro", "arquivo_origem"],
    "Tempo": ["ano", "mes", "data_abertura", "data_ult_movimento", "dias_ate_movimento"],
    "O que foi pedido": ["categoria", "servico_codigo", "servico", "tipo_registro", "iniciativa", "rotulos_ocorrencia"],
    "Para onde foi": ["orgao", "canal_entrada", "situacao"],
    "Território": ["bairro", "bairro_oficial", "rpa", "rpa_inferida", "localidade", "regional", "id_local",
                   "numero_informado", "lat", "lon"],
    "Texto": ["texto", "texto_de_atendente"],
    "SEDEC": ["sedec_n_pedidos_vistoria", "sedec_n_pedidos_lona"],
    "Ouvidoria": ["ouv_data_prazo", "ouv_no_prazo", "ouv_resposta_antes_do_registro"],
    "Câmara": ["camara_autoria", "camara_data_envio_prefeitura", "camara_canal_envio", "camara_dias_ate_envio",
               "camara_data_resposta", "camara_dias_ate_resposta", "camara_desfecho"],
    "Bairro (IBGE)": ["bairro_populacao_2022", "bairro_domicilios_2022", "bairro_pct_pop_favela_2022"],
}

# Papel de cada coluna num modelo supervisionado. Não decide o modelo: aponta o que pode ser alvo, o que pode
# entrar como atributo, o que só se sabe depois do atendimento (vazamento) e o que não deve entrar.
PAPEL = {
    "Identificador (não usar)": ["id", "id_registro", "arquivo_origem"],
    "Alvo possível": ["categoria", "servico_codigo", "servico", "orgao", "rotulos_ocorrencia"],
    "Entrada de texto": ["texto"],
    "Atributo": ["fonte", "ano", "mes", "data_abertura", "tipo_registro", "iniciativa", "canal_entrada", "bairro",
                 "bairro_oficial", "rpa", "rpa_inferida", "localidade", "regional", "numero_informado",
                 "texto_de_atendente", "sedec_n_pedidos_vistoria", "sedec_n_pedidos_lona", "ouv_data_prazo",
                 "camara_canal_envio", "camara_data_envio_prefeitura", "camara_dias_ate_envio",
                 "bairro_populacao_2022", "bairro_domicilios_2022", "bairro_pct_pop_favela_2022"],
    "Resultado (vazamento se for atributo)": ["data_ult_movimento", "dias_ate_movimento", "situacao", "ouv_no_prazo",
                                              "ouv_resposta_antes_do_registro", "camara_data_resposta",
                                              "camara_dias_ate_resposta", "camara_desfecho"],
    "Uso interno (sensível)": ["id_local", "lat", "lon", "camara_autoria"],
}


def _inverter(mapa: dict[str, list[str]]) -> dict[str, str]:
    return {coluna: chave for chave, colunas in mapa.items() for coluna in colunas}


def _intervalo(menor, maior) -> str:
    if menor is None:
        return ""
    def texto(v) -> str:
        return f"{v:g}" if isinstance(v, float) else str(v)
    return f"{texto(menor)} a {texto(maior)}"


def medir(caminho: Path) -> tuple[pd.DataFrame, int]:
    preenchidos: Counter = Counter()
    por_fonte: Counter = Counter()
    linhas_fonte: Counter = Counter()
    distintos: dict[str, set] = {}
    contagens: dict[str, Counter] = {}
    colunas: list[str] = []
    menor: dict[str, object] = {}
    maior: dict[str, object] = {}
    total = 0
    for parte in pd.read_csv(caminho, chunksize=TAMANHO_PARTE, dtype=str, keep_default_na=True):
        total += len(parte)
        linhas_fonte.update(parte["fonte"].value_counts().to_dict())
        for coluna in parte.columns:
            serie = parte[coluna].str.strip().replace("", None)
            if coluna not in colunas:
                colunas.append(coluna)
            validos = serie.notna()
            preenchidos[coluna] += int(validos.sum())
            for fonte, n in parte.loc[validos, "fonte"].value_counts().items():
                por_fonte[(coluna, fonte)] += int(n)
            if coluna in COM_INTERVALO and validos.any():
                valores = serie.dropna()
                if not coluna.startswith(("data_", "ouv_data", "camara_data")):
                    valores = pd.to_numeric(valores, errors="coerce").dropna()
                menor[coluna] = min(menor.get(coluna, valores.min()), valores.min())
                maior[coluna] = max(maior.get(coluna, valores.max()), valores.max())
            vistos = distintos.setdefault(coluna, set())
            if len(vistos) < MAX_DISTINTOS_CONTADOS:
                vistos.update(serie.dropna().unique().tolist())
            if coluna not in SEM_EXEMPLO:
                contagens.setdefault(coluna, Counter()).update(serie.dropna().value_counts().to_dict())
    linhas = []
    for coluna in colunas:
        registro = {"coluna": coluna,
                    "pct_preenchido": preenchidos[coluna] / total * 100,
                    "n_distintos": len(distintos[coluna]),
                    "exemplos": " · ".join(v for v, _ in contagens[coluna].most_common(MAX_EXEMPLOS))
                    if coluna in contagens else "",
                    "intervalo": _intervalo(menor.get(coluna), maior.get(coluna))}
        for fonte in FONTES:
            registro[f"pct_{fonte}"] = por_fonte[(coluna, fonte)] / linhas_fonte[fonte] * 100
        linhas.append(registro)
    return pd.DataFrame(linhas), total


def main() -> None:
    medidas, total = medir(DATASET)
    descricoes = pd.read_csv(DESCRICOES)
    tabela = descricoes.merge(medidas, on="coluna", how="right")
    tabela["grupo"] = tabela["coluna"].map(_inverter(GRUPO))
    tabela["papel_em_modelo"] = tabela["coluna"].map(_inverter(PAPEL))
    tabela["ordem"] = range(len(tabela))
    faltando = tabela[tabela["grupo"].isna() | tabela["papel_em_modelo"].isna() | tabela["descricao"].isna()]
    if not faltando.empty:
        raise ValueError(f"colunas sem grupo, papel ou descrição: {faltando['coluna'].tolist()}")
    tabela.to_parquet(SAIDA, index=False)
    print(f"{len(tabela)} colunas, {total:,} linhas -> {SAIDA}")


if __name__ == "__main__":
    main()
