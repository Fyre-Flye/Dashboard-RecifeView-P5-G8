import random

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from src import ahp, ajuda, filtros, metricas
from src.componentes import fontes, kpi, leitura
from src.config import (AZUL25, DESTAQUE, RAMPA, SEM_DADO, TEXTO_TEMA, cor_fundo, cor_suave, eixo_numero,
                        nome_categoria, nome_orgao)
from src.dados import malha, resumo_preparacao, tabela

f = filtros.atuais()
CRIT = {c.chave: c for c in ahp.CRITERIOS}
CHAVES = list(CRIT)
# As cores seguem a origem do critério: risco vem da Defesa Civil (laranja); atraso e reincidência, do 156.
CORES = {"risco": DESTAQUE, "vulnerabilidade": "#9A3FB8", "atraso": "#0F62FE", "reincidencia": "#1B998B"}

st.title("Prioridade (AHP)")
st.markdown("Onde agir primeiro, com **critérios explícitos e ajustáveis**. O índice combina quatro critérios que "
            "saíram da EDA, com pesos obtidos pelo AHP (Analytic Hierarchy Process): quem decide compara os critérios "
            "dois a dois, e o método calcula os pesos e confere se os julgamentos são coerentes.")
st.info("Os julgamentos que vêm carregados são uma **proposta inicial do grupo para discussão**, não pesos validados "
        "pela Prefeitura. O próximo passo é refazer as comparações com a Profª Maíra, o Prof. Marcelo e, se possível, "
        "quem opera a Defesa Civil e a Emlurb. Você pode refazê-las abaixo e ver o mapa mudar.", icon=":material/info:")
filtros.legenda(f, {"Período": "fixo em 2021–2025 (estoque aberto: arquivos 2025–2026), como na EDA.",
                    "Território": "RPA e bairro destacam o mapa e filtram a lista; a posição é sempre na cidade toda.",
                    "Categoria": "vale só para os pedidos da seção 4."})
fontes(['156_EMLURB', 'DEFESA_CIVIL', 'CAMARA_REQUERIMENTOS', 'OUVIDORIA'])

# --- Critérios ----------------------------------------------------------------------------------------
st.subheader("Os Quatro Critérios e Como Cada Um É Medido",
             help="O que entra no índice de prioridade, de onde vem cada número e por que ele importa.")
st.table(pd.DataFrame([{"Critério": c.nome, "Indicador": c.unidade, "O que mede e por quê": c.descricao,
                        "Como vira nota (0 a 1): bairro": c.nota_bairro,
                        "Como vira nota (0 a 1): pedido": c.nota_pedido}
                       for c in ahp.CRITERIOS]).set_index("Critério"))
leitura("No índice dos bairros, cada critério vira a posição relativa do bairro entre os 89 bairros com 1.000 moradores "
        "ou mais (perto de 0 = menor valor, 1 = maior; bairro sem dado = 0). Usar a posição, e não o valor bruto, evita "
        "que poucos bairros extremos achatem os outros. Na classificação de um pedido (seção 4), risco e vulnerabilidade "
        "vêm do bairro, e atraso e reincidência são medidos no próprio pedido. Os pesos saem das comparações abaixo. "
        "A fórmula completa, com um exemplo de cálculo, está na seção 6, no fim da página.")


# --- Comparações par a par ----------------------------------------------------------------------------
OPCOES = [-9, -8, -7, -6, -5, -4, -3, -2, 1, 2, 3, 4, 5, 6, 7, 8, 9]


def chave_estado(a: str, b: str) -> str:
    return f"ahp_{a}_{b}"


def para_opcao(valor: float) -> int:
    return int(round(valor)) if valor >= 1 else -int(round(1 / valor))


def para_valor(opcao: int) -> float:
    return float(opcao) if opcao > 0 else 1 / -opcao


def restaurar_julgamentos() -> None:
    """Callback do botão: roda antes dos sliders serem desenhados, então pode trocar o valor deles.

    Alterar o estado de um widget depois de ele existir na página dá StreamlitAPIException.
    """
    for (a, b), v in ahp.JULGAMENTOS_PADRAO.items():
        st.session_state[chave_estado(a, b)] = para_opcao(v)


for (a, b), v in ahp.JULGAMENTOS_PADRAO.items():
    st.session_state.setdefault(chave_estado(a, b), para_opcao(v))

c1, c2 = st.columns([1.15, 1], gap="large")
with c1:
    st.subheader("1. Compare os Critérios Dois a Dois",
                 help="Para cada par, arraste para o critério que pesa mais. O número diz quantas vezes mais.")
    st.caption("Para cada par, quanto um critério é mais importante que o outro para decidir onde agir primeiro "
               "(escala de Saaty: 1 = igual, 3 = moderadamente, 5 = fortemente, 7 = muito, 9 = extremamente).")
    julgamentos = {}
    for a, b in ahp.pares(CHAVES):
        na, nb = CRIT[a].nome, CRIT[b].nome

        def rotulo(o, na=na, nb=nb):
            if o == 1:
                return "igual importância"
            return f"{na} {o}× mais" if o > 0 else f"{nb} {-o}× mais"

        op = st.select_slider(f"{na} × {nb}", OPCOES, key=chave_estado(a, b), format_func=rotulo,
                              help=f"Para a esquerda, {nb} pesa mais; para a direita, {na}. No meio, os dois valem igual.")
        julgamentos[(a, b)] = para_valor(op)
    st.button("Voltar à proposta inicial do grupo", icon=":material/restart_alt:", on_click=restaurar_julgamentos,
              help="Desfaz as suas comparações e volta aos julgamentos propostos pelo grupo.")

m = ahp.matriz_de_comparacao(julgamentos, CHAVES)
w = dict(zip(CHAVES, ahp.pesos(m)))
rc = ahp.razao_consistencia(m)

with c2:
    st.subheader("2. Pesos Resultantes",
                 help="Quanto cada critério vale no índice, calculado pelo AHP a partir das comparações ao lado.")
    pesos = pd.DataFrame({"criterio": [CRIT[k].nome for k in CHAVES], "chave": CHAVES, "peso": [w[k] * 100 for k in CHAVES]})
    pesos["rotulo"] = pesos["peso"].map(lambda v: metricas.porcentagem(v, 1))
    base = alt.Chart(pesos).encode(
        y=alt.Y("criterio:N", sort=pesos.sort_values("peso", ascending=False)["criterio"].tolist(), title=None,
                axis=alt.Axis(labelOverlap=False)),
        x=alt.X("peso:Q", title="peso (%)", scale=alt.Scale(domain=[0, max(70, pesos["peso"].max() + 10)])),
        tooltip=[alt.Tooltip("criterio:N", title="Critério"), alt.Tooltip("rotulo:N", title="Peso")],
    )
    st.altair_chart((base.mark_bar().encode(color=alt.Color(
        "chave:N", scale=alt.Scale(domain=list(CORES), range=list(CORES.values())), legend=None))
        + base.mark_text(align="left", dx=4, color=TEXTO_TEMA).encode(text="rotulo:N")).properties(height=alt.Step(34)),
        width="stretch")
    ok = rc <= ahp.RC_ACEITAVEL
    kpi(st, "Razão de consistência (RC)", metricas.porcentagem(rc * 100, 1),
        "julgamentos coerentes (RC ≤ 10%)" if ok else "incoerente: revise as comparações",
        "Compara a coerência dos julgamentos com a de comparações feitas ao acaso. Se A > B e B > C, então A deve "
        "ser > C. Acima de 10%, os pesos não devem ser usados.")
    if not ok:
        st.warning("RC acima de 10%: algum julgamento contradiz os outros. O mapa abaixo usa estes pesos mesmo assim, "
                   "só para você ver o efeito.", icon=":material/warning:")

# --- Índice ---------------------------------------------------------------------------------------------
ind = tabela("indicadores_bairro").set_index("bairro_oficial")
r = ahp.indice_prioridade(ind, w)
r["destaque"] = True
if f.rpas:
    r["destaque"] &= r["rpa"].isin(f.rpas)
if f.bairros:
    r["destaque"] &= r.index.isin(f.bairros)
r["indice_txt"] = r["indice"].map(lambda v: metricas.numero(v, 1))
for k in CHAVES:
    r[f"{k}_txt"] = r[CRIT[k].coluna].map(lambda v: metricas.numero(v, 1))

# --- Exemplo de ocorrências classificadas ----------------------------------------------------------------
SITUACAO = {"CADASTRADA": "cadastrado", "PREPARACAO": "em preparação", "EXECUCAO": "em execução",
            "PENDENCIA": "com pendência", "FISCALIZACAO": "em fiscalização", "MONITORAMENTO": "em monitoramento"}
SORTEIO = "sorteio_ocorrencias"
CANAL_ENVIO = {"OFICIO": "ofício", "PROTOCOLO NA PREFEITURA": "protocolo na Prefeitura",
               "LOTE JSON SISTEMA PCR": "lote do sistema da Prefeitura", "SISTEMA SEGOV": "sistema da SEGOV",
               "ENVIADO AO EXECUTIVO": "envio ao Executivo", "E-MAIL": "e-mail",
               "CIENCIA AOS INTERESSADOS": "ciência aos interessados"}
NOTA_ALTA = 7
CORES_SORTEIO = ["#D7263D", "#FFB000", "#7CB518"]      # 1º, 2º e 3º sorteados: cartão e cruz no mapa
F156, CAMARA, OUVIDORIA = "Central 156 / Emlurb", "Indicações da Câmara", "Ouvidoria"
FONTES_EXEMPLO = {
    F156: {"tabela": "ocorrencias_abertas_156", "registro": "pedidos abertos", "genero": "o",
           "explica": "**pedidos abertos do 156**: risco e vulnerabilidade vêm do bairro do pedido; atraso e "
                      "reincidência vêm do próprio pedido."},
    CAMARA: {"tabela": "indicacoes_sem_resposta", "registro": "indicações sem resposta", "genero": "a",
             "explica": "**indicações de vereadores enviadas à Prefeitura e ainda sem resposta registrada**, o retrato "
                        "da fragmentação: risco e vulnerabilidade vêm do bairro; o atraso conta desde o envio, contra o "
                        "tempo típico de resposta do tema; a reincidência são outras indicações do mesmo tema no mesmo "
                        "bairro nos 90 dias anteriores (a Câmara não tem endereço)."},
    OUVIDORIA: {"tabela": "manifestacoes_abertas_ouvidoria", "registro": "manifestações abertas", "genero": "a",
                "explica": "**manifestações abertas na Ouvidoria** (inclui o app Conecta Recife). A base aberta da "
                           "Ouvidoria **não tem bairro, endereço nem coordenadas**, então risco, vulnerabilidade e "
                           "reincidência não se aplicam: a nota usa só o atraso em relação ao prazo legal e **não é "
                           "comparável** com a das outras fontes."},
}


def sortear() -> None:
    st.session_state[SORTEIO] = random.randrange(1_000_000)


def data_br(v) -> str:
    return f"{v:%d/%m/%Y}" if pd.notna(v) else "—"


def classificar(fonte: str) -> pd.DataFrame:
    base = tabela(FONTES_EXEMPLO[fonte]["tabela"])
    if fonte == OUVIDORIA:
        return ahp.indice_so_atraso(base)
    r = ahp.indice_ocorrencias(f.aplicar(base, ano=False), ind, w)
    r["nome"] = r["bairro_oficial"].map(ind["nome"])
    return r


def textos(linha: pd.Series, fonte: str) -> tuple[str, str, str, str]:
    """Título, contexto, tempo e repetição de um registro, para o cartão."""
    n = linha.get("pedidos_anteriores")
    if fonte == F156:
        vezes = linha["idade_dias"] / linha["prazo_tipico_dias"] if linha["prazo_tipico_dias"] else np.nan
        prazo = (f"prazo típico da categoria: {metricas.numero(linha['prazo_tipico_dias'])} dias "
                 f"({metricas.numero(vezes, 1)}× o prazo)") if pd.notna(vezes) else "categoria sem prazo típico"
        if pd.isna(n):
            rep = "Endereço sem número: não dá para saber se o problema se repete."
        elif n == 0:
            rep = "Primeiro pedido deste serviço no endereço."
        else:
            rep = f"O endereço já teve <b>{metricas.numero(n)}</b> pedido{'s' if n > 1 else ''} do mesmo serviço antes deste."
        return (nome_categoria(linha["servico"]),
                f"{nome_categoria(linha['categoria'])} · {linha['nome']} (RPA {linha['rpa']}) · "
                f"{SITUACAO.get(linha['situacao'], str(linha['situacao']).lower())}",
                f"Aberto em {data_br(linha['data_abertura'])}, há {metricas.numero(linha['idade_dias'])} dias; {prazo}.", rep)
    if fonte == CAMARA:
        vezes = linha["idade_dias"] / linha["prazo_tipico_dias"]
        rep = ("Nenhuma outra indicação do mesmo tema no bairro nos 90 dias anteriores." if n == 0 else
               f"<b>{metricas.numero(n)}</b> outra{'s' if n > 1 else ''} indicaç{'ões' if n > 1 else 'ão'} do mesmo tema "
               f"no bairro nos 90 dias anteriores.")
        return (f"Indicação: {nome_categoria(linha['categoria']).lower()}",
                f"{linha['nome']} (RPA {linha['rpa']}) · enviada a {nome_orgao(linha['orgao'])} "
                f"por {CANAL_ENVIO.get(linha['canal_envio'], str(linha['canal_envio']).lower())}",
                f"Apresentada em {data_br(linha['data_abertura'])}, enviada em {data_br(linha['data_envio'])}: há "
                f"{metricas.numero(linha['idade_dias'])} dias sem resposta; tempo típico até a resposta no tema: "
                f"{metricas.numero(linha['prazo_tipico_dias'])} dias ({metricas.numero(vezes, 1)}×).", rep)
    canal = linha["canal_entrada"]
    canal = f"canal {str(canal).lower()}" if pd.notna(canal) else "canal não informado (o campo some no arquivo de 2025)"
    return (nome_categoria(linha["assunto"]),
            f"{nome_categoria(linha['natureza'])} · {nome_categoria(linha['orgao'])} · {canal}",
            f"Registrada em {data_br(linha['data_abertura'])}; prazo legal em {data_br(linha['data_prazo'])}: "
            f"<b>{metricas.numero(linha['dias_alem_do_prazo'])} dias além do prazo</b>.",
            "Sem lugar na base aberta: risco, vulnerabilidade e reincidência não se aplicam.")


def barra_contribuicao(linha: pd.Series) -> alt.Chart:
    d = pd.DataFrame({"chave": CHAVES, "criterio": [CRIT[k].nome for k in CHAVES],
                      "pontos": [linha[f"contrib_{k}"] for k in CHAVES],
                      "nota": [metricas.numero(linha[f"nota_{k}"], 1) for k in CHAVES]})
    d["pontos_txt"] = d["pontos"].map(lambda v: metricas.numero(v, 1))
    return alt.Chart(d).mark_bar(stroke=cor_fundo(), strokeWidth=1, height=14).encode(
        x=alt.X("pontos:Q", stack="zero", scale=alt.Scale(domain=[0, ahp.NOTA_MAXIMA]), axis=None),
        color=alt.Color("chave:N", scale=alt.Scale(domain=CHAVES, range=[CORES[k] for k in CHAVES]), legend=None),
        order=alt.Order("ordem:Q"),
        tooltip=[alt.Tooltip("criterio:N", title="Critério"), alt.Tooltip("nota:N", title="Nota no critério (0 a 10)"),
                 alt.Tooltip("pontos_txt:N", title="Pontos na nota final")],
    ).transform_calculate(ordem=f"indexof({CHAVES}, datum.chave)").properties(height=22)


def cartao(linha: pd.Series, total: int, fonte: str) -> None:
    titulo_cartao, contexto, tempo, repeticao = textos(linha, fonte)
    with st.container(border=True):
        a, b = st.columns([1, 3.4], vertical_alignment="center")
        selo = (f"<div style='color:{linha['cor']};font-weight:700;font-size:.85rem'>✚ {linha['ordem']}º sorteado</div>"
                if "cor" in linha else "")
        a.markdown(selo + f"<div style='font-size:.78rem;opacity:.7'>nota</div>"
                   f"<div style='font-weight:700;line-height:1.05;white-space:nowrap'>"
                   f"<span style='font-size:2.4rem'>{metricas.numero(linha['indice'], 1)}</span>"
                   f"<span style='font-size:1.05rem'> de 10</span></div>"
                   f"<div style='font-size:.78rem;opacity:.7'>{metricas.numero(linha['fila'])}º de "
                   f"{metricas.numero(total)} na fila</div>", unsafe_allow_html=True)
        b.markdown(f"**{titulo_cartao}**  \n<span style='font-size:.88rem'>{contexto}<br>{tempo}<br>{repeticao}</span>",
                   unsafe_allow_html=True)
        b.altair_chart(barra_contribuicao(linha), width="stretch")


def tabela_exibicao(linhas: pd.DataFrame, fonte: str, notas: bool = True) -> pd.DataFrame:
    num = metricas.numero
    t = pd.DataFrame({"Fila": linhas["fila"].map(lambda v: f"{num(v)}º"), "Nota": linhas["indice"].round(1)})
    if fonte == F156:
        t["Serviço"] = linhas["servico"].map(nome_categoria)
        t["Bairro"] = linhas["nome"] + " (RPA " + linhas["rpa"].astype(str) + ")"
        t["Situação"] = linhas["situacao"].map(lambda v: SITUACAO.get(v, v))
        t["Aberto em"] = linhas["data_abertura"].map(data_br)
        t["Aberto há"] = linhas["idade_dias"].map(lambda v: f"{num(v)} dias")
        t["Prazo típico"] = linhas["prazo_tipico_dias"].map(lambda v: f"{num(v)} dias" if pd.notna(v) else "—")
        t["Pedidos anteriores"] = linhas["pedidos_anteriores"].map(lambda v: "sem número" if pd.isna(v) else num(v))
    elif fonte == CAMARA:
        t["Tema"] = linhas["categoria"].map(nome_categoria)
        t["Bairro"] = linhas["nome"] + " (RPA " + linhas["rpa"].astype(str) + ")"
        t["Enviada a"] = linhas["orgao"].map(nome_orgao)
        t["Enviada em"] = linhas["data_envio"].map(data_br)
        t["Sem resposta há"] = linhas["idade_dias"].map(lambda v: f"{num(v)} dias")
        t["Tempo típico"] = linhas["prazo_tipico_dias"].map(lambda v: f"{num(v)} dias")
        t["Mesmo tema no bairro (90 dias)"] = linhas["pedidos_anteriores"].map(num)
    else:
        t["Assunto"] = linhas["assunto"].map(nome_categoria)
        t["Natureza"] = linhas["natureza"].map(nome_categoria)
        t["Órgão"] = linhas["orgao"].map(nome_categoria)
        t["Canal"] = linhas["canal_entrada"].map(lambda v: str(v).lower() if pd.notna(v) else "—")
        t["Registrada em"] = linhas["data_abertura"].map(data_br)
        t["Dias além do prazo"] = linhas["dias_alem_do_prazo"].map(num)
    if notas:
        for k in CHAVES:
            t[CRIT[k].nome] = linhas[f"nota_{k}"].map(lambda v: num(v, 1))
    return t


def mostrar_tabela(t: pd.DataFrame) -> None:
    st.dataframe(t, hide_index=True, width="stretch", column_config=ajuda.colunas(
        t.columns, Nota=st.column_config.ProgressColumn("Nota", min_value=0, max_value=10, format="localized",
                                                        help=ajuda.texto("Nota"))))


@st.cache_data
def centroides() -> pd.DataFrame:
    """Centro aproximado de cada bairro (média dos vértices do maior anel), para marcar quem não tem coordenada."""
    linhas = []
    for f_ in malha()["features"]:
        geo = f_["geometry"]
        aneis = [geo["coordinates"][0]] if geo["type"] == "Polygon" else [p_[0] for p_ in geo["coordinates"]]
        anel = max(aneis, key=len)
        linhas.append({"bairro_oficial": f_["properties"]["bairro_oficial"],
                       "lon_c": sum(c[0] for c in anel) / len(anel), "lat_c": sum(c[1] for c in anel) / len(anel)})
    return pd.DataFrame(linhas).set_index("bairro_oficial")


def onde_marcar(amostra: pd.DataFrame, fonte: str) -> pd.DataFrame:
    """Ponto de cada sorteado no mapa: coordenada aproximada (156) ou centro do bairro; Ouvidoria não tem lugar."""
    if fonte == OUVIDORIA or amostra.empty:
        return amostra.iloc[0:0].assign(lon=[], lat=[], como=[])
    c = centroides().reindex(amostra["bairro_oficial"])
    lon = amostra.get("lon_aprox", pd.Series(index=amostra.index, dtype=float))
    lat = amostra.get("lat_aprox", pd.Series(index=amostra.index, dtype=float))
    tem = lon.notna() & lat.notna()
    return amostra.assign(
        lon=lon.where(tem, c["lon_c"].to_numpy()), lat=lat.where(tem, c["lat_c"].to_numpy()),
        como=["coordenada aproximada (~100 m)" if t else "centro do bairro" for t in tem])


# Sorteio feito aqui, antes do mapa da seção 3, que marca os sorteados; a seção 4 mostra os mesmos.
st.session_state.setdefault(SORTEIO, 2026)
fonte_atual = st.session_state.get("fonte_exemplo", F156)
oc = classificar(fonte_atual)
if not oc.empty:
    oc["fila"] = oc["indice"].rank(ascending=False, method="min").astype(int)
    amostra = oc.sample(min(3, len(oc)), random_state=st.session_state[SORTEIO]).sort_values("indice", ascending=False)
    amostra = amostra.assign(ordem=range(1, len(amostra) + 1), cor=CORES_SORTEIO[:len(amostra)])
else:
    amostra = oc


st.subheader("3. Onde Agir Primeiro",
             help="O índice de prioridade de cada bairro, de 0 a 10, com os pesos acima. Passe o mouse no mapa.")
c1, c2 = st.columns([1, 1.15], gap="large")
with c1:
    tabela_mapa = r.reset_index()
    campos = ["nome", "rpa", "indice", "indice_txt", "posicao", "destaque"] + [f"{k}_txt" for k in CHAVES]
    mapa = alt.Chart(alt.Data(values=malha()["features"])).mark_geoshape(stroke="white", strokeWidth=0.7).transform_lookup(
        lookup="properties.bairro_oficial", from_=alt.LookupData(tabela_mapa, "bairro_oficial", campos),
    ).encode(
        color=alt.condition("isValid(datum.indice)", alt.Color(
            "indice:Q", title="índice de prioridade (0 a 10)", scale=alt.Scale(range=RAMPA, domain=[0, ahp.NOTA_MAXIMA]),
            legend=alt.Legend(orient="bottom", direction="horizontal", gradientLength=220, titleLimit=300)),
            alt.value(SEM_DADO)),
        opacity=alt.condition("datum.destaque", alt.value(1), alt.value(0.25)),
        tooltip=[alt.Tooltip("nome:N", title="Bairro"), alt.Tooltip("posicao:Q", title="Posição"),
                 alt.Tooltip("indice_txt:N", title="Índice")]
                + [alt.Tooltip(f"{k}_txt:N", title=f"{CRIT[k].nome} ({CRIT[k].unidade})") for k in CHAVES],
    ).project(type="mercator").properties(height=520)
    st.altair_chart(mapa, width="stretch")
    leitura("Quanto mais escuro, maior a prioridade. Cinza: bairros com menos de 1.000 moradores, fora do índice.")

with c2:
    lista = r[r["destaque"]].head(15)
    longo = lista.reset_index().melt(id_vars=["bairro_oficial", "nome", "posicao", "indice"],
                                     value_vars=[f"contrib_{k}" for k in CHAVES], var_name="crit", value_name="pontos")
    longo["chave"] = longo["crit"].str.replace("contrib_", "")
    longo["criterio"] = longo["chave"].map(lambda k: CRIT[k].nome)
    longo["rotulo_bairro"] = longo["posicao"].astype(str) + "º · " + longo["nome"]
    longo["pontos_txt"] = longo["pontos"].map(lambda v: metricas.numero(v, 1))
    longo["indice_txt"] = longo["indice"].map(lambda v: metricas.numero(v, 1))
    ordem = (lista["posicao"].astype(str) + "º · " + lista["nome"]).tolist()
    titulo_lista = "Os 15 Bairros com Maior Índice" + (" no Recorte" if f.territorio_ativo else "")
    st.markdown(f"**{titulo_lista}** · quanto cada critério contribui",
                help="Cada barra é a nota do bairro; as cores mostram quantos pontos vieram de cada critério.")
    st.markdown("<div style='font-size:0.85rem'>" + " &nbsp; ".join(
        f"<span style='color:{CORES[k]}'>■</span> {CRIT[k].nome}" for k in CHAVES) + "</div>", unsafe_allow_html=True)
    barras = alt.Chart(longo).mark_bar(stroke=cor_fundo(), strokeWidth=1).encode(
        y=alt.Y("rotulo_bairro:N", sort=ordem, title=None, axis=alt.Axis(labelLimit=220, labelOverlap=False)),
        x=alt.X("pontos:Q", title="pontos do índice (0 a 10)", stack="zero", scale=alt.Scale(domain=[0, ahp.NOTA_MAXIMA])),
        color=alt.Color("criterio:N", title=None,
                        scale=alt.Scale(domain=[CRIT[k].nome for k in CHAVES], range=[CORES[k] for k in CHAVES]),
                        legend=None),
        order=alt.Order("ordem_crit:Q"),
        tooltip=[alt.Tooltip("nome:N", title="Bairro"), alt.Tooltip("criterio:N", title="Critério"),
                 alt.Tooltip("pontos_txt:N", title="Pontos"), alt.Tooltip("indice_txt:N", title="Índice total")],
    ).transform_calculate(ordem_crit=f"indexof({CHAVES}, datum.chave)").properties(height=alt.Step(24))
    st.altair_chart(barras, width="stretch")
    leitura("Barras mais longas, prioridade maior. A cor mostra o porquê: um bairro pode subir por risco (morros), "
            "por vulnerabilidade, por pedidos que passaram do prazo ou por problemas que voltam.")

def limites_do_recife() -> tuple[float, float, float, float]:
    xs, ys = [], []
    for f_ in malha()["features"]:
        geo = f_["geometry"]
        poligonos = [geo["coordinates"]] if geo["type"] == "Polygon" else geo["coordinates"]
        for anel in (a for p_ in poligonos for a in p_):
            xs += [c[0] for c in anel]
            ys += [c[1] for c in anel]
    return min(xs), max(xs), min(ys), max(ys)


def mapa_sorteados(pontos: pd.DataFrame) -> alt.LayerChart:
    """Bairros em tom neutro e uma cruz atravessando o mapa em cada sorteado, na cor do cartão."""
    base = alt.Chart(alt.Data(values=malha()["features"])).mark_geoshape(
        fill=AZUL25, fillOpacity=0.55, stroke=cor_fundo(), strokeWidth=0.7).encode(
        tooltip=[alt.Tooltip("properties.nome:N", title="Bairro")])
    camadas = [base]
    if len(pontos):
        x0, x1, y0, y1 = limites_do_recife()
        pts = pontos.assign(x0=x0, x1=x1, y0=y0, y1=y1, rotulo=pontos["ordem"].astype(str) + "º",
                            nota_txt=pontos["indice"].map(lambda v: metricas.numero(v, 1)))
        cor = alt.Color("rotulo:N", scale=alt.Scale(domain=pts["rotulo"].tolist(), range=pts["cor"].tolist()), legend=None)
        dica = [alt.Tooltip("rotulo:N", title="Sorteado"), alt.Tooltip("nota_txt:N", title="Nota"),
                alt.Tooltip("como:N", title="Posição")]
        camadas += [
            alt.Chart(pts).mark_rule(strokeWidth=1.8, opacity=0.9).encode(
                longitude="lon:Q", latitude="y0:Q", longitude2="lon:Q", latitude2="y1:Q", color=cor, tooltip=dica),
            alt.Chart(pts).mark_rule(strokeWidth=1.8, opacity=0.9).encode(
                longitude="x0:Q", latitude="lat:Q", longitude2="x1:Q", latitude2="lat:Q", color=cor, tooltip=dica),
            alt.Chart(pts).mark_point(shape="circle", size=190, filled=True, stroke="white", strokeWidth=1.5, opacity=1)
            .encode(longitude="lon:Q", latitude="lat:Q", color=cor, tooltip=dica),
        ]
    return alt.layer(*camadas).project(type="mercator").properties(height=380)


st.subheader("4. Exemplo de Ocorrências Classificadas",
             help="Registros reais em aberto recebendo a nota de 0 a 10 do AHP, com os pesos acima.")
demanda_total = tabela("demanda").groupby("fonte")["n"].sum()
TOTAIS = {F156: (demanda_total.get("156_EMLURB", 0), "pedidos no 156 (2012–2026)"),
          CAMARA: (len(tabela("camara_indicacoes")), "indicações de vereadores (2021–2025)"),
          OUVIDORIA: (demanda_total.get("OUVIDORIA", 0), "manifestações na Ouvidoria (2018–2025)")}
EM_ABERTO = {nome: len(tabela(cfg["tabela"])) for nome, cfg in FONTES_EXEMPLO.items()}
contagem = {nome: f"{metricas.numero(TOTAIS[nome][0])} registros · {metricas.numero(EM_ABERTO[nome])} em aberto"
            for nome in FONTES_EXEMPLO}
fonte = st.radio("Fonte", list(FONTES_EXEMPLO), horizontal=True, key="fonte_exemplo",
                 captions=[contagem[n] for n in FONTES_EXEMPLO],
                 help="Registros de cada fonte na base aberta e quantos estão em aberto:  \n"
                      + "  \n".join(f"**{n}:** {contagem[n]}" for n in FONTES_EXEMPLO)
                      + "  \nDefesa Civil e SEDEC ficam de fora: não têm situação confiável de aberto/fechado.")
info = FONTES_EXEMPLO[fonte]
st.markdown(f"**{fonte}** tem **{metricas.numero(TOTAIS[fonte][0])}** {TOTAIS[fonte][1]} na base aberta; "
            f"**{metricas.numero(EM_ABERTO[fonte])}** estão em aberto e podem ser classificados abaixo.")
st.markdown("O índice acima é do **bairro**. Aqui o mesmo AHP, com os mesmos pesos, dá uma nota de 0 a 10 a "
            + info["explica"] + ("" if fonte == OUVIDORIA else " Mude as comparações lá em cima e as notas mudam aqui."))
if fonte == OUVIDORIA and (f.territorio_ativo or f.categorias):
    st.caption("Os filtros de território e de categoria não valem aqui: a Ouvidoria não tem bairro nem a mesma "
               "classificação de serviço.")
if oc.empty:
    st.caption(f"Nenhum registro em aberto no recorte escolhido (ou o bairro está fora do índice, com menos de "
               f"1.000 moradores).")
else:
    b1, b2 = st.columns([1, 3], vertical_alignment="center")
    b1.button("Sortear Ocorrências", icon=":material/casino:", on_click=sortear, width="stretch",
              help="Mostra outros três registros em aberto, sorteados da fonte escolhida.")
    recorte = "do recorte" if fonte != OUVIDORIA and (f.territorio_ativo or f.categorias) else "da cidade"
    fora = len(tabela(info["tabela"])) - len(oc) if fonte == CAMARA and not (f.territorio_ativo or f.categorias) else 0
    g = info["genero"]
    b2.caption(f"Três {info['registro'].split()[0]} sortead{g}s entre {g}s {metricas.numero(len(oc))} {info['registro']} "
               f"{recorte}, d{g} de maior nota para {g} de menor. A fila é a ordem de tod{g}s el{'e' if g == 'o' else 'a'}s "
               "pela nota."
               + (f" {metricas.numero(fora)} indicações ficam de fora: sem bairro identificado na ementa ou em bairro "
                  "com menos de 1.000 moradores." if fora else ""))

    st.markdown("<div style='font-size:0.85rem'>" + " &nbsp; ".join(
        f"<span style='color:{CORES[k]}'>■</span> {CRIT[k].nome}" for k in CHAVES)
        + " &nbsp; <span style='opacity:.7'>(pontos de cada critério na nota)</span></div>", unsafe_allow_html=True)
    aba_cartoes, aba_tabela = st.tabs(["Cartões", "Tabela"])
    with aba_tabela:
        mostrar_tabela(tabela_exibicao(amostra, fonte))
        st.caption("Nas quatro últimas colunas, a nota de 0 a 10 em cada critério (vazia quando o critério não se aplica); "
                   "a nota final pondera essas notas pelos pesos do AHP.")
    with aba_cartoes:
        c1, c2 = st.columns([1.35, 1], gap="large")
        with c1:
            for _, linha in amostra.iterrows():
                cartao(linha, len(oc), fonte)
        with c2:
            st.markdown("**Onde Ficam os Sorteados**",
                        help="Cada cruz marca um sorteado, na cor do cartão. Clique em Sortear e as cruzes se movem.")
            marcar = st.toggle("Mostrar as ocorrências no mapa", value=True, key="mapa_sorteadas",
                               help="Liga e desliga as cruzes dos sorteados.")
            if fonte == OUVIDORIA:
                st.caption("A Ouvidoria não tem bairro, endereço nem coordenadas na base aberta: nada a marcar.")
            pontos = onde_marcar(amostra, fonte) if marcar else amostra.iloc[0:0]
            st.altair_chart(mapa_sorteados(pontos), width="stretch")
            if len(pontos):
                st.markdown("<div style='font-size:.85rem'>" + "<br>".join(
                    f"<span style='color:{p_.cor};font-weight:700'>✚ {p_.ordem}º</span> nota "
                    f"{metricas.numero(p_.indice, 1)} <span style='opacity:.7'>· {p_.como}</span>"
                    for p_ in pontos.itertuples()) + "</div>", unsafe_allow_html=True,
                    help="Pedidos do 156 na coordenada arredondada a ~100 m; sem coordenada, e na Câmara, no centro "
                         "do bairro.")
            st.write("")
            st.markdown("**Onde Cada um Cai na Fila**",
                        help="Quantos registros em aberto há em cada faixa de nota. Os traços laranja são os sorteados.")
            faixas = np.arange(0, ahp.NOTA_MAXIMA + 0.5, 0.5)
            dist = pd.cut(oc["indice"], faixas, include_lowest=True).value_counts(sort=False)
            dist = pd.DataFrame({"inicio": faixas[:-1], "fim": faixas[1:], "registros": dist.to_numpy()})
            dist["faixa"] = dist["inicio"].map(lambda v: metricas.numero(v, 1)) + " a " + dist["fim"].map(lambda v: metricas.numero(v, 1))
            marcas = amostra.assign(rotulo=[f"{i}º" for i in range(1, len(amostra) + 1)],
                                    altura=[8 + 14 * i for i in range(len(amostra))],   # degraus: notas próximas não se cobrem
                                    nota_txt=amostra["indice"].map(lambda v: metricas.numero(v, 1)))
            barras_fila = alt.Chart(dist).mark_bar(color=cor_suave()).encode(
                x=alt.X("inicio:Q", bin="binned", title="nota de prioridade (0 a 10)", scale=alt.Scale(domain=[0, 10])),
                x2="fim:Q", y=alt.Y("registros:Q", axis=eixo_numero(info["registro"])),
                tooltip=[alt.Tooltip("faixa:N", title="Nota"), alt.Tooltip("registros:Q", title="Registros", format=",")])
            cor_marca = alt.Color("rotulo:N", scale=alt.Scale(domain=marcas["rotulo"].tolist(),
                                                              range=marcas["cor"].tolist()), legend=None)
            linhas = alt.Chart(marcas).mark_rule(strokeWidth=2.5).encode(
                x="indice:Q", color=cor_marca, tooltip=[alt.Tooltip("nota_txt:N", title="Nota")])
            rotulos = alt.Chart(marcas).mark_text(align="left", dx=4, fontWeight="bold", fontSize=12).encode(
                x="indice:Q", y=alt.Y("altura:Q", scale=None), text="rotulo:N", color=cor_marca)
            st.altair_chart((barras_fila + linhas + rotulos).resolve_scale(color="independent").properties(height=260),
                            width="stretch")
            alta = (oc["indice"] >= NOTA_ALTA).mean() * 100
            kpi(st, f"Com nota {NOTA_ALTA} ou mais", metricas.porcentagem(alta, 1),
                f"{metricas.numero((oc['indice'] >= NOTA_ALTA).sum())} de {metricas.numero(len(oc))} {info['registro']}",
                "Com os pesos atuais. Seria o primeiro lote de uma fila de atendimento."
                + (" Na Ouvidoria a nota é a posição pelo atraso, então 30% ficam sempre acima de 7." if fonte == OUVIDORIA else ""))

    data_ref = pd.Timestamp(resumo_preparacao()["data_referencia_estoque"])
    if fonte == F156:
        texto_leitura = ("<b>Atraso:</b> 5 = o pedido chegou ao prazo típico da categoria (p90 dos atendidos de 2021–2025); "
                         "10 = o dobro do prazo ou mais. <b>Reincidência:</b> 0 = primeiro pedido do serviço no endereço; "
                         "10 = dez ou mais pedidos anteriores (escala log). Endereços genéricos podem inflar a reincidência.")
    elif fonte == CAMARA:
        texto_leitura = ("<b>Atraso:</b> 5 = a indicação chegou ao tempo típico de resposta do tema (p90 das indicações "
                         "respondidas); 10 = o dobro ou mais. <b>Reincidência:</b> 0 = nenhuma outra indicação do mesmo tema "
                         "no bairro nos 90 dias anteriores; 10 = dez ou mais. \"Sem resposta registrada\" pode incluir "
                         "resposta dada fora do sistema da Câmara; tema e bairro vêm da ementa (rótulo fraco).")
    else:
        texto_leitura = ("<b>Atraso:</b> todas as manifestações abertas já passaram do prazo legal (10 dias úteis), então "
                         "a nota é a posição de cada uma entre as abertas pelos dias além do prazo: 10 = a mais atrasada. "
                         "Só os arquivos de 2024 e 2025 entram (nos antigos, \"aberto\" pode ser só o retrato do ano); "
                         "o de 2025 cobre de julho a dezembro.")
    leitura(f"{texto_leitura} A idade é contada até {data_ref:%d/%m/%Y}, data em que as bases foram baixadas. É um "
            "exemplo: os tetos e os pesos precisam ser validados com quem opera cada serviço.")

    with st.expander(f"A Fila Inteira: os 20 de Maior Nota {'no Recorte' if recorte == 'do recorte' else 'na Cidade'}"):
        mostrar_tabela(tabela_exibicao(oc.head(20), fonte, notas=False))


# --- Sensibilidade --------------------------------------------------------------------------------------
st.subheader("5. O Resultado Depende Muito dos Pesos?",
             help="Testa se o ranking muda quando o peso de um critério sobe ou desce.")
sens = ahp.sensibilidade(ind, w, top=10)
quadro = sens.pivot(index="criterio", columns="fator", values="mantidos_no_top").reindex([CRIT[k].nome for k in CHAVES])
quadro.columns = [f"peso × {str(c).replace('.', ',')}" for c in quadro.columns]
quadro.index.name = "Critério"
st.dataframe(quadro, width="stretch",
             column_config={c: st.column_config.ProgressColumn(
                 c, min_value=0, max_value=10, format="%d de 10",
                 help=f"Quantos dos 10 primeiros bairros continuam no top 10 se o peso do critério for multiplicado "
                      f"por {c.split('× ')[1]}.") for c in quadro.columns})
pior = sens.loc[sens["mantidos_no_top"].idxmin()]
leitura(f"Cada célula muda o peso de um critério (metade, três quartos, uma vez e um quarto, uma vez e meia), "
        f"redistribui o resto e conta quantos dos 10 primeiros continuam no top 10. Com os pesos atuais, o caso "
        f"mais sensível é <b>{pior['criterio']} × {str(pior['fator']).replace('.', ',')}</b>, que mantém "
        f"{int(pior['mantidos_no_top'])} de 10. Se quase tudo fica acima de 7, o ranking é estável e a discussão "
        "com especialistas pode focar nos poucos bairros de fronteira.")
st.caption("AHP não é aprendizado de máquina e não substitui o bônus de modelagem preditiva. Ele torna explícito e "
           "auditável um critério que hoje é implícito. Risco e vulnerabilidade andam juntos em parte (ρ ≈ 0,37), então "
           "os bairros de morro somam pontos nos dois.")


# --- Fórmula ---------------------------------------------------------------------------------------
def legenda_formula(itens: list[str]) -> None:
    st.caption("Onde: " + " · ".join(itens) + ".")


st.subheader("6. A Fórmula da Nota de Prioridade",
             help="Como os pesos e as notas de cada critério se juntam na nota de 0 a 10.")
st.markdown("**Pesos (AHP).** As comparações da seção 1 formam a matriz $A$. Os pesos são o autovetor principal "
            "dela, normalizado para somar 1, e a razão de consistência diz se os julgamentos são coerentes:")
st.latex(r"A\,w = \lambda_{\max}\,w,\qquad \sum_{k} w_k = 1,\qquad "
         r"RC = \frac{(\lambda_{\max} - n)\,/\,(n - 1)}{IA_n} \le 0{,}10")
legenda_formula(["$A$ = matriz das comparações par a par", "$w$ = vetor de pesos", "$w_k$ = peso do critério $k$",
                 "$\\lambda_{\\max}$ = maior autovalor de $A$", "$n$ = número de critérios (4)",
                 "$IA_n$ = índice aleatório de Saaty", "$RC$ = razão de consistência"])
st.markdown("**Nota de um bairro** $b$ (seção 3):")
st.latex(r"P_b = 10 \cdot \big(\, w_R\, r_R(b) + w_V\, r_V(b) + w_A\, r_A(b) + w_E\, r_E(b) \,\big),"
         r"\qquad r_k(b) = \frac{\text{posição}_k(b)}{N}")
legenda_formula(["$P_b$ = nota de prioridade do bairro (0 a 10)", "$b$ = bairro",
                 "$w_R, w_V, w_A, w_E$ = pesos de risco, vulnerabilidade, atraso e reincidência",
                 "$r_k(b)$ = nota do bairro no critério $k$ (0 a 1)",
                 "$\\text{posição}_k(b)$ = posição do bairro do menor para o maior valor no critério $k$",
                 "$N$ = número de bairros comparados (89)"])
st.markdown("**Nota de um pedido aberto** $p$ do 156 ou da Câmara (seção 4), com os mesmos pesos:")
st.latex(r"P_p = 10 \cdot \bigg(\, w_R\, r_R(b_p) + w_V\, r_V(b_p) "
         r"+ w_A\, \frac{\min\!\big(d_p / T_{c_p},\; 2\big)}{2} "
         r"+ w_E\, \min\!\Big(\frac{\ln(1 + m_p)}{\ln 11},\; 1\Big) \,\bigg)")
legenda_formula(["$P_p$ = nota de prioridade do pedido (0 a 10)", "$p$ = pedido aberto", "$b_p$ = bairro do pedido",
                 "$w_R, w_V, w_A, w_E$ = pesos dos critérios", "$r_R(b_p), r_V(b_p)$ = notas de risco e vulnerabilidade do bairro",
                 "$d_p$ = dias em aberto", "$T_{c_p}$ = prazo típico da categoria do pedido",
                 "$m_p$ = pedidos anteriores no mesmo endereço e serviço (no 156) ou do mesmo tema no bairro (na Câmara)"])
st.markdown("**Manifestação da Ouvidoria** $o$ (seção 4): a base aberta não tem lugar, então só o atraso conta, "
            "pela posição entre as abertas. Essa nota não é comparável com as outras:")
st.latex(r"P_o = 10 \cdot \frac{\text{posição}(D_o)}{N_O}")
legenda_formula(["$P_o$ = nota da manifestação (0 a 10)", "$o$ = manifestação aberta da Ouvidoria",
                 "$D_o$ = dias além do prazo legal", "$\\text{posição}(D_o)$ = posição entre as abertas, da menos à mais atrasada",
                 "$N_O$ = número de manifestações abertas"])
@st.cache_data(show_spinner=False)
def exemplo_de_calculo() -> tuple[pd.Series, dict[str, float], dict[str, float]]:
    """Um pedido aberto real do 156 que usa todos os termos da fórmula, classificado com os pesos padrão.

    A regra de escolha é fixa para o exemplo não mudar a cada visita: entre os pedidos com 2 a 5 pedidos
    anteriores e de 1,2 a 1,8 vez o prazo típico, o de nota mais perto do 3º quartil desse grupo.
    """
    indicadores = tabela("indicadores_bairro").set_index("bairro_oficial")
    pesos_padrao = dict(zip(CHAVES, ahp.pesos(ahp.matriz_de_comparacao(ahp.JULGAMENTOS_PADRAO, CHAVES))))
    todos = ahp.indice_ocorrencias(tabela("ocorrencias_abertas_156"), indicadores, pesos_padrao)
    vezes = todos["idade_dias"] / todos["prazo_tipico_dias"]
    grupo = todos[todos["pedidos_anteriores"].between(2, 5) & vezes.between(1.2, 1.8)]
    escolhido = grupo.loc[(grupo["indice"] - grupo["indice"].quantile(0.75)).abs().idxmin()].copy()
    escolhido["nome"] = indicadores.loc[escolhido["bairro_oficial"], "nome"]
    posicoes = {c.chave: float(indicadores[c.coluna].rank(method="average")[escolhido["bairro_oficial"]])
                for c in ahp.CRITERIOS if c.chave in ("risco", "vulnerabilidade")}
    return escolhido, pesos_padrao, posicoes


def peso_txt(valor: float) -> str:
    return metricas.numero(valor, 3)


def n_tex(valor: float, casas: int) -> str:
    casas = 0 if float(valor).is_integer() else casas
    return metricas.numero(valor, casas).replace(",", "{,}")


st.markdown("**Exemplo com um pedido real.** Um pedido aberto do 156, calculado com os pesos padrão "
            "(se você mudar as comparações na seção 1, as notas da seção 4 mudam, mas o exemplo fica fixo):")
ex, wp, pos = exemplo_de_calculo()
nota = {k: ex[f"nota_{k}"] / ahp.NOTA_MAXIMA for k in CHAVES}
st.markdown(
    f"- **Pedido:** {nome_categoria(ex['servico'])} ({nome_categoria(ex['categoria']).lower()}), no bairro "
    f"**{ex['nome']}**, aberto há **{metricas.numero(ex['idade_dias'])} dias**; o prazo típico da categoria é "
    f"**{metricas.numero(ex['prazo_tipico_dias'])} dias**; o endereço já teve **{metricas.numero(ex['pedidos_anteriores'])}** "
    f"pedidos do mesmo serviço antes.\n"
    f"- **Pesos padrão:** risco {metricas.numero(wp['risco'] * 100, 1)}%, vulnerabilidade "
    f"{metricas.numero(wp['vulnerabilidade'] * 100, 1)}%, atraso {metricas.numero(wp['atraso'] * 100, 1)}% e "
    f"reincidência {metricas.numero(wp['reincidencia'] * 100, 1)}%.")
st.markdown("Nota de cada critério, de 0 a 1:")
st.latex(rf"r_R(b_p) = \frac{{{n_tex(pos['risco'], 1)}}}{{89}} = {n_tex(nota['risco'], 3)}"
         rf"\qquad r_V(b_p) = \frac{{{n_tex(pos['vulnerabilidade'], 1)}}}{{89}} = {n_tex(nota['vulnerabilidade'], 3)}")
st.latex(rf"\text{{atraso}} = \frac{{\min({metricas.numero(ex['idade_dias'])}/{metricas.numero(ex['prazo_tipico_dias'])},\;2)}}{{2}}"
         rf" = \frac{{{n_tex(ex['idade_dias'] / ex['prazo_tipico_dias'], 3)}}}{{2}} = {n_tex(nota['atraso'], 3)}"
         rf"\qquad \text{{reincidência}} = \min\!\Big(\frac{{\ln(1 + {metricas.numero(ex['pedidos_anteriores'])})}}{{\ln 11}},\;1\Big)"
         rf" = {n_tex(nota['reincidencia'], 3)}")
legenda_formula([f"$r_R(b_p)$ = nota de risco do bairro {ex['nome']}",
                 f"$r_V(b_p)$ = nota de vulnerabilidade do bairro {ex['nome']}",
                 f"{metricas.numero(pos['risco'], 1 if pos['risco'] % 1 else 0)} e "
                 f"{metricas.numero(pos['vulnerabilidade'], 1 if pos['vulnerabilidade'] % 1 else 0)} = "
                 "$\\text{posição}_k(b_p)$, a posição do bairro do menor para o maior valor em cada critério",
                 "89 = $N$, número de bairros comparados",
                 f"{metricas.numero(ex['idade_dias'])} = $d_p$, dias em aberto",
                 f"{metricas.numero(ex['prazo_tipico_dias'])} = $T_{{c_p}}$, prazo típico da categoria do pedido",
                 f"{metricas.numero(ex['pedidos_anteriores'])} = $m_p$, pedidos anteriores no mesmo endereço e serviço",
                 "atraso e reincidência = notas do pedido nesses critérios, de 0 a 1"])
st.markdown("Soma ponderada e escala de 0 a 10:")
st.latex(rf"P_p = 10 \cdot \big({n_tex(wp['risco'], 3)} \cdot {n_tex(nota['risco'], 3)} "
         rf"+ {n_tex(wp['vulnerabilidade'], 3)} \cdot {n_tex(nota['vulnerabilidade'], 3)} "
         rf"+ {n_tex(wp['atraso'], 3)} \cdot {n_tex(nota['atraso'], 3)} "
         rf"+ {n_tex(wp['reincidencia'], 3)} \cdot {n_tex(nota['reincidencia'], 3)}\big)")
st.latex(rf"P_p = {n_tex(ex['contrib_risco'], 2)} + {n_tex(ex['contrib_vulnerabilidade'], 2)} "
         rf"+ {n_tex(ex['contrib_atraso'], 2)} + {n_tex(ex['contrib_reincidencia'], 2)} = \mathbf{{{n_tex(ex['indice'], 1)}}}")
legenda_formula(["$P_p$ = nota de prioridade do pedido (0 a 10)",
                 f"{peso_txt(wp['risco'])}, {peso_txt(wp['vulnerabilidade'])}, {peso_txt(wp['atraso'])} e "
                 f"{peso_txt(wp['reincidencia'])} = $w_R, w_V, w_A, w_E$, pesos padrão de risco, vulnerabilidade, "
                 "atraso e reincidência",
                 "cada produto = peso × nota do critério; na última linha, já multiplicado por 10, é a contribuição "
                 "do critério em pontos"])
do_lugar = (ex["contrib_risco"] + ex["contrib_vulnerabilidade"]) / ex["indice"] * 100
leitura(f"Com nota {metricas.numero(ex['indice'], 1)}, esse pedido empata ou supera "
        f"{metricas.numero(ex['percentil'], 0)}% dos pedidos abertos do 156 classificados com os pesos padrão. "
        f"{metricas.numero(do_lugar, 0)}% da nota vieram do lugar (risco e vulnerabilidade do bairro {ex['nome']}) e "
        f"{metricas.numero(100 - do_lugar, 0)}% do próprio pedido (atraso e repetição no endereço).")

st.write("")
st.markdown("**Cada variável em detalhe:**")
st.markdown("""
| Símbolo | O que é |
|---|---|
| $A$ | Matriz 4 × 4 das comparações par a par: $a_{ij}$ diz quantas vezes o critério $i$ pesa mais que o $j$ (escala de 1 a 9 de Saaty), e $a_{ji} = 1/a_{ij}$ |
| $w_R, w_V, w_A, w_E$ | Pesos de risco, vulnerabilidade, atraso e reincidência, entre 0 e 1 e somando 1 (os valores atuais estão no gráfico da seção 2) |
| $\\lambda_{\\max}$ | Maior autovalor de $A$; quanto mais perto de $n$, mais coerentes os julgamentos |
| $n$ | Número de critérios (4) |
| $IA_n$ | Índice aleatório de Saaty para $n$ critérios (0,90 para $n = 4$) |
| $RC$ | Razão de consistência; acima de 0,10 os julgamentos devem ser revistos |
| $b$ | Bairro; no índice, os 89 com 1.000 moradores ou mais |
| $N$ | Número de bairros comparados (89) |
| $\\text{posição}_k(b)$ | Posição do bairro do menor para o maior valor no indicador do critério $k$ (empates dividem a posição média) |
| $r_k(b)$ | Nota de 0 a 1 do bairro no critério $k$; bairro sem dado recebe 0 |
| $b_p$ | Bairro do pedido $p$; pedidos dos bairros fora do índice (menos de 1.000 moradores) não são classificados |
| $d_p$ | Dias desde a abertura do pedido (no 156) ou desde o envio à Prefeitura (na Câmara) até a data das bases |
| $T_{c_p}$ | Prazo típico da categoria do pedido: p90 dos dias até atender no 156 (2021–2025) ou até a resposta no mesmo tema na Câmara; categoria sem prazo típico, o termo de atraso vale 0 |
| $m_p$ | Pedidos anteriores no mesmo endereço e serviço (156) ou indicações do mesmo tema no bairro nos 90 dias antes (Câmara); sem número no endereço, o termo vale 0; com 10 ou mais, vale 1 |
| $D_o$, $N_O$ | Dias além do prazo legal da manifestação $o$ e número de manifestações abertas da Ouvidoria |
| $P_b, P_p, P_o$ | Nota de prioridade, de 0 a 10 |
""")
leitura("O fator 10 só muda a escala para uma nota que o gestor lê fácil. Cada parcela da soma é a contribuição do "
        "critério, em pontos, e é ela que aparece nas barras coloridas do ranking da seção 3 e dos cartões da seção 4.")
