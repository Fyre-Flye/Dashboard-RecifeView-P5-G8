"""Painel Geral: a página principal, para o gestor bater o olho e saber por onde começar.

A página inteira mostra o estado de um dia: hoje (o último retrato das bases), um dia sorteado ou uma
simulação que avança um dia a cada poucos segundos por um mês. Cada bloco aponta para a página de detalhe. O estoque de cada dia é reconstruído pelas
linhas do tempo (src/retrato.py); as entradas e os atendimentos do dia vêm do fluxo diário do 156.
Cidade inteira, com os pesos padrão do AHP.
"""

import random
import time

import altair as alt
import pandas as pd
import streamlit as st

from src import ahp, ajuda, metricas, retrato
from src.componentes import fontes, leitura, placa
from src.config import (AZUL, DESTAQUE, RAMPA, SEM_DADO, TEXTO_TEMA, eixo_numero, formato_br, nome_categoria,
                        nome_unidade)
from src.dados import malha, resumo_preparacao, tabela

SEGUNDOS_POR_DIA = 2.5
DIAS_SIMULADOS = 30
NOTA_ALTA = 7
DIAS_SEMANA = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro"]
OUTRAS_PORTAS = {"CAMARA_REQUERIMENTOS": "Câmara", "OUVIDORIA": "Ouvidoria", "DEFESA_CIVIL": "Defesa Civil"}
num = metricas.numero

HOJE = pd.Timestamp(resumo_preparacao()["data_referencia_estoque"])
fluxo = tabela("fluxo_diario_156")
por_dia = fluxo.groupby("data")[["entradas", "atendidos"]].sum()
entradas_fontes = tabela("entradas_diarias").pivot_table(index="data", columns="fonte", values="n", fill_value=0)
PRIMEIRO, ULTIMO = por_dia.index.min(), por_dia.index.max()
ULTIMO_156 = tabela("linha_do_tempo_156")["data_abertura"].max()
ULTIMO_OUVIDORIA = tabela("linha_do_tempo_ouvidoria")["data_abertura"].max()
ind = tabela("indicadores_bairro").set_index("bairro_oficial")
nomes_bairro = tabela("bairros").set_index("bairro_oficial")["nome"]
chaves = [c.chave for c in ahp.CRITERIOS]
PESOS = dict(zip(chaves, ahp.pesos(ahp.matriz_de_comparacao(ahp.JULGAMENTOS_PADRAO, chaves))))


@st.cache_data(max_entries=64, show_spinner=False)
def estado_em(dia: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """No dia: pedidos abertos do 156, a fila (os classificáveis pelo AHP, com nota), indicações sem resposta e
    Ouvidoria além do prazo. A fila deixa de fora bairros fora do índice (menos de 1.000 moradores)."""
    abertos = retrato.abertos_156(tabela("linha_do_tempo_156"), dia)
    fila = ahp.indice_ocorrencias(abertos, ind, PESOS)
    return (abertos, fila, retrato.camara_sem_resposta(tabela("linha_do_tempo_camara"), dia),
            retrato.ouvidoria_alem_do_prazo(tabela("linha_do_tempo_ouvidoria"), dia))


# --- Controles -------------------------------------------------------------------------------------------
def simular_mes() -> None:
    inicio = pd.Timestamp(random.choice(list(por_dia.index[:-DIAS_SIMULADOS])))
    st.session_state.update(wr_modo="simulacao", wr_inicio=inicio, wr_dia=inicio, wr_passo=time.time())


def dia_aleatorio() -> None:
    st.session_state.update(wr_modo="dia", wr_dia=pd.Timestamp(random.choice(list(por_dia.index))))


def voltar_para_hoje() -> None:
    st.session_state.update(wr_modo="hoje", wr_dia=HOJE)


def ultimo_dia_com_fluxo(dia: pd.Timestamp) -> pd.Timestamp | None:
    """O próprio dia, se tem fluxo diário do 156; senão o último dia com fluxo antes dele."""
    anteriores = por_dia.index[por_dia.index <= dia]
    return anteriores.max() if len(anteriores) else None


def data_longa(d: pd.Timestamp) -> str:
    return f"{DIAS_SEMANA[d.weekday()].capitalize()}, {d.day} de {MESES[d.month - 1]} de {d.year}"


def bloco(chave: str):
    """Moldura de cada bloco do painel: mesma borda, mesmo respiro, e a mesma altura dos vizinhos da linha."""
    return st.container(border=True, key=f"bloco-{chave}")


def titulo(texto: str, sub: str = "", ajuda: str = "") -> None:
    st.markdown(f"**{texto}**" + (f" · <span style='opacity:.75'>{sub}</span>" if sub else ""),
                unsafe_allow_html=True, help=ajuda or None)


def secao(texto: str, selo: str, cor: str, dica: str = "") -> None:
    """Título de cada parte do painel (o estoque do dia, o movimento do 156), com um selo ao lado."""
    dica = dica.replace("'", "&#39;")
    st.html(f"<div style='display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:.4rem'>"
                f"<div style='font-size:1.45rem;font-weight:700;line-height:1.3'>{texto}</div>"
                f"<div title='{dica}' style='cursor:{'help' if dica else 'default'};font-size:.75rem;font-weight:700;"
                f"letter-spacing:.06em;color:{cor};border:1px solid {cor};border-radius:6px;padding:2px 8px'>{selo}</div>"
                "</div>")


def lista_curta(rotulo: str, itens: list[tuple[str, float]]) -> None:
    """Mini-ranking: nome à esquerda, quantidade à direita, sem cortar o nome como numa tabela estreita."""
    linhas = "".join(f"<div style='display:flex;justify-content:space-between;gap:8px;padding:3px 0;"
                     f"border-bottom:1px solid rgba(128,128,128,.18)'><span>{nome}</span>"
                     f"<span style='font-variant-numeric:tabular-nums;opacity:.8'>{num(n)}</span></div>"
                     for nome, n in itens)
    st.html(f"<div style='font-size:.78rem;opacity:.7;margin-bottom:2px'>{rotulo}</div>"
            f"<div style='font-size:.88rem'>{linhas}</div>")


def legenda_extremos(serie: pd.Series) -> list[int]:
    """Só o menor e o maior valor na legenda do mapa: com escala comprimida, os rótulos do meio se encavalam no celular."""
    return [int(serie.min()), int(serie.max())] if len(serie) else []


def ver_detalhe(pagina: str, rotulo: str, icone: str) -> None:
    st.page_link(pagina, label=rotulo, icon=icone, width="content")




st.session_state.setdefault("wr_modo", "hoje")
st.session_state.setdefault("wr_dia", HOJE)
simulando = st.session_state["wr_modo"] == "simulacao"

cab = st.columns([3, 1.1], vertical_alignment="bottom")
cab[0].title("Painel Geral")
cab[0].markdown("O retrato da cidade num dia: o que está parado, o que não voltou e por onde começar. Cada bloco leva "
                "à página com o detalhe; o contexto e os achados estão em "
                "[Achados](/achados).")
with cab[1]:
    if simulando:
        st.button("Parar e voltar para hoje", icon=":material/stop:", on_click=voltar_para_hoje, type="primary",
                  width="stretch", help=f"Volta para {HOJE:%d/%m/%Y}, o dia em que as bases foram baixadas.")
    else:
        with st.popover("Ver outro dia", icon=":material/calendar_month:", width="stretch",
                        help="Mostra o painel num dia sorteado ou simula um mês, um dia a cada 2,5 s."):
            st.button("Simular um mês", icon=":material/play_arrow:", on_click=simular_mes, type="primary",
                      width="stretch", help="Sorteia um dia e avança um dia a cada 2,5 s, por 30 dias.")
            st.button("Dia aleatório", icon=":material/casino:", on_click=dia_aleatorio, width="stretch",
                      help="Mostra o painel inteiro num dia sorteado, parado.")
            st.button("Voltar para hoje", icon=":material/today:", on_click=voltar_para_hoje, width="stretch",
                      disabled=st.session_state["wr_modo"] == "hoje")
            st.caption(f"Os dias sorteados vão de {PRIMEIRO:%d/%m/%Y} a {ULTIMO:%d/%m/%Y}. As bases só têm a data, sem "
                       "horário. Para uma TV, recolha a barra lateral e use tela cheia (F11).")
fontes(["156_EMLURB", "DEFESA_CIVIL", "CAMARA_REQUERIMENTOS", "OUVIDORIA"])


# --- Quadro do dia ---------------------------------------------------------------------------------------
def quadro() -> None:
    e = st.session_state
    if e["wr_modo"] == "simulacao" and time.time() - e.get("wr_passo", 0) >= SEGUNDOS_POR_DIA - 0.3:
        if e["wr_dia"] < e["wr_inicio"] + pd.to_timedelta(DIAS_SIMULADOS - 1, unit="D"):
            e["wr_dia"] = pd.Timestamp(e["wr_dia"]) + pd.to_timedelta(1, unit="D")
            e["wr_passo"] = time.time()
        else:
            e["wr_modo"] = "fim"
            st.rerun()                                    # para o relógio da página
    modo, dia = e["wr_modo"], pd.Timestamp(e["wr_dia"])

    if modo in ("simulacao", "fim"):
        passo = (dia - pd.Timestamp(e["wr_inicio"])).days + 1
        selo = f"SIMULAÇÃO · dia {passo} de {DIAS_SIMULADOS}" + (" · encerrada" if modo == "fim" else "")
    else:
        selo = f"HOJE · bases baixadas em {HOJE:%d/%m/%Y}" if modo == "hoje" else "DIA SORTEADO"
    cor_selo = DESTAQUE if modo in ("simulacao", "fim") else AZUL
    dica_hoje = (f"{HOJE:%d/%m/%Y} é o dia em que as bases foram baixadas dos portais, não o do registro mais recente. "
                 f"Registro mais recente: 156 em {ULTIMO_156:%d/%m/%Y}; Câmara, indicações até dezembro de 2025, com "
                 f"envio e resposta acompanhados até {HOJE:%d/%m/%Y}; Ouvidoria em {ULTIMO_OUVIDORIA:%d/%m/%Y}; "
                 "Defesa Civil em dezembro de 2024.") if modo == "hoje" else ""
    secao(data_longa(dia), selo, cor_selo, dica_hoje)
    if modo in ("simulacao", "fim"):
        st.progress(passo / DIAS_SIMULADOS)

    abertos, fila, camara, ouvidoria = estado_em(dia)
    dia_fluxo = ultimo_dia_com_fluxo(dia)
    no_dia = "neste dia" if dia_fluxo == dia else f"em {dia_fluxo:%d/%m/%Y}"

    # 1. O que está parado agora
    atrasados = int(abertos["atrasado"].sum())
    prioritarios = int((fila["indice"] >= NOTA_ALTA).sum())
    fim_janela = min(dia, ULTIMO)
    ultimos30 = por_dia.loc[fim_janela - pd.to_timedelta(29, unit="D"):fim_janela, "entradas"].sum()
    anteriores30 = por_dia.loc[fim_janela - pd.to_timedelta(59, unit="D"):fim_janela - pd.to_timedelta(30, unit="D"),
                               "entradas"].sum()
    variacao = (ultimos30 / anteriores30 - 1) * 100 if anteriores30 else None
    p = st.columns(5, gap="small")
    with p[0]:
        placa(st, "Pedidos abertos no 156", num(len(abertos)),
              ajuda="Pedidos que já tinham entrado e ainda não tinham sido atendidos nesta data. Laranja: além do prazo típico da categoria.",
              detalhe=f"<b>{metricas.porcentagem(atrasados / len(abertos) * 100 if len(abertos) else 0)}</b> além do prazo típico",
              alerta=True, link=("views/prazos.py", "Prazos", ":material/schedule:"), chave="abertos", esticar=True)
    with p[1]:
        placa(st, f"Fila prioritária (nota ≥ {NOTA_ALTA})", num(prioritarios),
              ajuda="Pedidos abertos com nota de prioridade 7 ou mais no AHP: o primeiro lote a atender.",
              detalhe=f"{metricas.porcentagem(prioritarios / len(fila) * 100 if len(fila) else 0, 1)} dos classificáveis",
              link=("views/prioridade.py", "Prioridade", ":material/low_priority:"), chave="fila", esticar=True)
    with p[2]:
        placa(st, "Indicações sem resposta", num(len(camara)),
              ajuda="Indicações de vereadores já enviadas à Prefeitura e ainda sem resposta registrada nesta data.",
              detalhe=f"mediana de <b>{num(camara['idade_dias'].median())} dias</b> desde o envio", alerta=True,
              link=("views/retorno.py", "Retorno", ":material/call_split:"), chave="camara", esticar=True)
    with p[3]:
        placa(st, "Ouvidoria além do prazo", num(len(ouvidoria)),
              ajuda="Manifestações abertas cujo prazo legal de resposta (10 dias úteis) já tinha passado.",
              detalhe=f"mediana de {num(ouvidoria['dias_alem_do_prazo'].median())} dias além do prazo legal", alerta=True,
              link=("views/retorno.py", "Retorno", ":material/call_split:"), chave="ouvidoria", esticar=True)
    with p[4]:
        placa(st, f"Entrada no 156 · 30 dias até {fim_janela:%d/%m}", num(ultimos30),
              ajuda="Pedidos que entraram no 156 nos 30 dias até a data, comparados com os 30 dias antes.",
              detalhe="sem os 30 dias anteriores para comparar" if variacao is None else
              f"{'+' if variacao >= 0 else ''}{metricas.porcentagem(variacao)} sobre os 30 dias anteriores",
              alerta=variacao is not None and variacao > 10,
              link=("views/reincidencia.py", "Reincidência", ":material/repeat:"), chave="entrada", esticar=True)

    # 2. Alertas: o resumo em frases
    cat = (abertos.groupby("categoria", observed=True).agg(abertos=("atrasado", "size"), atrasados=("atrasado", "sum"))
           .nlargest(7, "atrasados").reset_index())
    cat["nome"] = cat["categoria"].map(nome_categoria)
    cat["rotulo"] = cat["atrasados"].map(num) + " · " + (cat["atrasados"] / cat["abertos"] * 100).map(metricas.porcentagem)
    alertas = []
    if not cat.empty:
        alertas.append(f"<b>{cat.iloc[0]['nome']}</b> tem {num(cat.iloc[0]['atrasados'])} pedidos abertos além do prazo "
                       "típico, o maior estoque atrasado da cidade.")
    if not fila.empty:
        primeiro = fila.iloc[0]
        nove = int((fila["indice"] >= 9).sum())
        alertas.append((f"<b>{num(nove)}</b> pedido{'s têm' if nove > 1 else ' tem'} nota 9 ou mais" if nove else
                        "Nenhum pedido tem nota 9 ou mais") + "; o primeiro da fila é "
                       f"{nome_categoria(primeiro['servico']).lower()} em {nomes_bairro.get(primeiro['bairro_oficial'])}, "
                       f"aberto há {num(primeiro['idade_dias'])} dias.")
    if not camara.empty:
        tema = camara["categoria"].value_counts()
        alertas.append(f"Na Câmara, <b>{nome_categoria(tema.index[0]).lower()}</b> lidera as indicações sem resposta "
                       f"({num(tema.iloc[0])}).")
    if not ouvidoria.empty:
        orgao = ouvidoria["orgao"].value_counts()
        alertas.append(f"Na Ouvidoria, <b>{nome_unidade(orgao.index[0])}</b> concentra {num(orgao.iloc[0])} das "
                       f"{num(len(ouvidoria))} manifestações além do prazo.")
    st.space("xxsmall")   # 1rem + .25 + 1rem: o mesmo respiro dos blocos lado a lado
    with bloco("alertas"):
        titulo("Alertas do Dia", ajuda="Frases geradas automaticamente a partir dos números desta data.")
        st.html("<ul style='margin:0;padding-left:1.3rem;line-height:1.6'>"
                + "".join(f"<li style='margin:.15rem 0'>{a}</li>" for a in alertas) + "</ul>")

    # 3. Onde está e por onde começar
    st.space("xxsmall")
    c1, c2 = st.columns([1, 1.25], gap="medium")
    with c1, bloco("mapa"):
        titulo("Onde o Estoque Atrasado Está", "pedidos do 156 além do prazo típico",
               "Quanto mais escuro o bairro, mais pedidos abertos já passaram do prazo típico da categoria. A escala de cores "
               "é comprimida (potência 0,3), porque as contagens vão de poucos a mais de mil: assim os bairros do meio não "
               "somem no claro e o mapa fica na mesma faixa de azuis do Onde Agir Primeiro.")
        por_bairro = abertos[abertos["atrasado"]].groupby("bairro_oficial", observed=True).size().rename("atrasados").reset_index()
        por_bairro["nome"] = por_bairro["bairro_oficial"].map(nomes_bairro)
        por_bairro["txt"] = por_bairro["atrasados"].map(num)
        st.altair_chart(alt.Chart(alt.Data(values=malha()["features"])).mark_geoshape(stroke="white", strokeWidth=0.6)
                        .transform_lookup(lookup="properties.bairro_oficial",
                                          from_=alt.LookupData(por_bairro, "bairro_oficial", ["nome", "atrasados", "txt"]))
                        .encode(color=alt.condition("isValid(datum.atrasados)", alt.Color(
                            "atrasados:Q", title="pedidos atrasados", scale=alt.Scale(range=RAMPA, type="pow", exponent=0.3),
                            legend=alt.Legend(orient="bottom", direction="horizontal", gradientLength=200,
                                              values=legenda_extremos(por_bairro["atrasados"]),
                                              labelExpr=formato_br())), alt.value(SEM_DADO)),
                                tooltip=[alt.Tooltip("nome:N", title="Bairro"), alt.Tooltip("txt:N", title="Atrasados")])
                        .project(type="mercator").properties(height=370), width="stretch")
        st.space("stretch")
        ver_detalhe("views/territorio.py", "Ver taxas por bairro em Território", ":material/map:")
    with c2, bloco("fila"):
        titulo("Fila do Dia", f"os 10 pedidos abertos de maior nota (de {num(len(fila))})",
               "Os pedidos abertos nesta data, em ordem de prioridade pela nota do AHP. Por onde começar.")
        topo = fila.head(10)
        st.dataframe(pd.DataFrame({
            "Nota": topo["indice"].round(1),
            "Serviço": topo["servico"].map(nome_categoria),
            "Bairro": topo["bairro_oficial"].map(nomes_bairro),
            "Aberto há": topo["idade_dias"].map(lambda v: f"{num(v)} dias"),
            "Anteriores": topo["pedidos_anteriores"].map(lambda v: "—" if pd.isna(v) else num(v)),
        }), hide_index=True, width="stretch", height=388, column_config={
            "Nota": st.column_config.ProgressColumn("Nota", min_value=0, max_value=10, format="localized", width="small",
                                                    help=ajuda.texto("Nota")),
            "Serviço": st.column_config.TextColumn("Serviço", width="medium", help=ajuda.texto("Serviço")),
            "Bairro": st.column_config.TextColumn("Bairro", width="small", help=ajuda.texto("Bairro")),
            "Aberto há": st.column_config.TextColumn("Aberto há", width="small", help=ajuda.texto("Aberto há")),
            "Anteriores": st.column_config.TextColumn("Anteriores", width="small",
                                                              help=ajuda.texto("Anteriores no local"))})
        st.space("stretch")
        ver_detalhe("views/prioridade.py", "Ver fila completa e cálculo da nota em Prioridade", ":material/low_priority:")

    # 4. O movimento do dia no 156
    st.space("small")
    secao("O Movimento no 156", "FLUXO DO DIA" if dia_fluxo == dia else f"ÚLTIMO FLUXO · {dia_fluxo:%d/%m/%Y}",
          AZUL, "Entradas e atendimentos do 156 por dia. O estoque acima é sempre da data do painel." +
          ("" if dia_fluxo == dia else f" O fluxo diário das bases vai até {dia_fluxo:%d/%m/%Y}: as placas e os "
           "gráficos abaixo mostram esse último dia."))
    if dia_fluxo is not None:
        hoje = por_dia.loc[dia_fluxo]
        media = por_dia[por_dia.index.weekday == dia_fluxo.weekday()]["entradas"].mean()
        diferenca = (hoje["entradas"] / media - 1) * 100
        saldo = int(hoje["entradas"] - hoje["atendidos"])
        outras = entradas_fontes.loc[dia_fluxo] if dia_fluxo in entradas_fontes.index else pd.Series(dtype=float)
        q = st.columns(4, gap="small")
        with q[0]:
            placa(st, f"Entraram no 156 {no_dia}", num(hoje["entradas"]), ajuda="Pedidos registrados no 156 nesta data.",
                   detalhe=f"{'+' if diferenca >= 0 else ''}{metricas.porcentagem(diferenca)} sobre a média de "
                   f"{DIAS_SEMANA[dia_fluxo.weekday()]}", alerta=diferenca > 25, chave="entraram", esticar=True)
        with q[1]:
            placa(st, f"Atendidos no 156 {no_dia}", num(hoje["atendidos"]), detalhe="pela data do último movimento",
                   ajuda="Pedidos marcados como atendidos nesta data, de qualquer data de entrada.", chave="atendidos", esticar=True)
        with q[2]:
            placa(st, "Saldo do dia" if dia_fluxo == dia else f"Saldo em {dia_fluxo:%d/%m}",
                   f"{'+' if saldo > 0 else ''}{num(saldo)}",
                   ajuda="Entradas menos atendimentos: positivo, a fila cresceu.",
                   detalhe="a fila cresceu" if saldo > 0 else "a fila diminuiu", alerta=saldo > 0, chave="saldo", esticar=True)
        with q[3]:
            placa(st, f"Outras portas {no_dia}", num(sum(outras.get(c, 0) for c in OUTRAS_PORTAS)),
                   ajuda="Registros que entraram nesta data pela Câmara, pela Ouvidoria e pela Defesa Civil.",
                   detalhe=" · ".join(f"{nome} {num(outras.get(c, 0))}" for c, nome in OUTRAS_PORTAS.items()), chave="outras", esticar=True)

    st.space("xxsmall")
    c1, c2, c3 = st.columns([1.3, 1, 1], gap="medium")
    with c1, bloco("trinta"):
        if modo in ("simulacao", "fim"):
            inicio = pd.Timestamp(e["wr_inicio"])
            janela = pd.date_range(inicio, inicio + pd.to_timedelta(DIAS_SIMULADOS - 1, unit="D"))
            titulo("O Mês da Simulação até Agora", "156, por dia",
                   "Azul: pedidos que entraram em cada dia. Laranja: pedidos atendidos. Os dias seguintes ainda vazios.")
        else:
            janela = pd.date_range(fim_janela - pd.to_timedelta(29, unit="D"), fim_janela)
            titulo(f"Os 30 Dias até {fim_janela:%d/%m/%Y}", "156, por dia",
                   "Azul: pedidos que entraram em cada dia. Laranja: pedidos atendidos.")
        serie = por_dia.reindex(janela, fill_value=0)
        serie.loc[serie.index > dia] = 0                                   # o futuro ainda não aconteceu
        serie = serie.rename_axis("data").reset_index().melt(id_vars="data", var_name="tipo", value_name="n")
        serie["tipo"] = serie["tipo"].map({"entradas": "entraram", "atendidos": "atendidos"})
        serie["dia_txt"] = serie["data"].dt.strftime("%d/%m")
        ordem_dias = serie.drop_duplicates("data")["dia_txt"].tolist()
        st.altair_chart(alt.Chart(serie).mark_bar().encode(
            x=alt.X("dia_txt:N", sort=ordem_dias, title=None,
                    axis=alt.Axis(labelAngle=-90, labelExpr="(indexof(" + str(ordem_dias) + ", datum.value) % 3 == 0) ? datum.value : ''")),
            xOffset=alt.XOffset("tipo:N", sort=["entraram", "atendidos"]),
            y=alt.Y("n:Q", axis=eixo_numero(None)),
            color=alt.Color("tipo:N", scale=alt.Scale(domain=["entraram", "atendidos"], range=[AZUL, DESTAQUE]),
                            legend=alt.Legend(orient="top", title=None)),
            tooltip=[alt.Tooltip("dia_txt:N", title="Dia"), alt.Tooltip("tipo:N", title=" "),
                     alt.Tooltip("n:Q", title="Pedidos", format=",")],
        ).properties(height=250), width="stretch")
    with c2, bloco("categorias"):
        titulo("Categorias com Mais Atraso", "abertos no 156",
               "Pedidos abertos além do prazo típico, por categoria · % dos abertos da categoria que já atrasaram.")
        base = alt.Chart(cat).encode(y=alt.Y("nome:N", sort="-x", title=None, axis=alt.Axis(labelLimit=125)),
                                     x=alt.X("atrasados:Q", axis=None,
                                             scale=alt.Scale(domain=[0, max(cat["atrasados"].max(), 1) * 3.0], nice=False)))
        st.altair_chart((base.mark_bar(color=DESTAQUE) + base.mark_text(align="left", dx=4, color=TEXTO_TEMA, fontSize=10)
                         .encode(text="rotulo:N")).properties(height=210), width="stretch")
        st.space("stretch")
        ver_detalhe("views/prazos.py", "Ver em Prazos", ":material/schedule:")
    with c3, bloco("entrou"):
        titulo("O que Mais Entrou " + ("Neste Dia" if dia_fluxo == dia else f"em {dia_fluxo:%d/%m/%Y}"), "156",
               "As 3 categorias e os 3 bairros com mais pedidos registrados nesta data, com a quantidade.")
        do_dia = fluxo[fluxo["data"] == dia_fluxo]
        if do_dia.empty:
            st.caption("Sem entradas registradas neste dia.")
        else:
            cats = do_dia.groupby("categoria")["entradas"].sum().nlargest(3)
            bairros = do_dia.groupby("bairro_oficial")["entradas"].sum().nlargest(3)
            lista_curta("Categorias", [(nome_categoria(c), n) for c, n in cats.items()])
            lista_curta("Bairros", [(nomes_bairro.get(b, b), n) for b, n in bairros.items()])

    st.space("small")
    leitura("Como o estoque de cada dia é reconstruído: um pedido conta como aberto da entrada até o atendimento (ou até "
            "hoje, se continua aberto nos arquivos mais recentes). Pedidos que ficaram \"abertos\" em arquivos anuais "
            "antigos têm destino desconhecido e ficam de fora, então em datas antigas o estoque é um piso. Em "
            f"{HOJE:%d/%m/%Y} os números batem com o retrato das outras páginas. Cidade inteira, com os pesos padrão do "
            "AHP: os filtros da barra lateral não se aplicam aqui.")


st.fragment(quadro, run_every=SEGUNDOS_POR_DIA if simulando else None)()
