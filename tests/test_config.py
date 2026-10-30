from src.config import titulo


def test_titulo_capitaliza_palavras_e_mantem_preposicoes_em_minusculas():
    assert titulo("Onde o pedido se perde") == "Onde o Pedido se Perde"
    assert titulo("Como o painel atende ao enunciado") == "Como o Painel Atende ao Enunciado"


def test_titulo_mantem_siglas_numeros_e_primeira_palavra():
    assert titulo("O prazo piorou na cauda (H4)") == "O Prazo Piorou na Cauda (H4)"
    assert titulo("3. Onde agir primeiro") == "3. Onde Agir Primeiro"
    assert titulo("4. O resultado depende") == "4. O Resultado Depende"
    assert titulo("Funciona. A perda") == "Funciona. A Perda"
    assert titulo("Prioridade (AHP)") == "Prioridade (AHP)"


def test_titulo_capitaliza_depois_de_dois_pontos():
    assert titulo("Ouvidoria: por onde a manifestação entra") == "Ouvidoria: Por Onde a Manifestação Entra"


def test_titulo_capitaliza_as_partes_de_uma_palavra_com_barra():
    assert titulo("Defesa civil/risco: órgão → desfecho") == "Defesa Civil/Risco: Órgão → Desfecho"
