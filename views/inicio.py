"""Achados: a narrativa do painel. O que a análise mostrou, com o número de cada achado e o caminho para a página
que o detalha. Os números respeitam os filtros da barra lateral."""

import altair as alt
import pandas as pd
import streamlit as st

from src import filtros, metricas
from src.componentes import fontes
from src.config import ESCALA_FONTE, eixo_numero, rotulo_fonte
from src.dados import tabela

# Anos em que a fonte publicou só parte dos registros: aparecem tracejados e com ponto vazado no gráfico.
ANOS_PARCIAIS = {("OUVIDORIA", 2025): "a Ouvidoria de 2025 só traz parte do ano",
                 ("SEDEC_CHAMADOS", 2024): "a cópia da SEDEC é de março de 2024",
                 ("156_EMLURB", 2026): "2026 vai até o download, em 07/10/2026"}
TODAS = ["156_EMLURB", "DEFESA_CIVIL", "OUVIDORIA", "SEDEC_CHAMADOS", "CAMARA_REQUERIMENTOS"]

f = filtros.atuais()


def achado(coluna, pergunta: str, frase: str, pagina: str, rotulo: str, icone: str) -> None:
    """Cartão de achado: a pergunta, a frase com o número e, no rodapé, o link para a página que o detalha.
    O texto vai em st.html: o st.markdown come 1rem do fim do bloco e o link colava no texto."""
    with coluna.container(border=True, height="stretch", gap="small"):
        st.html(f"<div style='font-size:.8rem;opacity:.7;margin-bottom:4px'>{pergunta}</div>"
                f"<div style='font-size:1.02rem;line-height:1.45'>{frase}</div>")
        st.space("stretch")
        st.page_link(pagina, label=rotulo, icon=icone, width="content")


st.title("Achados")
st.markdown("#### A porta de entrada funciona. A perda está depois dela.")
st.markdown("Demandas chegam à Prefeitura por cinco portas. O que falha é o caminho de volta: pouca coisa retorna com "
            "resposta registrada, o mesmo problema volta ao mesmo lugar e uma parte dos pedidos fica meses na fila. "
            "Cada achado abaixo leva à página que o detalha; o [Painel Geral](/) mostra o estado de hoje.")
filtros.legenda(f, aplicacao={"RPA": "aplica (a Ouvidoria sai)", "Bairro": "aplica (a Ouvidoria sai)",
                                     "Categoria": "só 156 e Câmara"})
fontes(TODAS)

# --- Os números de cada achado (com os filtros) -----------------------------------------------------------
demanda = tabela("demanda")
d = f.aplicar(demanda, categoria=False)
if f.categorias:
    d = d[d["fonte"].isin(["156_EMLURB", "CAMARA_REQUERIMENTOS"]) & d["categoria"].isin(f.categorias)]
if f.territorio_ativo:
    d = d[d["bairro_oficial"].notna() | d["rpa"].notna()]
d = d[~((d["fonte"] == "DEFESA_CIVIL") & (d["iniciativa"] != "CIDADAO"))]   # só a demanda do cidadão

ind = f.aplicar(tabela("camara_indicacoes"))
rep = f.aplicar(tabela("reincidencia_156"))
praz = f.aplicar(tabela("prazos_156"))
ouv = f.aplicar(tabela("ouvidoria"), territorio=False, categoria=False)
estoque = f.aplicar(tabela("estoque_156"), ano=False)
bairros_ind = tabela("indicadores_bairro")
if f.territorio_ativo:
    bairros_ind = f.aplicar(bairros_ind, ano=False, categoria=False)

num, pct = metricas.numero, metricas.porcentagem
ouv_app = ouv[ouv["ano"] >= 2023]
app = ouv_app.loc[ouv_app["canal_entrada"] == "APP CONECTA RECIFE", "n"].sum() / ouv_app["n"].sum() * 100 \
    if ouv_app["n"].sum() else None
enviadas = ind["enviada"].mean() * 100 if len(ind) else None
respondidas = ind["respondida"].mean() * 100 if len(ind) else None
repetidos = rep["repetidos"].sum() / rep["registros"].sum() * 100 if rep["registros"].sum() else None
p90 = metricas.quantil_ponderado(praz["dias"], praz["n"], 0.9)
mediana = metricas.quantil_ponderado(praz["dias"], praz["n"], 0.5)
anos_praz = sorted(a for a in praz["ano"].unique() if a <= 2025)
p90_por_ano = {a: metricas.quantil_ponderado(g["dias"], g["n"], 0.9) for a, g in praz.groupby("ano") if a in anos_praz}
abertos, atrasados = estoque["abertos"].sum(), estoque["acima_prazo_tipico"].sum()
lider_156 = bairros_ind.nlargest(1, "taxa_156")["nome"].tolist()
lider_dc = bairros_ind.nlargest(1, "taxa_defesa_civil")["nome"].tolist()


def ou_traco(valor: str | None) -> str:
    return valor if valor not in (None, "—") else "sem dado no recorte"


st.space("xxsmall")
l1 = st.columns(3, gap="medium")
achado(l1[0], "A porta de entrada",
       f"O app Conecta Recife é <b>{ou_traco(pct(app))}</b> das manifestações da Ouvidoria desde 2023; o telefone "
       "e o site dominam. E quase toda indicação de vereador chega à Prefeitura: "
       f"<b>{ou_traco(pct(enviadas))}</b> são enviadas.",
       "views/retorno.py", "Ver em Retorno", ":material/call_split:")
achado(l1[1], "O caminho de volta",
       f"Só <b>{ou_traco(pct(respondidas))}</b> das indicações da Câmara voltam com resposta registrada "
       f"(de {num(len(ind))} no recorte). O pedido chega, mas a resposta não aparece.",
       "views/retorno.py", "Ver em Retorno", ":material/call_split:")
achado(l1[2], "O problema volta",
       f"<b>{ou_traco(pct(repetidos))}</b> dos pedidos do 156 caem num local + serviço que já teve pedido. "
       "Não é só pedido em dobro: o mesmo problema volta ao mesmo endereço.",
       "views/reincidencia.py", "Ver em Reincidência", ":material/repeat:")
st.space("xxsmall")
l2 = st.columns(3, gap="medium")
tendencia = ""
if len(p90_por_ano) >= 2:
    primeiro, ultimo = min(p90_por_ano), max(p90_por_ano)
    tendencia = (f" O p90 foi de {metricas.dias(p90_por_ano[primeiro])} em {primeiro} para "
                 f"{metricas.dias(p90_por_ano[ultimo])} em {ultimo}.")
achado(l2[0], "A cauda da fila",
       f"Metade dos pedidos do 156 é atendida em <b>{metricas.dias(mediana)}</b>, mas 1 em cada 10 leva mais de "
       f"<b>{metricas.dias(p90)}</b>.{tendencia}",
       "views/prazos.py", "Ver em Prazos", ":material/schedule:")
achado(l2[1], "O estoque parado",
       f"<b>{num(abertos)}</b> pedidos seguem abertos nos arquivos mais recentes do 156, e <b>{pct(atrasados / abertos * 100) if abertos else '—'}</b> "
       "já passaram do prazo típico da categoria.",
       "views/prioridade.py", "Ver em Prioridade", ":material/low_priority:")
achado(l2[2], "O território",
       ("Serviço urbano e emergência apontam para bairros diferentes: por habitante, "
        f"<b>{lider_156[0]}</b> lidera no 156 e <b>{lider_dc[0]}</b> na Defesa Civil.")
       if lider_156 and lider_dc else "Sem bairros com população suficiente no recorte.",
       "views/territorio.py", "Ver em Território", ":material/map:")

# --- Volume por fonte -------------------------------------------------------------------------------
st.space("small")
st.subheader("Quanto Chega por Cada Porta",
             help="Registros por ano em cada fonte. Clique numa fonte da legenda para destacá-la. Linha tracejada e "
                  "ponto vazado: ano em que a fonte publicou só parte dos registros.")
serie = d.groupby(["ano", "fonte"], as_index=False)["n"].sum()
serie["fonte_nome"] = serie["fonte"].map(rotulo_fonte)
serie["registros"] = serie["n"].map(num)
serie["parcial"] = [(fo, a) in ANOS_PARCIAIS for fo, a in zip(serie["fonte"], serie["ano"])]
serie["situacao"] = [ANOS_PARCIAIS.get((fo, a), "ano completo") for fo, a in zip(serie["fonte"], serie["ano"])]
if serie.empty:
    st.info("Nenhum registro para os filtros escolhidos.")
else:
    # Trecho tracejado: do último ano completo até o ano parcial, só nas fontes que têm ano parcial.
    ponte = []
    for (fonte, ano), _ in ANOS_PARCIAIS.items():
        anterior = serie[(serie["fonte"] == fonte) & (serie["ano"] == ano - 1)]
        parcial = serie[(serie["fonte"] == fonte) & (serie["ano"] == ano)]
        if not anterior.empty and not parcial.empty:
            ponte.append(pd.concat([anterior, parcial]).assign(trecho=f"{fonte}-{ano}"))
    clique = alt.selection_point(fields=["fonte_nome"], bind="legend")
    cor = alt.Color("fonte_nome:N", title="Fonte", scale=ESCALA_FONTE,
                    legend=alt.Legend(orient="bottom", columns=3, labelLimit=320))
    opacidade = alt.condition(clique, alt.value(1), alt.value(0.15))
    dica = [alt.Tooltip("fonte_nome:N", title="Fonte"), alt.Tooltip("ano:O", title="Ano"),
            alt.Tooltip("registros:N", title="Registros"), alt.Tooltip("situacao:N", title="Situação")]
    x = alt.X("ano:O", title=None, axis=alt.Axis(labelAngle=0))
    y = alt.Y("n:Q", axis=eixo_numero("registros por ano"))
    cheia = alt.Chart(serie[~serie["parcial"]]).mark_line().encode(x=x, y=y, color=cor, opacity=opacidade)
    camadas = [cheia]
    if ponte:
        camadas.append(alt.Chart(pd.concat(ponte)).mark_line(strokeDash=[5, 4]).encode(
            x=x, y=y, color=cor, detail="trecho:N", opacity=opacidade))
    camadas.append(alt.Chart(serie[~serie["parcial"]]).mark_point(size=55, filled=True).encode(
        x=x, y=y, color=cor, opacity=opacidade, tooltip=dica))
    camadas.append(alt.Chart(serie[serie["parcial"]]).mark_point(size=70, filled=False, strokeWidth=2).encode(
        x=x, y=y, color=cor, opacity=opacidade, tooltip=dica))
    st.altair_chart(alt.layer(*camadas).add_params(clique).properties(height=320), width="stretch")
    notas = ["Clique numa fonte da legenda para destacá-la. Tracejado e ponto vazado: ano parcial "
             "(Ouvidoria 2025, SEDEC 2024, 156 em 2026)."]
    if f.territorio_ativo:
        notas.append("Com filtro de território, a Ouvidoria sai do gráfico: a fonte não publica o bairro.")
    if f.categorias:
        notas.append("Com filtro de categoria, só o 156 e a Câmara ficam: as outras fontes usam outra classificação.")
    notas.append("A Defesa Civil mostra só ações pedidas pelo cidadão e não publicou 2025.")
    st.caption(" ".join(notas))
