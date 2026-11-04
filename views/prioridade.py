import random

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from src import ahp, filtros, metricas
from src.componentes import kpi, leitura
from src.config import (DESTAQUE, RAMPA, SEM_DADO, TEXTO_TEMA, cor_fundo, cor_suave, eixo_numero, nome_categoria,
                        nome_orgao)
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

# --- Critérios ----------------------------------------------------------------------------------------
st.subheader("Os Quatro Critérios e Como Cada Um É Medido")
st.table(pd.DataFrame([{"Critério": c.nome, "Indicador": c.unidade, "O que mede e por quê": c.descricao}
                       for c in ahp.CRITERIOS]).set_index("Critério"))
leitura("Cada bairro recebe, em cada critério, a sua posição relativa entre os 89 bairros com 1.000 moradores ou mais "
        "(0 = menor valor, 1 = maior). O índice é a soma ponderada dessas posições, uma nota de 0 a 10. Usar a posição, "
        "e não o valor bruto, evita que poucos bairros extremos achatem os outros. Os pesos saem das comparações abaixo.")

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
    st.subheader("1. Compare os Critérios Dois a Dois")
    st.caption("Para cada par, quanto um critério é mais importante que o outro para decidir onde agir primeiro "
               "(escala de Saaty: 1 = igual, 3 = moderadamente, 5 = fortemente, 7 = muito, 9 = extremamente).")
    julgamentos = {}
    for a, b in ahp.pares(CHAVES):
        na, nb = CRIT[a].nome, CRIT[b].nome

        def rotulo(o, na=na, nb=nb):
            if o == 1:
                return "igual importância"
            return f"{na} {o}× mais" if o > 0 else f"{nb} {-o}× mais"

        op = st.select_slider(f"{na} × {nb}", OPCOES, key=chave_estado(a, b), format_func=rotulo)
        julgamentos[(a, b)] = para_valor(op)
    st.button("Voltar à proposta inicial do grupo", icon=":material/restart_alt:", on_click=restaurar_julgamentos)

m = ahp.matriz_de_comparacao(julgamentos, CHAVES)
w = dict(zip(CHAVES, ahp.pesos(m)))
rc = ahp.razao_consistencia(m)

with c2:
    st.subheader("2. Pesos Resultantes")
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

st.subheader("3. Onde Agir Primeiro")
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
    st.markdown(f"**{titulo_lista}** · quanto cada critério contribui")
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

# --- Exemplo de ocorrências classificadas ----------------------------------------------------------------
SITUACAO = {"CADASTRADA": "cadastrado", "PREPARACAO": "em preparação", "EXECUCAO": "em execução",
            "PENDENCIA": "com pendência", "FISCALIZACAO": "em fiscalização", "MONITORAMENTO": "em monitoramento"}
SORTEIO = "sorteio_ocorrencias"
CANAL_ENVIO = {"OFICIO": "ofício", "PROTOCOLO NA PREFEITURA": "protocolo na Prefeitura",
               "LOTE JSON SISTEMA PCR": "lote do sistema da Prefeitura", "SISTEMA SEGOV": "sistema da SEGOV",
               "ENVIADO AO EXECUTIVO": "envio ao Executivo", "E-MAIL": "e-mail",
               "CIENCIA AOS INTERESSADOS": "ciência aos interessados"}
NOTA_ALTA = 7
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
        a.markdown(f"<div style='font-size:.78rem;opacity:.7'>nota</div>"
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
    st.dataframe(t, hide_index=True, width="stretch", column_config={
        "Nota": st.column_config.ProgressColumn("Nota", min_value=0, max_value=10, format="localized"),
        **{CRIT[k].nome: st.column_config.TextColumn(CRIT[k].nome, help=f"Nota de 0 a 10 no critério {CRIT[k].nome}")
           for k in CHAVES if CRIT[k].nome in t}})


st.subheader("4. Exemplo de Ocorrências Classificadas")
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
oc = classificar(fonte)
if oc.empty:
    st.caption(f"Nenhum registro em aberto no recorte escolhido (ou o bairro está fora do índice, com menos de "
               f"1.000 moradores).")
else:
    oc["fila"] = oc["indice"].rank(ascending=False, method="min").astype(int)
    st.session_state.setdefault(SORTEIO, 2026)
    b1, b2 = st.columns([1, 3], vertical_alignment="center")
    b1.button("Sortear Ocorrências", icon=":material/casino:", on_click=sortear, width="stretch")
    recorte = "do recorte" if fonte != OUVIDORIA and (f.territorio_ativo or f.categorias) else "da cidade"
    fora = len(tabela(info["tabela"])) - len(oc) if fonte == CAMARA and not (f.territorio_ativo or f.categorias) else 0
    g = info["genero"]
    b2.caption(f"Três {info['registro'].split()[0]} sortead{g}s entre {g}s {metricas.numero(len(oc))} {info['registro']} "
               f"{recorte}, d{g} de maior nota para {g} de menor. A fila é a ordem de tod{g}s el{'e' if g == 'o' else 'a'}s "
               "pela nota."
               + (f" {metricas.numero(fora)} indicações ficam de fora: sem bairro identificado na ementa ou em bairro "
                  "com menos de 1.000 moradores." if fora else ""))
    amostra = oc.sample(min(3, len(oc)), random_state=st.session_state[SORTEIO]).sort_values("indice", ascending=False)

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
            st.markdown("**Onde Cada um Cai na Fila**")
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
            linhas = alt.Chart(marcas).mark_rule(color=DESTAQUE, strokeWidth=2).encode(
                x="indice:Q", tooltip=[alt.Tooltip("nota_txt:N", title="Nota")])
            rotulos = alt.Chart(marcas).mark_text(color=DESTAQUE, align="left", dx=4, fontWeight="bold", fontSize=12).encode(
                x="indice:Q", y=alt.Y("altura:Q", scale=None), text="rotulo:N")
            st.altair_chart((barras_fila + linhas + rotulos).properties(height=260), width="stretch")
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
st.subheader("5. O Resultado Depende Muito dos Pesos?")
sens = ahp.sensibilidade(ind, w, top=10)
quadro = sens.pivot(index="criterio", columns="fator", values="mantidos_no_top").reindex([CRIT[k].nome for k in CHAVES])
quadro.columns = [f"peso × {str(c).replace('.', ',')}" for c in quadro.columns]
quadro.index.name = "Critério"
st.dataframe(quadro, width="stretch",
             column_config={c: st.column_config.ProgressColumn(c, min_value=0, max_value=10, format="%d de 10")
                            for c in quadro.columns})
pior = sens.loc[sens["mantidos_no_top"].idxmin()]
leitura(f"Cada célula muda o peso de um critério (metade, três quartos, uma vez e um quarto, uma vez e meia), "
        f"redistribui o resto e conta quantos dos 10 primeiros continuam no top 10. Com os pesos atuais, o caso "
        f"mais sensível é <b>{pior['criterio']} × {str(pior['fator']).replace('.', ',')}</b>, que mantém "
        f"{int(pior['mantidos_no_top'])} de 10. Se quase tudo fica acima de 7, o ranking é estável e a discussão "
        "com especialistas pode focar nos poucos bairros de fronteira.")
st.caption("AHP não é aprendizado de máquina e não substitui o bônus de modelagem preditiva. Ele torna explícito e "
           "auditável um critério que hoje é implícito. Risco e vulnerabilidade andam juntos em parte (ρ ≈ 0,37), então "
           "os bairros de morro somam pontos nos dois.")
