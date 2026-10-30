"""Constantes do painel: cores da identidade RecifeView, nomes de exibição e o tema dos gráficos Altair."""

import altair as alt

# Identidade RecifeView (AssetsVisuais/PaletaDeCores.txt) e a rampa de azuis usada na EDA (N3)
AZUL = "#0F62FE"
NAVY = "#062A5F"
AZUL70 = "#5B93FE"
AZUL40 = "#9FC0FF"
AZUL25 = "#C6DAFF"
CLARO = "#EAF2FF"
TEXTO = "#111111"
TEXTO_SECUNDARIO = "#4A4F5C"
CINZA = "#8C8C8C"
GRADE = "#E3ECFB"
DESTAQUE = "#E8590C"      # laranja de ênfase, usado só para chamar atenção a um ponto

FONTE = "Montserrat, sans-serif"

# Uma cor por fonte de dados (identidade, não ordem). Paleta conferida com o validador de cores do
# skill de dataviz: separação para daltonismo (ΔE ≥ 8) e contraste ≥ 3:1 sobre o fundo branco.
NOMES_FONTE = {
    "156_EMLURB": "Central 156 / Emlurb",
    "DEFESA_CIVIL": "Defesa Civil",
    "OUVIDORIA": "Ouvidoria",
    "SEDEC_CHAMADOS": "SEDEC (áreas de risco)",
    "CAMARA_REQUERIMENTOS": "Câmara (vereadores)",
}
CORES_FONTE = {
    "Central 156 / Emlurb": AZUL,
    "Defesa Civil": DESTAQUE,
    "Ouvidoria": "#1B998B",
    "SEDEC (áreas de risco)": "#9A3FB8",
    "Câmara (vereadores)": "#B8860B",
}
ESCALA_FONTE = alt.Scale(domain=list(CORES_FONTE), range=list(CORES_FONTE.values()))

# Rampa sequencial de um só matiz (claro -> escuro) para magnitude nos mapas e no mapa de calor
RAMPA = [CLARO, AZUL25, AZUL40, AZUL70, AZUL, NAVY]

ANO_MIN, ANO_MAX = 2012, 2026
ANOS_PARCIAIS = {2026: "2026 vai só até o download das bases (07/10/2026)",
                 2025: "2025: Ouvidoria só tem parte do ano e a Defesa Civil publicou o arquivo vazio"}

AVISO_IA = ("Esta entrega foi auxiliada por IA (Claude, Anthropic); o grupo revisou o conteúdo. "
            "Dados abertos da Prefeitura do Recife, Câmara Municipal e IBGE.")


def tema_recifeview():
    eixo = {"labelFont": FONTE, "titleFont": FONTE, "labelColor": TEXTO_SECUNDARIO, "titleColor": TEXTO_SECUNDARIO,
            "titleFontWeight": 600, "labelFontSize": 11, "titleFontSize": 11, "gridColor": GRADE,
            "domainColor": AZUL25, "tickColor": AZUL25}
    return {
        "config": {
            "font": FONTE,
            "background": "transparent",
            "view": {"stroke": None},
            "title": {"font": FONTE, "fontSize": 14, "fontWeight": 700, "color": TEXTO, "anchor": "start",
                      "subtitleFont": FONTE, "subtitleColor": TEXTO_SECUNDARIO, "subtitleFontSize": 11},
            "axis": eixo,
            "axisX": {"grid": False},
            "legend": {"labelFont": FONTE, "titleFont": FONTE, "labelColor": TEXTO, "titleColor": TEXTO_SECUNDARIO,
                       "labelFontSize": 11, "titleFontSize": 11, "orient": "top", "titleOrient": "left"},
            "header": {"labelFont": FONTE, "titleFont": FONTE},
            "text": {"font": FONTE, "color": TEXTO},
            "bar": {"color": AZUL, "cornerRadiusEnd": 3},
            "line": {"color": AZUL, "strokeWidth": 2},
            "point": {"color": AZUL, "size": 60, "filled": True},
            "range": {"category": list(CORES_FONTE.values()), "heatmap": RAMPA, "ramp": RAMPA},
        }
    }


def formato_br(campo: str = "datum.value", fmt: str = ",.0f") -> str:
    """Expressão Vega que formata um número no padrão brasileiro (1.234,5).

    O Streamlit desenha os gráficos com o formato americano (1,234.5) e não aceita trocar o locale.
    A expressão troca todos os separadores: ',' -> '_' -> '.', e '.' -> ','.
    """
    texto = f"format({campo}, '{fmt}')"
    return f"join(split(join(split(join(split({texto}, ','), '_'), '.'), ','), '_'), '.')"


def eixo_numero(titulo: str | None = None, fmt: str = ",.0f", **kwargs) -> alt.Axis:
    return alt.Axis(title=titulo, labelExpr=formato_br(fmt=fmt), **kwargs)


def registrar_tema() -> None:
    alt.theme.register("recifeview", enable=True)(tema_recifeview)


# As fontes publicam nomes em maiúsculas e sem acento. Para exibir, devolvemos acentos às palavras comuns.
_ACENTOS = {
    "PAVIMENTACAO": "pavimentação", "ILUMINACAO": "iluminação", "PUBLICA": "pública", "PRACAS": "praças",
    "TRANSITO": "trânsito", "SINALIZACAO": "sinalização", "ARBORIZACAO": "arborização", "FISCALIZACAO": "fiscalização",
    "PROVISORIA": "provisória", "LUMINARIAS": "luminárias", "DENUNCIAS": "denúncias", "VAO": "vão",
    "CONSERVACAO": "conservação", "MANUTENCAO": "manutenção", "EDUCACAO": "educação", "SAUDE": "saúde",
    "AGUA": "água", "ESGOTO": "esgoto", "PODA": "poda", "URBANISTICO": "urbanístico", "ANIMAIS": "animais",
    "SERVICOS": "serviços", "INFORMACAO": "informação", "RECLAMACAO": "reclamação", "SOLICITACAO": "solicitação",
    "DENUNCIA": "denúncia", "SUGESTAO": "sugestão", "VISTORIA": "vistoria", "ACAO": "ação", "PROTECAO": "proteção",
    "CALCADAS": "calçadas", "ARVORES": "árvores", "NECROPOLES": "necrópoles", "MOBILIARIO": "mobiliário",
    "REPOSICAO": "reposição", "VEICULO": "veículo", "SEMAFOROS": "semáforos", "EMPREL": "Emprel", "LAMPADA": "lâmpada", "LAMPADAS": "lâmpadas",
    "PUBLICO": "público", "CAPINACAO": "capinação", "IMPLANTACAO": "implantação", "LUMINARIA": "luminária",
    "MUDANCA": "mudança", "ASFALTICO": "asfáltico", "PRACA": "praça", "RECUPERACAO": "recuperação",
    "PARALELEPIPEDO": "paralelepípedo", "REMOCAO": "remoção", "POCO": "poço", "PRE-MOLDADOS": "pré-moldados",
    "FITOSSANITARIO": "fitossanitário", "VIA": "via",
}
_SIGLAS = {"EMLURB", "URB", "CTTU", "SEINFRA", "SEDEC", "COMPESA", "SEGOV", "EMPREL", "CONVIVA", "RECIPREV", "COMDICA"}


def nome_categoria(texto) -> str:
    """'ILUMINACAO PUBLICA' -> 'Iluminação pública'."""
    if texto is None or texto != texto:
        return "—"
    palavras = [_ACENTOS.get(p, p.lower()) for p in str(texto).replace("/", " / ").split()]
    frase = " ".join(palavras).replace(" / ", "/")
    return frase[:1].upper() + frase[1:]


def nome_orgao(texto) -> str:
    """Mantém siglas em maiúsculas e encurta nomes compostos: 'SEINFRA/INFRAESTRUTURA' -> 'SEINFRA'."""
    if texto is None or texto != texto:
        return "—"
    primeiro = str(texto).split("/")[0].strip()
    return primeiro if primeiro in _SIGLAS else nome_categoria(primeiro)


# Títulos em "Title Case" à brasileira: palavras com inicial maiúscula, menos artigos, preposições,
# contrações e conjunções curtas no meio do título ("Onde o Pedido se Perde").
_MINUSCULAS = {"a", "o", "as", "os", "e", "ou", "de", "da", "do", "das", "dos", "em", "na", "no", "nas", "nos",
               "por", "pela", "pelo", "para", "com", "ao", "aos", "à", "às", "um", "uma", "se", "que", "x", "×"}


def titulo(texto: str) -> str:
    """'Onde o pedido se perde' -> 'Onde o Pedido se Perde'. Siglas e números ficam como estão."""
    palavras = texto.split(" ")
    resultado = []
    for i, p in enumerate(palavras):
        if not p or not p[0].isalpha() or (p.isupper() and len(p) > 1):
            resultado.append(p)                      # número, sigla (AHP, RPA, H4) ou símbolo
        elif i > 0 and p.lower() in _MINUSCULAS and not resultado[-1].endswith((":", "·", ".")):
            resultado.append(p.lower())
        else:
            resultado.append("/".join(parte[:1].upper() + parte[1:] for parte in p.split("/")))
    return " ".join(resultado)
