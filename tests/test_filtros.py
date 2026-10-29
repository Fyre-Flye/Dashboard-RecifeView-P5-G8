from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from src.filtros import PERIODO_PADRAO, Filtros


def _df():
    return pd.DataFrame({
        "ano": [2019, 2021, 2023, 2025],
        "rpa": ["1", "3", "3", "6"],
        "bairro_oficial": ["RECIFE", "CASA AMARELA", "GUABIRABA", "IBURA"],
        "categoria": ["DRENAGEM", "DRENAGEM", "ILUMINACAO PUBLICA", "DRENAGEM"],
    })


def test_filtros_vazios_so_aplicam_o_periodo():
    f = Filtros(anos=(2021, 2025), rpas=(), bairros=(), categorias=())
    assert f.aplicar(_df())["ano"].tolist() == [2021, 2023, 2025]
    assert not f.territorio_ativo


def test_filtros_combinados():
    f = Filtros(anos=(2012, 2026), rpas=("3",), bairros=(), categorias=("DRENAGEM",))
    assert f.aplicar(_df())["bairro_oficial"].tolist() == ["CASA AMARELA"]


def test_pagina_pode_desligar_um_filtro():
    f = Filtros(anos=(2012, 2026), rpas=("3",), bairros=(), categorias=("DRENAGEM",))
    assert len(f.aplicar(_df(), territorio=False)) == 3


def test_tabela_sem_a_coluna_ignora_o_filtro():
    f = Filtros(anos=(2012, 2026), rpas=("3",), bairros=("GUABIRABA",), categorias=())
    sem_territorio = pd.DataFrame({"ano": [2022, 2023], "orgao": ["URB", "EMLURB"]})
    assert len(f.aplicar(sem_territorio)) == 2


def test_limpar_filtros_volta_ao_padrao_sem_erro():
    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=120)
    at.session_state["f_rpas"] = ["6"]
    at.session_state["f_anos"] = (2015, 2018)
    at.run()
    next(b for b in at.button if b.label == "Limpar filtros").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state["f_rpas"] == []
    assert tuple(at.session_state["f_anos"]) == PERIODO_PADRAO
