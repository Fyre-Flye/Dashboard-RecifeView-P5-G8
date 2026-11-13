"""War Room: protótipo de tela de sala de operações, para bater o olho.

A página inteira mostra o estado de um dia: hoje (o último retrato das bases), um dia sorteado ou uma
simulação que avança um dia a cada poucos segundos por um mês. O estoque de cada dia é reconstruído pelas
linhas do tempo (src/retrato.py); as entradas e os atendimentos do dia vêm do fluxo diário do 156.
Cidade inteira, com os pesos padrão do AHP.
"""

import random
import time

import altair as alt
import pandas as pd
import streamlit as st

from src import ahp, ajuda, metricas, retrato
from src.componentes import fontes, leitura
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


def painel(rotulo: str, valor: str, detalhe: str, alerta: bool = False, ajuda_txt: str = "") -> None:
    """Placa grande de sala de operações: rótulo, número e uma linha de contexto. Borda laranja = atenção.
    `ajuda_txt` aparece ao passar o mouse sobre a placa."""
    cor = DESTAQUE if alerta else AZUL
    dica = ajuda_txt.replace("'", "&#39;")
    st.markdown(
        f"<div title='{dica}' style='cursor:help;border:1px solid {cor}55;border-left:6px solid {cor};border-radius:10px;padding:12px 16px;"
        f"min-height:118px'><div style='font-size:.85rem;opacity:.75'>{rotulo}</div>"
        f"<div style='font-size:2.4rem;font-weight:700;line-height:1.1'>{valor}</div>"
        f"<div style='font-size:.85rem;opacity:.8'>{detalhe}</div></div>", unsafe_allow_html=True)


st.session_state.setdefault("wr_modo", "hoje")
st.session_state.setdefault("wr_dia", HOJE)
st.title("War Room")
st.markdown("Protótipo de tela de operações: o que está parado, o que não voltou e onde agir primeiro, num só quadro. "
            "A página inteira mostra o estado de **um dia**: hoje, um dia sorteado ou um mês simulado.")
simulando = st.session_state["wr_modo"] == "simulacao"
b = st.columns([1.2, 1.1, 1.1, 2.2])
b[0].button("Simular um Mês", icon=":material/play_arrow:", on_click=simular_mes, type="primary", width="stretch",
            help="Sorteia um dia e avança um dia a cada 2,5 s, por 30 dias. A página inteira acompanha.")
b[1].button("Dia Aleatório", icon=":material/casino:", on_click=dia_aleatorio, width="stretch",
            help="Mostra a página inteira num dia sorteado, parado.")
b[2].button("Parar e Voltar para Hoje" if simulando else "Voltar para Hoje", icon=":material/today:",
            on_click=voltar_para_hoje, width="stretch", disabled=st.session_state["wr_modo"] == "hoje",
            help=f"Volta para {HOJE:%d/%m/%Y}, o dia em que as bases foram baixadas.")
b[3].caption(f"A simulação sorteia um dia real entre {PRIMEIRO:%d/%m/%Y} e {ULTIMO:%d/%m/%Y} e avança um dia a cada "
             f"{str(SEGUNDOS_POR_DIA).replace('.', ',')} s, por {DIAS_SIMULADOS} dias. As bases só têm a data, sem "
             "horário. Para a sala, recolha a barra lateral e use tela cheia (F11).")
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
    st.markdown(f"<div style='display:flex;gap:16px;align-items:baseline;flex-wrap:wrap'>"
                f"<div style='font-size:2.2rem;font-weight:700'>{data_longa(dia)}</div>"
                f"<div style='font-size:.85rem;font-weight:700;letter-spacing:.06em;color:{cor_selo};"
                f"border:1px solid {cor_selo};border-radius:6px;padding:2px 8px'>{selo}</div></div>",
                unsafe_allow_html=True)
    if modo in ("simulacao", "fim"):
        st.progress(passo / DIAS_SIMULADOS)
    if modo == "hoje":
        st.caption(f"{HOJE:%d/%m/%Y} é o dia em que as bases foram baixadas dos portais, não o do registro mais recente: "
                   "o estoque é o que os arquivos baixados mostram em aberto naquele dia. Registro mais recente de cada "
                   f"fonte: 156 em {ULTIMO_156:%d/%m/%Y} · Câmara: indicações apresentadas até dezembro de 2025, com o "
                   f"envio e a resposta acompanhados até {HOJE:%d/%m/%Y} · Ouvidoria em {ULTIMO_OUVIDORIA:%d/%m/%Y} · "
                   "Defesa Civil em dezembro de 2024.")

    abertos, fila, camara, ouvidoria = estado_em(dia)

    # O dia: entradas e atendimentos. Depois do fim do fluxo diário, mostra o último dia com fluxo, dizendo qual.
    dia_fluxo = ultimo_dia_com_fluxo(dia)
    no_dia = "neste dia" if dia_fluxo == dia else f"em {dia_fluxo:%d/%m/%Y}"
    if dia_fluxo != dia:
        st.markdown(f"<div style='font-size:.9rem;border-left:4px solid {AZUL};padding:4px 10px;margin:4px 0 8px'>"
                    f"O fluxo diário do 156 nas bases vai até <b>{data_longa(dia_fluxo).lower()}</b>. Os quatro quadros "
                    f"de cima mostram esse último dia; o estoque, a fila e os alertas abaixo são de <b>{dia:%d/%m/%Y}</b>."
                    "</div>", unsafe_allow_html=True)
    if dia_fluxo is not None:
        hoje = por_dia.loc[dia_fluxo]
        media = por_dia[por_dia.index.weekday == dia_fluxo.weekday()]["entradas"].mean()
        diferenca = (hoje["entradas"] / media - 1) * 100
        saldo = int(hoje["entradas"] - hoje["atendidos"])
        outras = entradas_fontes.loc[dia_fluxo] if dia_fluxo in entradas_fontes.index else pd.Series(dtype=float)
        q = st.columns(4, gap="small")
        with q[0]:
            painel(f"Entraram no 156 {no_dia}", num(hoje["entradas"]), ajuda_txt="Pedidos registrados no 156 nesta data.",
                   detalhe=
                   f"{'+' if diferenca >= 0 else ''}{metricas.porcentagem(diferenca)} sobre a média de "
                   f"{DIAS_SEMANA[dia_fluxo.weekday()]}", alerta=diferenca > 25)
        with q[1]:
            painel(f"Atendidos no 156 {no_dia}", num(hoje["atendidos"]), "pela data do último movimento",
                   ajuda_txt="Pedidos marcados como atendidos nesta data, de qualquer data de entrada.")
        with q[2]:
            painel("Saldo do dia" if dia_fluxo == dia else f"Saldo em {dia_fluxo:%d/%m}", f"{'+' if saldo > 0 else ''}{num(saldo)}",
                   ajuda_txt="Entradas menos atendimentos: positivo, a fila cresceu.",
                   detalhe=
                   "a fila cresceu" if saldo > 0 else "a fila diminuiu", alerta=saldo > 0)
        with q[3]:
            painel(f"Outras portas {no_dia}", num(sum(outras.get(c, 0) for c in OUTRAS_PORTAS)),
                   ajuda_txt="Registros que entraram nesta data pela Câmara, pela Ouvidoria e pela Defesa Civil.",
                   detalhe=
                   " · ".join(f"{nome} {num(outras.get(c, 0))}" for c, nome in OUTRAS_PORTAS.items()))

    st.write("")
    # O estoque no dia
    atrasados = int(abertos["atrasado"].sum())
    prioritarios = int((fila["indice"] >= NOTA_ALTA).sum())
    fim_janela = min(dia, ULTIMO)
    ultimos30 = por_dia.loc[fim_janela - pd.to_timedelta(29, unit="D"):fim_janela, "entradas"].sum()
    anteriores30 = por_dia.loc[fim_janela - pd.to_timedelta(59, unit="D"):fim_janela - pd.to_timedelta(30, unit="D"),
                               "entradas"].sum()
    p = st.columns(5, gap="small")
    with p[0]:
        painel("Pedidos abertos no 156", num(len(abertos)),
               ajuda_txt="Pedidos que já tinham entrado e ainda não tinham sido atendidos nesta data. Laranja: além do prazo típico da categoria.",
               detalhe=
               f"<b>{metricas.porcentagem(atrasados / len(abertos) * 100 if len(abertos) else 0)}</b> além do prazo típico",
               alerta=True)
    with p[1]:
        painel(f"Fila prioritária (nota ≥ {NOTA_ALTA})", num(prioritarios),
               ajuda_txt="Pedidos abertos com nota de prioridade 7 ou mais no AHP: o primeiro lote a atender.",
               detalhe=
               f"{metricas.porcentagem(prioritarios / len(fila) * 100 if len(fila) else 0, 1)} dos classificáveis")
    with p[2]:
        painel("Indicações sem resposta", num(len(camara)),
               ajuda_txt="Indicações de vereadores já enviadas à Prefeitura e ainda sem resposta registrada nesta data.",
               detalhe=
               f"mediana de <b>{num(camara['idade_dias'].median())} dias</b> desde o envio", alerta=True)
    with p[3]:
        painel("Ouvidoria além do prazo", num(len(ouvidoria)),
               ajuda_txt="Manifestações abertas cujo prazo legal de resposta (10 dias úteis) já tinha passado.",
               detalhe=
               f"mediana de {num(ouvidoria['dias_alem_do_prazo'].median())} dias além do prazo legal", alerta=True)
    with p[4]:
        variacao = (ultimos30 / anteriores30 - 1) * 100 if anteriores30 else None
        painel(f"Entrada no 156 · 30 dias até {fim_janela:%d/%m}", num(ultimos30),
               ajuda_txt="Pedidos que entraram no 156 nos 30 dias até a data, comparados com os 30 dias antes.",
               detalhe=
               "sem os 30 dias anteriores para comparar" if variacao is None else
               f"{'+' if variacao >= 0 else ''}{metricas.porcentagem(variacao)} sobre os 30 dias anteriores",
               alerta=variacao is not None and variacao > 10)

    st.write("")
    c1, c2 = st.columns([1, 1.25], gap="large")
    with c1:
        st.markdown("**Onde o Estoque Atrasado Está** · pedidos do 156 abertos além do prazo típico",
                    help="Quanto mais escuro o bairro, mais pedidos abertos já passaram do prazo típico da categoria.")
        por_bairro = abertos[abertos["atrasado"]].groupby("bairro_oficial", observed=True).size().rename("atrasados").reset_index()
        por_bairro["nome"] = por_bairro["bairro_oficial"].map(nomes_bairro)
        por_bairro["txt"] = por_bairro["atrasados"].map(num)
        st.altair_chart(alt.Chart(alt.Data(values=malha()["features"])).mark_geoshape(stroke="white", strokeWidth=0.6)
                        .transform_lookup(lookup="properties.bairro_oficial",
                                          from_=alt.LookupData(por_bairro, "bairro_oficial", ["nome", "atrasados", "txt"]))
                        .encode(color=alt.condition("isValid(datum.atrasados)", alt.Color(
                            "atrasados:Q", title="pedidos atrasados", scale=alt.Scale(range=RAMPA, type="sqrt"),
                            legend=alt.Legend(orient="bottom", direction="horizontal", gradientLength=240, tickCount=4,
                                              labelExpr=formato_br(), labelOverlap=True)), alt.value(SEM_DADO)),
                                tooltip=[alt.Tooltip("nome:N", title="Bairro"), alt.Tooltip("txt:N", title="Atrasados")])
                        .project(type="mercator").properties(height=430), width="stretch")
    with c2:
        st.markdown(f"**Fila do Dia** · os 12 pedidos abertos de maior nota (de {num(len(fila))})",
                    help="Os pedidos abertos nesta data, em ordem de prioridade pela nota do AHP. Por onde começar.")
        topo = fila.head(12)
        st.dataframe(pd.DataFrame({
            "Nota": topo["indice"].round(1),
            "Serviço": topo["servico"].map(nome_categoria),
            "Bairro": topo["bairro_oficial"].map(nomes_bairro),
            "Aberto há": topo["idade_dias"].map(lambda v: f"{num(v)} dias"),
            "Anteriores no local": topo["pedidos_anteriores"].map(lambda v: "—" if pd.isna(v) else num(v)),
        }), hide_index=True, width="stretch", height=455, column_config={
            "Nota": st.column_config.ProgressColumn("Nota", min_value=0, max_value=10, format="localized", width="small",
                                                    help=ajuda.texto("Nota")),
            "Serviço": st.column_config.TextColumn("Serviço", width="medium", help=ajuda.texto("Serviço")),
            "Bairro": st.column_config.TextColumn("Bairro", width="small", help=ajuda.texto("Bairro")),
            "Aberto há": st.column_config.TextColumn("Aberto há", width="small", help=ajuda.texto("Aberto há")),
            "Anteriores no local": st.column_config.TextColumn("Anteriores no local", width="small",
                                                              help=ajuda.texto("Anteriores no local"))})

    c1, c2, c3 = st.columns([1.3, 1, 1], gap="large")
    with c1:
        if modo in ("simulacao", "fim"):
            inicio = pd.Timestamp(e["wr_inicio"])
            janela = pd.date_range(inicio, inicio + pd.to_timedelta(DIAS_SIMULADOS - 1, unit="D"))
            st.markdown("**O Mês da Simulação até Agora** · 156, por dia",
                        help="Azul: pedidos que entraram em cada dia. Laranja: pedidos atendidos. Os dias seguintes ainda vazios.")
        else:
            janela = pd.date_range(fim_janela - pd.to_timedelta(29, unit="D"), fim_janela)
            st.markdown(f"**Os 30 Dias até {fim_janela:%d/%m/%Y}** · 156, por dia",
                        help="Azul: pedidos que entraram em cada dia. Laranja: pedidos atendidos.")
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
        ).properties(height=260), width="stretch")
    with c2:
        st.markdown("**Categorias com Mais Atraso** · abertos no 156",
                    help="Pedidos abertos além do prazo típico, por categoria · % dos abertos da categoria que já atrasaram.")
        cat = (abertos.groupby("categoria", observed=True).agg(abertos=("atrasado", "size"), atrasados=("atrasado", "sum"))
               .nlargest(7, "atrasados").reset_index())
        cat["nome"] = cat["categoria"].map(nome_categoria)
        cat["rotulo"] = cat["atrasados"].map(num) + " · " + (cat["atrasados"] / cat["abertos"] * 100).map(metricas.porcentagem)
        base = alt.Chart(cat).encode(y=alt.Y("nome:N", sort="-x", title=None, axis=alt.Axis(labelLimit=140)),
                                     x=alt.X("atrasados:Q", axis=None,
                                             scale=alt.Scale(domain=[0, max(cat["atrasados"].max(), 1) * 1.7])))
        st.altair_chart((base.mark_bar(color=DESTAQUE) + base.mark_text(align="left", dx=4, color=TEXTO_TEMA, fontSize=11)
                         .encode(text="rotulo:N")).properties(height=260), width="stretch")
    with c3:
        st.markdown("**O que Mais Entrou Neste Dia** · 156" if dia_fluxo == dia else
                    f"**O que Mais Entrou em {dia_fluxo:%d/%m/%Y}** · 156, último dia com fluxo",
                    help="Categorias e bairros com mais pedidos registrados nesta data. Entre parênteses, quantos.")
        do_dia = fluxo[fluxo["data"] == dia_fluxo]
        if do_dia.empty:
            st.caption("Sem entradas registradas neste dia.")
        else:
            cats = do_dia.groupby("categoria")["entradas"].sum().nlargest(5)
            bairros = do_dia.groupby("bairro_oficial")["entradas"].sum().nlargest(5)
            st.dataframe(pd.DataFrame({"Categoria": [f"{nome_categoria(c)} ({num(n)})" for c, n in cats.items()],
                                       "Bairro": [f"{nomes_bairro.get(b, b)} ({num(n)})" for b, n in bairros.items()]}),
                         hide_index=True, width="stretch", column_config={
                             "Categoria": st.column_config.Column("Categoria", help="Categorias com mais entradas neste dia (pedidos)."),
                             "Bairro": st.column_config.Column("Bairro", help="Bairros com mais entradas neste dia (pedidos).")})

    # Alertas
    st.markdown("**Alertas do Dia**", help="Frases geradas automaticamente a partir dos números desta data.")
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
    if dia_fluxo is not None and por_dia.loc[dia_fluxo, "entradas"] > 0:
        alertas.append(f"Entraram {num(por_dia.loc[dia_fluxo, 'entradas'])} pedidos no 156 {no_dia}, "
                       f"{'acima' if diferenca >= 0 else 'abaixo'} da média de {DIAS_SEMANA[dia_fluxo.weekday()]} "
                       f"({metricas.porcentagem(abs(diferenca))}).")
    if not camara.empty:
        tema = camara["categoria"].value_counts()
        alertas.append(f"Na Câmara, <b>{nome_categoria(tema.index[0]).lower()}</b> lidera as indicações sem resposta "
                       f"({num(tema.iloc[0])}).")
    if not ouvidoria.empty:
        orgao = ouvidoria["orgao"].value_counts()
        alertas.append(f"Na Ouvidoria, <b>{nome_unidade(orgao.index[0])}</b> concentra {num(orgao.iloc[0])} das "
                       f"{num(len(ouvidoria))} manifestações além do prazo.")
    st.markdown("<ul style='margin-top:0'>" + "".join(f"<li>{a}</li>" for a in alertas) + "</ul>", unsafe_allow_html=True)
    leitura("Como o estoque de cada dia é reconstruído: um pedido conta como aberto da entrada até o atendimento (ou até "
            "hoje, se continua aberto nos arquivos mais recentes). Pedidos que ficaram \"abertos\" em arquivos anuais "
            "antigos têm destino desconhecido e ficam de fora, então em datas antigas o estoque é um piso. Em "
            f"{HOJE:%d/%m/%Y} os números batem com o retrato das outras páginas.")


st.fragment(quadro, run_every=SEGUNDOS_POR_DIA if simulando else None)()
