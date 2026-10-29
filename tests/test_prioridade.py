"""O botão de restaurar os julgamentos do AHP volta aos valores padrão sem quebrar a página."""

from pathlib import Path

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
