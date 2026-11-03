"""O botão de restaurar os julgamentos do AHP volta aos valores padrão sem quebrar a página."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src import ahp

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def test_voltar_a_proposta_inicial_restaura_os_julgamentos():
    at = AppTest.from_file(APP, default_timeout=120)
    at.switch_page("views/prioridade.py").run()
    par = at.select_slider(key="ahp_risco_vulnerabilidade")
    par.set_value(-6).run()
    assert at.select_slider(key="ahp_risco_vulnerabilidade").value == -6

    botao = next(b for b in at.button if "proposta inicial" in b.label)
    botao.click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert at.select_slider(key="ahp_risco_vulnerabilidade").value == ahp.JULGAMENTOS_PADRAO[("risco", "vulnerabilidade")]


def test_sortear_ocorrencias_troca_os_pedidos_sem_erro():
    at = AppTest.from_file(APP, default_timeout=120)
    at.switch_page("views/prioridade.py").run()
    antes = at.session_state["sorteio_ocorrencias"]
    botao = next(b for b in at.button if b.label == "Sortear Ocorrências")
    for _ in range(3):
        botao.click().run()
        assert not at.exception, [e.value for e in at.exception]
    assert at.session_state["sorteio_ocorrencias"] != antes


@pytest.mark.parametrize("fonte", ["Central 156 / Emlurb", "Indicações da Câmara", "Ouvidoria"])
@pytest.mark.parametrize("filtros", [{}, {"f_bairros": ["GUABIRABA"]}, {"f_categorias": ["COLETA SELETIVA"]}],
                         ids=["padrao", "bairro", "categoria"])
def test_cada_fonte_do_exemplo_abre_e_sorteia_sem_erro(fonte, filtros):
    at = AppTest.from_file(APP, default_timeout=120)
    for chave, valor in filtros.items():
        at.session_state[chave] = valor
    at.switch_page("views/prioridade.py").run()
    at.radio(key="fonte_exemplo").set_value(fonte).run()
    assert not at.exception, [e.value for e in at.exception]
    botao = next((b for b in at.button if b.label == "Sortear Ocorrências"), None)
    if botao is not None:
        botao.click().run()
        assert not at.exception, [e.value for e in at.exception]
