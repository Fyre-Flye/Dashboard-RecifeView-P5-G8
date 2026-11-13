import streamlit as st

from src.config import AVISO_IA
from src.filtros import desenhar_barra_lateral

st.set_page_config(page_title="RecifeView · Demandas do Recife", page_icon="assets/recifeview_icone.png",
                   layout="wide")
st.logo("assets/recifeview_wordmark.png", icon_image="assets/recifeview_icone.png", size="large")
# Mais conteúdo por tela: o Streamlit reserva muito espaço no topo e entre blocos. Ajuste só de espaçamento.
st.html("""<style>
.stMainBlockContainer {padding-top: 3.6rem; padding-bottom: 2rem;}
.stMainBlockContainer h1 {padding-top: .25rem; padding-bottom: .5rem;}
.stMainBlockContainer h2, .stMainBlockContainer h3 {padding-top: .6rem; padding-bottom: .3rem;}
@media (max-width: 640px) {.stMainBlockContainer {padding-left: 1rem; padding-right: 1rem; padding-top: 3.6rem;}}
</style>""")

pagina = st.navigation({
    "Visão Geral": [
        st.Page("views/war_room.py", title="Painel Geral", icon=":material/dashboard:", default=True),
        st.Page("views/inicio.py", title="Achados", icon=":material/lightbulb:", url_path="achados"),
    ],
    "Onde o Pedido se Perde": [
        st.Page("views/retorno.py", title="Retorno e Fragmentação", icon=":material/call_split:"),
        st.Page("views/reincidencia.py", title="Reincidência", icon=":material/repeat:"),
        st.Page("views/prazos.py", title="Prazos", icon=":material/schedule:"),
    ],
    "Onde Agir Primeiro": [
        st.Page("views/territorio.py", title="Território", icon=":material/map:"),
        st.Page("views/prioridade.py", title="Prioridade (AHP)", icon=":material/low_priority:"),
    ],
    "Referência": [
        st.Page("views/sobre.py", title="Sobre os Dados", icon=":material/info:"),
    ],
})

SEM_FILTROS = {"Painel Geral": "O Painel Geral mostra a cidade inteira num dia, com os pesos padrão do AHP: os "
                               "filtros não se aplicam aqui e voltam a valer nas outras páginas.",
               "Sobre os Dados": "Esta página descreve o dataset inteiro: os filtros não se aplicam aqui."}
desenhar_barra_lateral(SEM_FILTROS.get(pagina.title))
pagina.run()

st.divider()
st.caption(AVISO_IA + " Projetos 5 · CESAR School · 2026.2 · Grupo 08 · trilha AVD.")
