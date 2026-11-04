"""Textos curtos de ajuda (hover) do painel, num só lugar.

Cada texto cabe numa linha: o nome inteiro do que está na tela e o que aquilo é. A mesma coluna tem a mesma
ajuda em todas as páginas.
"""

import streamlit as st

COLUNAS = {
    # pedidos e fila (156)
    "Fila": "Posição na fila: 1º é o de maior nota entre os abertos.",
    "Nota": "Nota de prioridade de 0 a 10 pelo AHP. Maior = mais urgente.",
    "Serviço": "Serviço pedido ao 156.",
    "Categoria": "Grupo de serviço (iluminação, drenagem, poda…).",
    "Bairro": "Bairro do registro.",
    "RPA": "Região Político-Administrativa (o Recife tem 6).",
    "Situação": "Etapa do pedido no 156 no último retrato.",
    "Aberto em": "Data em que o pedido foi registrado.",
    "Aberto há": "Dias desde o registro até a data mostrada.",
    "Prazo típico": "p90 da categoria: 9 em cada 10 pedidos atendidos saem antes disso.",
    "Pedidos anteriores": "Pedidos do mesmo serviço no mesmo endereço antes deste. 'Sem número': não dá para saber.",
    "Anteriores no local": "Pedidos do mesmo serviço no mesmo endereço antes deste. '—': endereço sem número.",
    # Câmara
    "Tema": "Assunto da indicação, inferido da ementa.",
    "Enviada a": "Órgão da Prefeitura que recebeu a indicação.",
    "Enviada em": "Data em que a Câmara enviou a indicação à Prefeitura.",
    "Sem resposta há": "Dias desde o envio sem resposta registrada.",
    "Tempo típico": "p90 dos dias até a resposta, nas indicações do mesmo tema que tiveram resposta.",
    "Mesmo tema no bairro (90 dias)": "Outras indicações do mesmo tema no mesmo bairro nos 90 dias antes desta.",
    # Ouvidoria
    "Assunto": "Assunto da manifestação na Ouvidoria.",
    "Natureza": "Tipo de manifestação: reclamação, denúncia, solicitação…",
    "Órgão": "Órgão responsável pela resposta.",
    "Canal": "Por onde a manifestação entrou (0800, site, e-mail, app…).",
    "Registrada em": "Data do registro na Ouvidoria.",
    "Dias além do prazo": "Dias desde o fim do prazo legal de resposta (10 dias úteis).",
    # critérios do AHP
    "Critério": "Critério do índice de prioridade (AHP).",
    "Risco": "Nota de 0 a 10 no critério Risco (Defesa Civil no bairro).",
    "Vulnerabilidade": "Nota de 0 a 10 no critério Vulnerabilidade (% em favela no bairro).",
    "Atraso": "Nota de 0 a 10 no critério Atraso (tempo aberto contra o prazo típico).",
    "Reincidência": "Nota de 0 a 10 no critério Reincidência (o problema que volta).",
    # território
    "População": "Moradores do bairro no Censo 2022.",
    "% em favela": "Parcela da população em favelas e comunidades urbanas (Censo 2022).",
    "Pedidos 156": "Pedidos ao 156 do bairro no período escolhido.",
    "156 / mil hab. / ano": "Pedidos ao 156 por mil moradores, por ano.",
    "Ações Def. Civil": "Ações da Defesa Civil pedidas pelo cidadão no bairro, no período.",
    "Def. Civil / mil hab. / ano": "Ações da Defesa Civil por mil moradores, por ano.",
    # reincidência
    "Pedidos": "Pedidos do mesmo serviço neste mesmo endereço.",
    "Dias com pedido": "Dias diferentes com pedido: separa problema que volta de pedido em dobro.",
    "Período": "Primeiro e último ano com pedido.",
    # sobre os dados
    "Fonte": "Porta de entrada da demanda.",
    "Registros": "Linhas no dataset do RecifeView.",
    "Uma linha é": "O que cada registro representa nessa fonte.",
    "Origem": "De onde os dados foram baixados.",
    "Correção": "Ajuste feito antes de agregar (detalhes na N3).",
}


def texto(coluna: str) -> str | None:
    return COLUNAS.get(coluna)


def colunas(nomes, **especificas) -> dict:
    """column_config com a ajuda de cada coluna conhecida. `especificas` substitui a configuração de uma coluna
    (use `texto(nome)` como `help` nela para manter a mesma ajuda)."""
    config = {}
    for nome in nomes:
        if nome in especificas:
            config[nome] = especificas[nome]
        elif nome in COLUNAS:
            config[nome] = st.column_config.Column(nome, help=COLUNAS[nome])
    return config
