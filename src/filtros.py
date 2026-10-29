"""Filtros globais da barra lateral.

Os widgets são desenhados no app.py (antes da página), então o valor escolhido continua valendo
quando a pessoa troca de página. Cada página lê os filtros com `atuais()` e aplica só os que fazem
sentido para as suas fontes, dizendo isso numa legenda (`legenda()`).
"""

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from src.config import ANO_MAX, ANO_MIN, nome_categoria
from src.dados import categorias_156, tabela

PERIODO_PADRAO = (2021, 2025)     # recorte comum da EDA (N3): todas as fontes têm dado


@dataclass(frozen=True)
class Filtros:
    anos: tuple[int, int]
    rpas: tuple[str, ...]
    bairros: tuple[str, ...]
    categorias: tuple[str, ...]

    @property
    def territorio_ativo(self) -> bool:
        return bool(self.rpas or self.bairros)

    def aplicar(self, df: pd.DataFrame, ano: bool = True, territorio: bool = True, categoria: bool = True) -> pd.DataFrame:
        mascara = pd.Series(True, index=df.index)
        if ano and "ano" in df:
            mascara &= df["ano"].between(*self.anos)
        if territorio and self.rpas and "rpa" in df:
            mascara &= df["rpa"].isin(self.rpas)
        if territorio and self.bairros and "bairro_oficial" in df:
            mascara &= df["bairro_oficial"].isin(self.bairros)
        if categoria and self.categorias and "categoria" in df:
            mascara &= df["categoria"].isin(self.categorias)
        return df[mascara]


def desenhar_barra_lateral() -> None:
    bairros = tabela("bairros").sort_values("nome")
    with st.sidebar:
        st.subheader("Filtros")
        st.slider("Período", ANO_MIN, ANO_MAX, PERIODO_PADRAO, key="f_anos",
                  help="Ano de abertura do pedido. 2025 e 2026 são parciais em algumas fontes (veja 'Sobre os dados').")
        st.multiselect("RPA", [str(i) for i in range(1, 7)], key="f_rpas", placeholder="Todas",
                       format_func=lambda r: f"RPA {r}",
                       help="Região Político-Administrativa. Vazio = todas.")
        rpas = st.session_state.get("f_rpas") or []
        opcoes = bairros[bairros["rpa"].isin(rpas)] if rpas else bairros
        nomes = dict(zip(bairros["bairro_oficial"], bairros["nome"]))
        st.multiselect("Bairro", opcoes["bairro_oficial"].tolist(), key="f_bairros", placeholder="Todos",
                       format_func=nomes.get)
        st.multiselect("Categoria de serviço", categorias_156(), key="f_categorias", placeholder="Todas",
                       format_func=nome_categoria,
                       help="Grupos de serviço do 156. Na Câmara, a categoria foi inferida da ementa.")
        if st.button("Limpar filtros", width="stretch"):
            for chave in ("f_rpas", "f_bairros", "f_categorias"):
                st.session_state[chave] = []
            st.session_state["f_anos"] = PERIODO_PADRAO
            st.rerun()


def atuais() -> Filtros:
    s = st.session_state
    return Filtros(
        anos=tuple(s.get("f_anos", PERIODO_PADRAO)),
        rpas=tuple(s.get("f_rpas") or ()),
        bairros=tuple(s.get("f_bairros") or ()),
        categorias=tuple(s.get("f_categorias") or ()),
    )


def legenda(f: Filtros, ignorados: dict[str, str] | None = None) -> None:
    """Mostra o recorte em uso e quais filtros a página não consegue aplicar (e por quê)."""
    partes = [f"{f.anos[0]}–{f.anos[1]}" if f.anos[0] != f.anos[1] else str(f.anos[0])]
    if f.rpas:
        partes.append("RPA " + ", ".join(f.rpas))
    if f.bairros:
        nomes = dict(zip(tabela("bairros")["bairro_oficial"], tabela("bairros")["nome"]))
        partes.append(", ".join(nomes.get(b, b) for b in f.bairros[:4]) + ("…" if len(f.bairros) > 4 else ""))
    if f.categorias:
        partes.append(", ".join(nome_categoria(c) for c in f.categorias[:3]) + ("…" if len(f.categorias) > 3 else ""))
    texto = "Recorte: " + " · ".join(partes)
    if ignorados:
        texto += "  \n" + " ".join(f"_{k}_: {v}" for k, v in ignorados.items())
    st.caption(texto)
