"""Gera as tabelas do painel (data/clean) a partir do dataset do grupo (data/raw).

Uso, na raiz do repositório:

    python -m pipeline.preparar_dados

Entradas (NÃO versionadas; copie da pasta Dados do Drive do grupo para data/raw/):
- recifeview_demandas_recife_2012_2026.csv.xz   (Dados/01_DATASET_PRINCIPAL_recifeview-dataset)
- referencia_bairros.zip                          (Dados/02_fontes_separadas/bruto)

Saídas (versionadas): tabelas agregadas em Parquet, a malha de bairros simplificada e um
resumo da preparação em JSON.
"""

import json
import time
import zipfile
from pathlib import Path

import pandas as pd
from shapely.geometry import mapping, shape

from pipeline import agregados, correcoes

RAIZ = Path(__file__).resolve().parents[1]
BRUTO = RAIZ / "data" / "raw"
SAIDA = RAIZ / "data" / "clean"
DATASET = BRUTO / "recifeview_demandas_recife_2012_2026.csv.xz"
MALHA = BRUTO / "referencia_bairros.zip"

# Data em que as bases abertas foram baixadas (README do dataset): referência para a idade do estoque aberto.
DATA_REFERENCIA = pd.Timestamp("2026-10-07")

COLUNAS = [
    "fonte", "ano", "data_abertura", "data_ult_movimento", "dias_ate_movimento", "categoria", "servico_codigo",
    "servico", "tipo_registro", "orgao", "canal_entrada", "bairro_oficial", "rpa", "situacao", "iniciativa",
    "id_local", "numero_informado", "texto", "ouv_no_prazo", "camara_data_envio_prefeitura", "camara_canal_envio",
    "camara_data_resposta", "camara_dias_ate_envio", "camara_dias_ate_resposta", "camara_desfecho",
    "bairro_populacao_2022", "bairro_domicilios_2022", "bairro_pct_pop_favela_2022", "arquivo_origem",
]
CATEGORICAS = ["fonte", "categoria", "servico_codigo", "servico", "tipo_registro", "orgao", "canal_entrada",
               "bairro_oficial", "rpa", "situacao", "iniciativa", "numero_informado", "texto", "ouv_no_prazo",
               "camara_canal_envio", "camara_desfecho", "arquivo_origem"]
DATAS = ["data_abertura", "data_ult_movimento", "camara_data_envio_prefeitura", "camara_data_resposta"]


def ler_dataset(caminho: Path) -> pd.DataFrame:
    tipos = {c: "category" for c in CATEGORICAS} | {"id_local": "str"}
    df = pd.read_csv(caminho, usecols=COLUNAS, dtype=tipos, low_memory=False)
    for c in DATAS:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    df["ano"] = pd.to_numeric(df["ano"], errors="coerce")
    return df


def aplicar_correcoes(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    log = {}
    df, log["prazos negativos anulados"] = correcoes.anular_prazos_negativos(df)
    df, log["156: categorias unificadas (terraplenagem)"] = correcoes.unificar_categorias_156(df)
    df, log["Ouvidoria: nomes de órgão harmonizados"] = correcoes.harmonizar_orgaos_ouvidoria(df)
    df, log["Câmara: matérias com bairro recuperado pela ementa"] = correcoes.recuperar_bairro_camara(df)
    df = correcoes.completar_territorio(df)
    df, log["registros com prazo de zero dias (marcados)"] = correcoes.marcar_fechado_no_dia(df)
    df = df.drop(columns=["texto"])        # a ementa só serviu para recuperar o bairro; não sai daqui
    return df, log


def malha_simplificada(caminho_zip: Path, tolerancia: float = 0.0002) -> tuple[dict, dict[str, str]]:
    """GeoJSON dos 94 bairros com a geometria simplificada (~20 m) e a chave `bairro_oficial`."""
    with zipfile.ZipFile(caminho_zip) as zf:
        nome = next(n for n in zf.namelist() if n.endswith(".geojson"))
        bruto = json.loads(zf.read(nome))
    feicoes, nomes = [], {}
    for f in bruto["features"]:
        chave = correcoes.normalizar(f["properties"]["EBAIRRNOME"])
        chave = correcoes.APELIDOS_BAIRRO.get(chave, chave)
        nomes[chave] = f["properties"]["EBAIRRNOMEOF"]
        geometria = shape(f["geometry"]).simplify(tolerancia, preserve_topology=True)
        geo = json.loads(json.dumps(mapping(geometria)), parse_float=lambda x: round(float(x), 5))
        feicoes.append({"type": "Feature", "properties": {"bairro_oficial": chave, "nome": nomes[chave]},
                        "geometry": geo})
    return {"type": "FeatureCollection", "features": feicoes}, nomes


def main() -> None:
    inicio = time.time()
    SAIDA.mkdir(parents=True, exist_ok=True)
    print("lendo o dataset...")
    df, log = aplicar_correcoes(ler_dataset(DATASET))

    geo, nomes = malha_simplificada(MALHA)
    (SAIDA / "bairros.geojson").write_text(json.dumps(geo, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    bairros = agregados.tabela_bairros(df, nomes)
    estoque = agregados.estoque_156(df, DATA_REFERENCIA)
    tabelas = {
        "bairros": bairros,
        "demanda": agregados.demanda(df),
        "prazos_156": agregados.prazos_156(df),
        "reincidencia_156": agregados.reincidencia_156(df),
        "locais_cronicos_156": agregados.locais_cronicos(df),
        "camara_indicacoes": agregados.camara_indicacoes(df),
        "ouvidoria": agregados.ouvidoria(df),
        "estoque_156": estoque,
        "indicadores_bairro": agregados.indicadores_bairro(df, bairros, estoque),
    }
    for nome, tabela in tabelas.items():
        tabela.to_parquet(SAIDA / f"{nome}.parquet", index=False)
        print(f"{nome:22s} {len(tabela):>9,} linhas")

    resumo = {
        "gerado_em": pd.Timestamp.now().strftime("%Y-%m-%d"),
        "linhas_no_dataset": len(df),
        "data_referencia_estoque": DATA_REFERENCIA.strftime("%Y-%m-%d"),
        "correcoes": log,
    }
    (SAIDA / "resumo_preparacao.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    for k, v in log.items():
        print(f"{k:55s} {v:>9,}")
    print(f"pronto em {time.time() - inicio:.0f} s")


if __name__ == "__main__":
    main()
