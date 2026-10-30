from src.config import (FUNDO_CLARO, FUNDO_ESCURO, PAR_COMPARACAO_CLARO, PAR_COMPARACAO_ESCURO, RAMPA_PRAZO_CLARO,
                        RAMPA_PRAZO_ESCURO, titulo)


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


def _luminancia(cor: str) -> float:
    canais = [int(cor.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canais]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contraste(a: str, b: str) -> float:
    claro, escuro = sorted([_luminancia(a), _luminancia(b)], reverse=True)
    return (claro + 0.05) / (escuro + 0.05)


def test_par_de_comparacao_se_distingue_nos_dois_temas():
    for destaque, apoio in (PAR_COMPARACAO_CLARO, PAR_COMPARACAO_ESCURO):
        assert _contraste(destaque, apoio) >= 3


def test_rampa_de_prazo_ganha_contraste_com_o_fundo_do_mais_rapido_ao_mais_lento():
    for rampa, fundo in ((RAMPA_PRAZO_CLARO, FUNDO_CLARO), (RAMPA_PRAZO_ESCURO, FUNDO_ESCURO)):
        contrastes = [_contraste(cor, fundo) for cor in rampa]
        assert contrastes == sorted(contrastes)
