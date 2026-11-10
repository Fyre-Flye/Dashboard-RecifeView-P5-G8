"""Índice de prioridade por bairro com AHP (Analytic Hierarchy Process, Saaty).

Sugestão da Profª Maíra (19/10): usar o AHP para priorizar, no lugar de um classificador complexo,
e mostrar o resultado num mapa do Recife. Os critérios saem da EDA (N3, seção 8.2).

Como funciona, em três passos:
1. Quem decide compara os critérios dois a dois, na escala de 1 a 9 de Saaty.
2. Os pesos são o autovetor principal da matriz de comparações; a razão de consistência (RC)
   diz se os julgamentos são coerentes entre si (RC ≤ 0,10).
3. Cada bairro recebe uma nota de 0 a 1 em cada critério (posição relativa entre os bairros)
   e o índice é a soma ponderada, de 0 a 10 (escala de nota, mais fácil de ler para gestores).

Os julgamentos padrão abaixo são uma proposta inicial do grupo para discussão. NÃO foram validados
por especialistas da Prefeitura; o painel deixa qualquer pessoa refazê-los.
"""

from dataclasses import dataclass
from itertools import combinations

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Criterio:
    chave: str
    nome: str
    coluna: str          # coluna de indicadores_bairro.parquet
    unidade: str
    descricao: str
    nota_bairro: str     # como o indicador vira nota de 0 a 1 no índice dos bairros
    nota_pedido: str     # como vira nota de 0 a 1 na classificação de um pedido aberto


CRITERIOS = [
    Criterio("risco", "Risco", "taxa_defesa_civil", "ações / mil hab. / ano",
             "Demanda do cidadão à Defesa Civil (vistoria, lona) por habitante, 2021–2024. "
             "Mede exposição a risco em encostas e áreas alagáveis.",
             "Posição relativa da taxa entre os bairros: r = posição ÷ N.",
             "Herda a nota do bairro do pedido."),
    Criterio("vulnerabilidade", "Vulnerabilidade", "pct_favela", "% da população",
             "Parcela da população do bairro em favelas e comunidades urbanas (Censo 2022). "
             "O mesmo problema pesa mais onde a capacidade de se recuperar é menor, e o volume de pedidos não mostra isso.",
             "Posição relativa do percentual entre os bairros: r = posição ÷ N.",
             "Herda a nota do bairro do pedido."),
    Criterio("atraso", "Atraso", "pct_atraso_156", "% do estoque aberto",
             "Parcela dos pedidos do 156 ainda abertos (arquivos 2025–2026) que já passaram do prazo "
             "típico da categoria (p90 dos atendidos de 2021–2025).",
             "Posição relativa do percentual entre os bairros: r = posição ÷ N.",
             "Idade do pedido ÷ prazo típico da categoria, limitado a 2 e dividido por 2: "
             "0,5 = chegou ao prazo típico; 1 = o dobro do prazo ou mais. Na Câmara, o prazo típico é o p90 "
             "dos dias até a resposta no mesmo tema."),
    Criterio("reincidencia", "Reincidência", "pct_reincidencia_156", "% dos pedidos",
             "Parcela dos pedidos do 156 (2021–2025, com número no endereço) que caem num local + serviço "
             "que se repete. O problema que volta pesa mais que o problema novo.",
             "Posição relativa do percentual entre os bairros: r = posição ÷ N.",
             "Pedidos anteriores no mesmo endereço e serviço, em escala logarítmica: ln(1 + m) ÷ ln(11). "
             "1 anterior ≈ 0,29; 3 ≈ 0,58; 10 ou mais = 1. Sem número no endereço: 0. Na Câmara, m são as "
             "indicações do mesmo tema no bairro nos 90 dias antes."),
]

# Escala de Saaty: o valor diz quantas vezes o primeiro critério é mais importante que o segundo.
ESCALA = {1: "igual importância", 2: "entre igual e moderada", 3: "moderadamente mais importante",
          4: "entre moderada e forte", 5: "fortemente mais importante", 6: "entre forte e muito forte",
          7: "muito mais importante", 8: "entre muito forte e extrema", 9: "extremamente mais importante"}

# Proposta inicial (para discussão com a Maíra, o Marcelo e, se possível, a Defesa Civil/Emlurb).
# Valor > 1: o primeiro critério do par pesa mais; valor < 1: o segundo pesa mais.
JULGAMENTOS_PADRAO = {
    ("risco", "vulnerabilidade"): 2,
    ("risco", "atraso"): 3,
    ("risco", "reincidencia"): 3,
    ("vulnerabilidade", "atraso"): 2,
    ("vulnerabilidade", "reincidencia"): 2,
    ("atraso", "reincidencia"): 1,
}

# Índice aleatório de Saaty (consistência de matrizes preenchidas ao acaso), por tamanho da matriz.
INDICE_ALEATORIO = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45}
RC_ACEITAVEL = 0.10
NOTA_MAXIMA = 10        # o índice vai de 0 a 10

# Classificação de um pedido (exemplo na página de Prioridade): onde as notas de atraso e reincidência chegam ao máximo.
ATRASO_TETO = 2.0             # aberto há o dobro do prazo típico da categoria, ou mais
REINCIDENCIA_TETO = 10        # 10 pedidos anteriores no mesmo endereço e serviço, ou mais


def pares(chaves: list[str]) -> list[tuple[str, str]]:
    return list(combinations(chaves, 2))


def matriz_de_comparacao(julgamentos: dict[tuple[str, str], float], chaves: list[str]) -> np.ndarray:
    """Matriz recíproca: a[i, j] = julgamento(i, j) e a[j, i] = 1 / a[i, j]."""
    pos = {c: i for i, c in enumerate(chaves)}
    m = np.ones((len(chaves), len(chaves)))
    for (a, b), valor in julgamentos.items():
        m[pos[a], pos[b]] = valor
        m[pos[b], pos[a]] = 1 / valor
    return m


def _autovalor_e_vetor(m: np.ndarray) -> tuple[float, np.ndarray]:
    valores, vetores = np.linalg.eig(m)
    i = int(np.argmax(valores.real))
    return float(valores[i].real), np.abs(vetores[:, i].real)


def pesos(m: np.ndarray) -> np.ndarray:
    _, v = _autovalor_e_vetor(m)
    return v / v.sum()


def razao_consistencia(m: np.ndarray) -> float:
    n = m.shape[0]
    if n <= 2:
        return 0.0
    lambda_max, _ = _autovalor_e_vetor(m)
    indice_consistencia = (lambda_max - n) / (n - 1)
    return max(indice_consistencia / INDICE_ALEATORIO[n], 0.0)


def notas_por_criterio(indicadores: pd.DataFrame, criterios=CRITERIOS) -> pd.DataFrame:
    """Nota de 0 a 1 de cada bairro em cada critério: a posição relativa (percentil) entre os bairros.

    Usar a posição, e não o valor bruto, evita que poucos bairros extremos (a Defesa Civil vai de 0,1 a
    119 ações por mil habitantes) achatem todos os outros. Bairro sem dado no critério recebe 0.
    """
    notas = pd.DataFrame(index=indicadores.index)
    for c in criterios:
        notas[c.chave] = indicadores[c.coluna].rank(pct=True, method="average").fillna(0.0)
    return notas


def indice_prioridade(indicadores: pd.DataFrame, w: dict[str, float], criterios=CRITERIOS) -> pd.DataFrame:
    """Índice de 0 a 10 e a contribuição de cada critério (pontos do índice)."""
    notas = notas_por_criterio(indicadores, criterios)
    contrib = pd.DataFrame({c.chave: notas[c.chave] * w[c.chave] * NOTA_MAXIMA for c in criterios})
    resultado = indicadores.copy()
    resultado["indice"] = contrib.sum(axis=1)
    for c in criterios:
        resultado[f"contrib_{c.chave}"] = contrib[c.chave]
    resultado["posicao"] = resultado["indice"].rank(ascending=False, method="min").astype(int)
    return resultado.sort_values("indice", ascending=False)


def sensibilidade(indicadores: pd.DataFrame, w: dict[str, float], top: int = 10,
                  fatores=(0.5, 0.75, 1.25, 1.5), criterios=CRITERIOS) -> pd.DataFrame:
    """Quantos bairros do top N continuam no top N quando o peso de um critério muda.

    Cada linha multiplica o peso de um critério por um fator e renormaliza os outros para somar 1.
    """
    base = set(indice_prioridade(indicadores, w, criterios).head(top).index)
    linhas = []
    for c in criterios:
        for f in fatores:
            novo = dict(w)
            novo[c.chave] = w[c.chave] * f
            soma = sum(novo.values())
            novo = {k: v / soma for k, v in novo.items()}
            topo = set(indice_prioridade(indicadores, novo, criterios).head(top).index)
            linhas.append({"criterio": c.nome, "fator": f, "peso_testado": novo[c.chave],
                           "mantidos_no_top": len(base & topo)})
    return pd.DataFrame(linhas)


def notas_ocorrencias(ocorrencias: pd.DataFrame, indicadores: pd.DataFrame) -> pd.DataFrame:
    """Nota de 0 a 1 de cada pedido aberto em cada critério (exemplo de classificação).

    - Risco e vulnerabilidade são do lugar: o pedido herda a nota do seu bairro.
    - Atraso é do pedido: idade ÷ prazo típico da categoria, com teto no dobro do prazo
      (0,5 = chegou ao prazo típico; 1 = dobro do prazo ou mais). Sem prazo típico: 0.
    - Reincidência é do pedido: pedidos anteriores no mesmo endereço e serviço, em escala log
      (1 anterior ≈ 0,29; 3 ≈ 0,58; 10 ou mais = 1). Sem número no endereço: 0, porque não dá para saber.
    """
    lugar = notas_por_criterio(indicadores)
    bairro = ocorrencias["bairro_oficial"]
    proporcao = (ocorrencias["idade_dias"] / ocorrencias["prazo_tipico_dias"]).astype(float)
    anteriores = ocorrencias["pedidos_anteriores"].astype(float)
    return pd.DataFrame({
        "risco": bairro.map(lugar["risco"]).astype(float),
        "vulnerabilidade": bairro.map(lugar["vulnerabilidade"]).astype(float),
        "atraso": (proporcao.clip(0, ATRASO_TETO) / ATRASO_TETO).fillna(0.0),
        "reincidencia": (np.log1p(anteriores) / np.log1p(REINCIDENCIA_TETO)).clip(0, 1).fillna(0.0),
    }, index=ocorrencias.index)


def indice_ocorrencias(ocorrencias: pd.DataFrame, indicadores: pd.DataFrame, w: dict[str, float],
                       criterios=CRITERIOS) -> pd.DataFrame:
    """Nota de prioridade de 0 a 10 de cada pedido aberto, com os mesmos pesos do índice dos bairros.

    Pedidos de bairros fora do índice (menos de 1.000 moradores) ficam de fora. `percentil` diz quantos
    por cento dos pedidos classificados têm nota menor ou igual.
    """
    dentro = ocorrencias[ocorrencias["bairro_oficial"].isin(indicadores.index)]
    notas = notas_ocorrencias(dentro, indicadores)
    resultado = dentro.copy()
    for c in criterios:
        resultado[f"nota_{c.chave}"] = notas[c.chave] * NOTA_MAXIMA
        resultado[f"contrib_{c.chave}"] = notas[c.chave] * w[c.chave] * NOTA_MAXIMA
    resultado["indice"] = resultado[[f"contrib_{c.chave}" for c in criterios]].sum(axis=1)
    resultado["percentil"] = resultado["indice"].rank(pct=True, method="max") * 100
    return resultado.sort_values("indice", ascending=False)


def indice_so_atraso(registros: pd.DataFrame, coluna: str = "dias_alem_do_prazo", criterios=CRITERIOS) -> pd.DataFrame:
    """Nota de 0 a 10 quando só o atraso pode ser medido (Ouvidoria: a base aberta não tem lugar).

    Todas as manifestações abertas já passaram do prazo legal, então uma escala fixa daria 10 a todas.
    A nota é a posição relativa dos dias além do prazo entre as abertas: 10 = a mais atrasada.
    Os outros critérios ficam vazios e não somam pontos; a nota não é comparável com a das outras fontes.
    """
    resultado = registros.copy()
    nota = resultado[coluna].astype(float).rank(pct=True, method="average") * NOTA_MAXIMA
    for c in criterios:
        resultado[f"nota_{c.chave}"] = nota if c.chave == "atraso" else np.nan
        resultado[f"contrib_{c.chave}"] = nota if c.chave == "atraso" else 0.0
    resultado["indice"] = nota
    resultado["percentil"] = resultado["indice"].rank(pct=True, method="max") * 100
    return resultado.sort_values("indice", ascending=False)
