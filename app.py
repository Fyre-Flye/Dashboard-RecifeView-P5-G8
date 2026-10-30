import streamlit as st

from src.config import AVISO_IA, registrar_tema
from src.filtros import desenhar_barra_lateral

st.set_page_config(page_title="RecifeView · Demandas do Recife", page_icon="assets/recifeview_icone.png",
                   layout="wide")
st.logo("assets/recifeview_wordmark.png", icon_image="assets/recifeview_icone.png", size="large")
registrar_tema()

pagina = st.navigation({
    "Visão Geral": [
        st.Page("views/inicio.py", title="Início", icon=":material/home:", default=True),
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

desenhar_barra_lateral()
pagina.run()

st.divider()
st.caption(AVISO_IA + " Projetos 5 · CESAR School · 2026.2 · Grupo 08 · trilha AVD.")
