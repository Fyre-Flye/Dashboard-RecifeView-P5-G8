import altair as alt
import pandas as pd
import streamlit as st

from src import ajuda, metricas
from src.config import RAMPA, TEXTO, cor_fundo
from src.dados import resumo_preparacao, tabela

FONTES_CURTAS = {"156_EMLURB": "156 / Emlurb", "DEFESA_CIVIL": "Defesa Civil", "OUVIDORIA": "Ouvidoria",
                 "SEDEC_CHAMADOS": "SEDEC", "CAMARA_REQUERIMENTOS": "Câmara"}
PAPEIS = {
    "Alvo possível": "o que um classificador poderia prever (categoria, serviço, órgão, rótulo da SEDEC)",
    "Entrada de texto": "texto livre para modelos de linguagem; o da SEDEC é só de uso interno",
    "Atributo": "conhecido no momento em que o pedido entra; pode alimentar o modelo",
    "Resultado (vazamento se for atributo)": "só existe depois do atendimento; usar como entrada vaza a resposta",
    "Identificador (não usar)": "chave técnica, sem informação para o modelo",
    "Uso interno (sensível)": "pseudônimo de endereço, coordenada ou autoria; fica fora do que é publicado",
}

st.title("Sobre os Dados")
st.markdown("O painel lê um retrato agregado do **dataset do RecifeView** (versão 1.0, 13/10/2026): 2,6 milhões de "
            "registros de cinco portas de entrada, 2012 a 2026, só o município do Recife. O mesmo dataset foi usado na "
            "EDA (entrega N3), e os números do painel batem com os dela.")

aba_fontes, aba_dicionario, aba_cuidados, aba_privacidade = st.tabs(
    ["Fontes e Cobertura", "Dicionário do Dataset", "Cuidados e Correções", "Privacidade, Glossário e IA"])

# --- Fontes e cobertura -----------------------------------------------------------------------------------
with aba_fontes:
    st.subheader("Fontes", help="As cinco portas de entrada do dataset e o que cada registro representa.")
    st.dataframe(pd.DataFrame([
        ["Central 156 / Emlurb", "2012–2026", "1.377.158", "solicitação de serviço urbano", "Portal de Dados Abertos do Recife (ODbL)"],
        ["Defesa Civil", "2014–2024", "886.263", "ação (vistoria, lona, monitoramento), não pedido", "Portal de Dados Abertos do Recife"],
        ["Ouvidoria-Geral", "2018–2025", "222.855", "manifestação (reclamação, denúncia, pedido…)", "Portal de Dados Abertos do Recife"],
        ["SEDEC (áreas de risco)", "2012–2024", "90.659", "chamado em área de risco", "cópia de 09/03/2024 no Internet Archive"],
        ["Câmara Municipal", "2021–2025", "66.546", "indicação ou requerimento de vereador", "sistema público SAGL da Câmara"],
        ["IBGE, Censo 2022", "2022", "94 bairros", "população, domicílios e % em favela", "SIDRA, tabelas 9922, 9923 e 10206"],
    ], columns=["Fonte", "Período", "Registros", "Uma linha é", "Origem"]), hide_index=True, width="stretch",
        column_config=ajuda.colunas(["Fonte", "Período", "Registros", "Uma linha é", "Origem"],
                                    Período=st.column_config.Column("Período", help="Anos cobertos por essa fonte no dataset.")))

    st.subheader("Cobertura: Registros por Fonte e Ano",
                 help="Quantos registros cada fonte tem em cada ano. Célula vazia: a fonte não publica aquele ano.")
    d = tabela("demanda")
    cob = d[d["ano"] >= 2012].groupby(["fonte_nome", "ano"])["n"].sum().reset_index()
    cob["n_txt"] = cob["n"].map(metricas.numero)
    mapa = alt.Chart(cob).encode(
        x=alt.X("ano:O", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("fonte_nome:N", title=None, axis=alt.Axis(labelLimit=220)),
        tooltip=[alt.Tooltip("fonte_nome:N", title="Fonte"), alt.Tooltip("ano:O", title="Ano"),
                 alt.Tooltip("n_txt:N", title="Registros")],
    )
    st.altair_chart((mapa.mark_rect(stroke=cor_fundo(), strokeWidth=2).encode(
        color=alt.Color("n:Q", scale=alt.Scale(type="log", range=RAMPA[1:]), legend=None))
        + mapa.mark_text(fontSize=9).encode(
            text=alt.Text("n_txt:N"), color=alt.condition("datum.n > 40000", alt.value("white"), alt.value(TEXTO))))
        .properties(height=alt.Step(36)), width="stretch")
    st.caption("Células vazias: a fonte não publica aquele ano. 2025 e 2026 são parciais (a Ouvidoria de 2025 só traz "
               "parte do ano; o arquivo de 2025 da Defesa Civil foi publicado vazio; 2026 vai até o download, em "
               "07/10/2026).")

# --- Dicionário do dataset --------------------------------------------------------------------------------
with aba_dicionario:
    dic = tabela("dicionario_dataset").sort_values("ordem")
    st.markdown("Cada coluna do **dataset do RecifeView**, a tabela única (camada ouro) de onde saem a EDA, este "
                "painel e a aplicação. A descrição foi escrita pelo grupo junto com o dataset; tipo de preenchimento, "
                "valores distintos, intervalo e exemplos foram medidos no próprio arquivo.")
    st.table(pd.DataFrame([
        ["Arquivo", "recifeview_demandas_recife_2012_2026.csv.xz (pasta Dados do Drive do grupo; não é público)"],
        ["Tamanho", f"{metricas.numero(resumo_preparacao()['linhas_no_dataset'])} linhas × {len(dic)} colunas · 27 MB "
                    "compactado, 694 MB descompactado"],
        ["Formato", "CSV, separador vírgula, UTF-8, datas AAAA-MM-DD, vazio = sem informação"],
        ["Versão", "1.0, de 13/10/2026 · bases baixadas em 07/10/2026"],
        ["Uma linha é", "um registro de uma fonte (pedido, ação, manifestação, chamado ou indicação)"],
        ["Chave entre fontes", "não existe: o mesmo problema no 156 e na Ouvidoria são duas linhas sem ligação; "
                               "o cruzamento é por bairro, serviço e período"],
        ["Licença", "dados abertos da Prefeitura (ODbL), Câmara (SAGL público) e IBGE"],
    ], columns=["Metadado", "Valor"]).set_index("Metadado"))

    f1, f2 = st.columns(2)
    grupo = f1.selectbox("Grupo de colunas", ["Todos"] + list(dict.fromkeys(dic["grupo"])),
                         help="Colunas agrupadas pelo assunto.")
    papel = f2.selectbox("Papel num modelo de classificação", ["Todos"] + list(PAPEIS),
                         help="O que cada coluna pode ser num modelo supervisionado. Não escolhe o modelo: só "
                              "separa alvo, atributo, resultado (vazamento) e o que não deve entrar.")
    vista = dic[(dic["grupo"] == grupo) | (grupo == "Todos")]
    vista = vista[(vista["papel_em_modelo"] == papel) | (papel == "Todos")]
    exibir = pd.DataFrame({
        "Coluna": vista["coluna"], "Grupo": vista["grupo"], "Tipo": vista["tipo"], "Descrição": vista["descricao"],
        "Preenchida em": vista["preenchida_em"], "% preenchido": vista["pct_preenchido"].round(1),
        "Distintos": vista["n_distintos"], "Intervalo": vista["intervalo"],
        "Valores mais comuns": vista["exemplos"], "Papel num modelo": vista["papel_em_modelo"]})
    escolha = st.dataframe(exibir, hide_index=True, width="stretch", height=420, on_select="rerun",
                           selection_mode="single-row", key="dic_tabela", column_config={
        "Coluna": st.column_config.TextColumn("Coluna", pinned=True, help="Nome da coluna no CSV."),
        "Tipo": st.column_config.TextColumn("Tipo", width="small", help="Tipo do conteúdo (texto, categoria, data…)."),
        "Descrição": st.column_config.TextColumn("Descrição", width="large", help="O que a coluna guarda em cada fonte."),
        "Preenchida em": st.column_config.TextColumn("Preenchida em", help="Fontes em que a coluna tem valor."),
        "% preenchido": st.column_config.ProgressColumn("% preenchido", min_value=0, max_value=100, format="%.1f%%",
                                                        help="Linhas com valor, entre as 2,6 milhões do dataset."),
        "Distintos": st.column_config.NumberColumn("Distintos", format="localized", help="Valores diferentes na coluna."),
        "Intervalo": st.column_config.TextColumn("Intervalo", help="Menor e maior valor (datas e números). Datas de "
                                                 "1900 e prazos negativos são defeitos das fontes."),
        "Valores mais comuns": st.column_config.TextColumn("Valores mais comuns", width="large",
                                                           help="Os quatro mais frequentes. Colunas com dado pessoal, "
                                                                "endereço ou texto livre não mostram exemplos."),
        "Papel num modelo": st.column_config.TextColumn("Papel num modelo", help="Veja a legenda abaixo da tabela.")})
    linhas = escolha.selection.rows if escolha and escolha.selection else []
    if linhas:
        c = vista.iloc[linhas[0]]
        with st.container(border=True):
            st.markdown(f"**`{c['coluna']}`** · {c['grupo']} · {c['tipo']} · {c['papel_em_modelo']}")
            st.markdown(c["descricao"])
            detalhes = [f"Preenchida em: {c['preenchida_em']}",
                        f"{metricas.porcentagem(c['pct_preenchido'], 1)} das linhas",
                        f"{metricas.numero(c['n_distintos'])} valores distintos"]
            if c["intervalo"]:
                detalhes.append(f"de {c['intervalo']}")
            st.caption(" · ".join(detalhes))
            if c["exemplos"]:
                st.caption("Mais comuns: " + c["exemplos"])
    else:
        st.caption("Clique numa linha para ver a descrição completa da coluna.")
    st.markdown("**Papel num modelo de classificação:**\n" + "\n".join(f"- **{k}:** {v}." for k, v in PAPEIS.items()))

    st.subheader("Preenchimento por Fonte",
                 help="% das linhas de cada fonte que têm valor na coluna. Mostra o que cada fonte realmente publica: "
                      "um modelo treinado numa fonte só pode usar as colunas preenchidas nela.")
    longo = vista.melt(id_vars=["coluna", "ordem"], value_vars=[f"pct_{f}" for f in FONTES_CURTAS],
                       var_name="fonte", value_name="pct")
    longo["fonte_nome"] = longo["fonte"].str.removeprefix("pct_").map(FONTES_CURTAS)
    longo["pct_txt"] = longo["pct"].map(lambda v: metricas.porcentagem(v) if v >= 0.05 else "")
    ordem_colunas = vista["coluna"].tolist()
    base = alt.Chart(longo).encode(
        x=alt.X("fonte_nome:N", title=None, sort=list(FONTES_CURTAS.values()),
                axis=alt.Axis(labelAngle=0, orient="top", labelLimit=170)),
        y=alt.Y("coluna:N", title=None, sort=ordem_colunas, axis=alt.Axis(labelLimit=240)),
        tooltip=[alt.Tooltip("coluna:N", title="Coluna"), alt.Tooltip("fonte_nome:N", title="Fonte"),
                 alt.Tooltip("pct:Q", title="% preenchido", format=".1f")])
    st.altair_chart((base.mark_rect(stroke=cor_fundo(), strokeWidth=1.5).encode(
        color=alt.Color("pct:Q", scale=alt.Scale(domain=[0, 100], range=RAMPA), legend=None))
        + base.mark_text(fontSize=10).encode(
            text="pct_txt:N", color=alt.condition("datum.pct > 55", alt.value("white"), alt.value(TEXTO))))
        .properties(height=alt.Step(20)), width="stretch")
    st.download_button("Baixar o dicionário (CSV)", icon=":material/download:",
                       data=dic.drop(columns=["ordem"]).to_csv(index=False).encode("utf-8-sig"),
                       file_name="dicionario_recifeview.csv", mime="text/csv",
                       help="A tabela acima inteira, com o preenchimento por fonte, para abrir no Excel ou no pandas.")

# --- Cuidados e correções ---------------------------------------------------------------------------------
with aba_cuidados:
    st.subheader("Cuidados de Leitura", help="O que pode enganar na leitura dos números.")
    st.markdown("""
- **Não há chave comum entre as fontes.** O mesmo problema registrado no 156 e na Ouvidoria vira duas linhas que não se ligam; o cruzamento é por bairro, serviço e período. Por isso a fragmentação é medida de forma indireta (pela Câmara), e o pedido de acesso à informação (LAI) ao SGDE, protocolado em 08/10, pode mudar isso.
- **Mais pedido não é mais problema.** O painel mostra taxa por habitante ao lado do volume e trata bairros com menos de 1.000 moradores à parte.
- **Defesa Civil conta ações.** O painel usa só as ações pedidas pelo cidadão (o monitoramento proativo fica fora).
- **Câmara:** categoria e órgão vêm de palavras-chave na ementa (rótulo fraco); "sem resposta registrada" não quer dizer que o serviço não foi feito.
- **Prazos:** só pedidos atendidos têm tempo final. Prazo zero costuma ser encerramento administrativo. Anos recentes têm cauda incompleta.
- **Estoque aberto:** só os arquivos 2025 e 2026 do 156, porque cada arquivo anual é um retrato e pedidos antigos podem ter congelado nele.
- **Coordenadas:** faltam em boa parte do 156, e não ao acaso; o recorte territorial é o bairro oficial (94 bairros) e a RPA. Só a seção de ocorrências classificadas usa a coordenada, arredondada a cerca de 100 m.
""")

    st.subheader("O que Foi Corrigido Antes de Agregar",
                 help="Ajustes aplicados aos dados antes de montar o painel, com quantos registros cada um afetou.")
    log = resumo_preparacao()
    st.dataframe(pd.DataFrame([{"Correção": k, "Registros": metricas.numero(v)} for k, v in log["correcoes"].items()]),
                 hide_index=True, width="content", column_config={
                     "Correção": st.column_config.Column("Correção", help=ajuda.texto("Correção")),
                     "Registros": st.column_config.Column("Registros", help="Quantos registros essa correção afetou.")})
    st.caption("As mesmas correções da EDA (N3, seção 1), agora no pipeline do painel (pipeline/correcoes.py), mais a "
               f"marca de prazo zero. Tabelas geradas em {log['gerado_em']} a partir de "
               f"{metricas.numero(log['linhas_no_dataset'])} registros.")

# --- Privacidade, glossário e IA --------------------------------------------------------------------------
with aba_privacidade:
    st.subheader("Privacidade", help="O que fica fora do repositório público e por quê.")
    st.markdown("O repositório público só tem **contagens e indicadores agregados** por ano, bairro, RPA, categoria e "
                "órgão, mais o dicionário de colunas (sem exemplos de colunas com dado pessoal). Não saem do Drive do "
                "grupo: o texto livre da SEDEC (mascarado por heurística, uso só interno), as ementas, o pseudônimo de "
                "endereço (`id_local`), as coordenadas exatas e a autoria das indicações. A lista de pontos crônicos "
                "mostra bairro e serviço, nunca o endereço. Um teste automático confere que nenhuma tabela publicada "
                "tem essas colunas.")

    st.subheader("Glossário", help="Termos usados no painel, em uma linha.")
    st.table(pd.DataFrame([
        ("RPA", "Região Político-Administrativa: as 6 regiões em que a Prefeitura divide os 94 bairros."),
        ("Mediana", "O valor do meio: metade dos pedidos leva menos que isso."),
        ("p90", "90% dos pedidos levam menos que isso; 1 em cada 10 leva mais."),
        ("Local repetido", "Pedido cujo endereço + serviço aparece 2 ou mais vezes (156, 2015–2025)."),
        ("Duplicidade", "Repetição em até 7 dias: provável pedido em dobro."),
        ("Reincidência", "Repetição 30 dias ou mais depois: o problema voltou."),
        ("Indicação", "Pedido de providência que um vereador envia à Prefeitura."),
        ("AHP", "Método que transforma comparações par a par entre critérios em pesos, com teste de coerência."),
        ("Camada ouro", "A tabela final, limpa e unificada, de onde saem análises e painéis (aqui, o dataset do grupo)."),
    ], columns=["Termo", "Significado"]).set_index("Termo"))

    st.subheader("Uso de IA", help="Como a IA ajudou nesta entrega.")
    st.markdown("Este painel foi construído pelo grupo com auxílio do Claude (Anthropic): código, testes e textos foram "
                "gerados a partir das entregas N1 a N3 e revisados pelo grupo. A declaração completa está em "
                "`prompts/declaracao-uso-ia.md` no repositório.")
