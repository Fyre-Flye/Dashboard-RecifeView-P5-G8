import pandas as pd

from src.filtros import Filtros


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
