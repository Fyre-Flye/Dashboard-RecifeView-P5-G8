"""Teste de fumaça: todas as páginas abrem sem erro com combinações de filtro, inclusive as de borda."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")
PAGINAS = ["views/inicio.py", "views/retorno.py", "views/reincidencia.py", "views/prazos.py",
           "views/territorio.py", "views/prioridade.py", "views/sobre.py"]
FILTROS = [
    {},                                                        # padrão: 2021–2025, cidade inteira
    {"f_bairros": ["GUABIRABA"]},                              # um bairro só
    {"f_rpas": ["1"], "f_categorias": ["PAVIMENTACAO"]},       # RPA + categoria
    {"f_categorias": ["COLETA SELETIVA"]},                     # categoria sem indicações da Câmara
    {"f_anos": (2012, 2012)},                                  # ano em que metade das fontes não existe
    {"f_anos": (2026, 2026)},                                  # ano parcial, sem Defesa Civil
]


@pytest.mark.parametrize("pagina", PAGINAS)
@pytest.mark.parametrize("filtros", FILTROS, ids=lambda f: ",".join(f) or "padrao")
def test_pagina_abre_sem_erro(pagina, filtros):
    at = AppTest.from_file(APP, default_timeout=120)
    for chave, valor in filtros.items():
        at.session_state[chave] = valor
    at.switch_page(pagina).run()
    assert not at.exception, [e.value for e in at.exception]
