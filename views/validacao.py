import altair as alt
import pandas as pd
import streamlit as st

from src import metricas, tendencia
from src.componentes import leitura, regua
from src.config import AZUL, CINZA, DESTAQUE
from src.dados import tabela

st.title("Testes e Validação")
st.markdown("O que mudou no painel depois de **uso real e do feedback recebido**: o que a orientadora validou, os "
            "problemas que apareceram usando o painel e foram corrigidos, e o que ainda será refinado antes da "
            "apresentação pública. A principal fonte de feedback foi a orientação com a **Profª Maíra Farias em "
            "17/11/2026** (gravada com autorização); as recomendações estão resumidas abaixo. Os outros itens vieram do "
            "uso do próprio grupo.")


def tabela_texto(linhas: list[tuple], colunas: list[str], altura: int = 90) -> None:
    st.dataframe(pd.DataFrame(linhas, columns=colunas), hide_index=True, width="stretch", row_height=altura,
                 height=altura * len(linhas) + 40,   # todas as linhas à vista, sem rolagem interna
                 column_config={c: st.column_config.TextColumn(width="large") for c in colunas[1:]})


# --- 1. Validado --------------------------------------------------------------------------------------------
st.subheader("1. O Que Foi Validado com a Orientadora",
             help="Pontos que a Profª Maíra viu funcionando no painel e aprovou, ou sugeriu e já foram aplicados.")
tabela_texto([
    ("AHP para priorizar", "Aprovou a abordagem: o AHP é um método consolidado e útil para a Prefeitura, porque deixa a "
     "prioridade explícita e auditável.", "Validado"),
    ("Ocorrências classificadas (Prioridade, aba 2)", "Leu com o grupo a nota de pedidos reais e entendeu por que cada um "
     "subiu (risco do bairro, atraso e reincidência). Gostou do gráfico e sugeriu melhorar o visual.",
     "Validado; visual a refinar"),
    ("Vulnerabilidade com dois subcritérios", "Recomendou separar a vulnerabilidade por renda da vulnerabilidade por "
     "favela, porque medem coisas diferentes e não caminham juntas.", "Aplicado em 17/11"),
    ("Risco com dois subcritérios", "Observou que o risco reunia coisas demais num número só e recomendou dividi-lo em "
     "subcritérios: volume de ações e ações por habitante.", "Aplicado em 20/11"),
    ("Avaliar dados ausentes dos indicadores", "Recomendou conferir os dados ausentes de cada indicador antes de usá-lo no "
     "AHP: um indicador com muita falta não serve de critério.", "Aplicado em 20/11 (tabela na aba Método da Prioridade)"),
    ("Data de referência fixa", "Lembrou que o atraso deve contar até a data em que os dados foram baixados, e não até o "
     "dia de hoje.", "Já era assim; confirmado"),
    ("Bairros fora do índice em cinza", "Entendeu sem explicação que o cinza é ausência de nota (menos de 1.000 "
     "moradores).", "Validado"),
], ["Item", "O que a orientadora recomendou ou observou", "Situação"])

# --- 2. Corrigido por uso -------------------------------------------------------------------------------------
st.subheader("2. Problemas Encontrados no Uso e Corrigidos",
             help="Defeitos e confusões que apareceram usando o painel, com a correção feita.")
tabela_texto([
    ("30/10", "No teste de ponta a ponta, o clique no mapa do Território, o botão de restaurar os pesos do AHP e o "
     "\"Limpar filtros\" não funcionavam.", "Corrigidos, cada um com teste automático."),
    ("13/11", "Gráficos com muitas barras finas eram difíceis de ler com o mouse (precisão de agulha).",
     "Régua tracejada que acompanha o mouse, na vertical e na horizontal, em todos os gráficos com eixo."),
    ("14/11", "Na simulação da chuva, não ficava claro o que era a faixa amarela nem quanto tempo a Emlurb teria para "
     "se preparar.", "Faixa rotulada como previsão (dias antes da chuva), começo da sobrecarga marcado e botão de "
     "recomeçar."),
    ("17/11", "Pau Ferro, Recife, Santo Antônio, Ilha do Leite e Paissandu sumiam do mapa da Prioridade, e bairros "
     "sem pedido atrasado sumiam do mapa do Painel Geral em datas antigas.", "Fundo cinza sob a camada colorida: bairro "
     "sem valor fica cinza e com nome na dica."),
    ("17/11", "Morros antigos (Morro da Conceição, Alto do Mandu, Totó) tinham 0% de favela pelo IBGE e ficavam com "
     "vulnerabilidade mínima.", "Renda média do Censo 2022 como segundo subcritério; renda também no Território."),
    ("17/11", "O risco de Mangabeira estava inflado: 49 das 53 ações eram um único mapeamento no mesmo endereço e dia.",
     "O risco passou a contar atendimentos (endereço, dia e serviço), não cada ação."),
], ["Quando", "O que apareceu", "Correção"])

# --- 3. A refinar -----------------------------------------------------------------------------------------------
st.subheader("3. O Que Ainda Será Refinado Antes da Apresentação",
             help="Sugestões recebidas e pontas soltas que ainda não entraram no índice, com o motivo.")
tabela_texto([
    ("Tendência do bairro em relação à cidade", "Sugestão da Profª Maíra. Prévia calculada abaixo; falta o grupo "
     "decidir se vira um quinto critério e com que peso, porque ela anda na direção contrária do risco.", "Grupo, com a orientadora"),
    ("Natureza da solicitação", "Dar nota ao tipo de pedido (deslizamento antes de plantio de árvore), com um "
     "dicionário de categorias montado por IA e conferido pelo grupo. A própria orientadora alertou para o risco de "
     "viés.", "Grupo"),
    ("Pesos do AHP", "Continuam uma proposta do grupo. Falta refazer as comparações com os professores e, se possível, "
     "com a Defesa Civil e a Emlurb.", "Grupo e especialistas"),
    ("Visual das ocorrências classificadas", "A orientadora gostou e sugeriu melhorar o visual.", "Grupo"),
    ("Dados da Defesa Civil", "A base aberta para em 2024 e nov.–dez. de 2024 estão incompletos. Alto do Mandu tem "
     "poucos atendimentos na Defesa Civil, mas está no percentil 0,73 na SEDEC: pode haver registro sob outro bairro.",
     "Pedido de dados à Prefeitura"),
    ("Ilha do Retiro", "39% da população em favela e renda média de R$ 8.967: combinação rara, a conferir no Censo.",
     "Grupo"),
], ["Item", "Situação e motivo", "Quem decide"])

st.subheader("Fora do Escopo do Projeto 5", help="Ideias registradas para continuar no Projeto 6 ou depois.")
leitura("Aprendizado de máquina: a orientadora recomendou focar na entrega do Projeto 5. Um classificador (árvore de "
        "decisão, regressão logística) precisaria de rótulos de prioridade que não existem; usar o próprio AHP como "
        "rótulo seria circular. O caminho sugerido para depois é agrupar os bairros com k-means sobre os mesmos "
        "indicadores, normalizados. Chuva por região da cidade (zonas Norte, Sul, Leste e Oeste) como parte do risco e o "
        "disparo automático dos dois avisos da página Chuva e Carga também ficam como trabalho futuro.")

# --- 4. Prévia da tendência --------------------------------------------------------------------------------------
st.subheader("4. Prévia: Tendência do Bairro em Relação à Cidade",
             help="Candidato a quinto critério do AHP, sugerido pela orientadora. Ainda não entra no índice.")
st.markdown("Os pedidos ao 156 crescem na cidade inteira também porque ficou mais fácil pedir. Para separar isso de um "
            "bairro que piora, a conta usa a **fatia do bairro no total da cidade**, ano a ano, e mede a inclinação "
            "dessa fatia: positivo = o bairro cresce mais que a cidade; negativo = cresce menos ou cai. A janela padrão "
            "começa em 2021, início da gestão atual da Prefeitura, e pode ser mudada.")
demanda = tabela("demanda")
ind = tabela("indicadores_bairro").set_index("bairro_oficial")
anos = st.slider("Janela de anos", 2013, 2025, (2021, 2025), help="Anos completos do 156 usados na tendência.")
if anos[1] - anos[0] < 2:
    st.warning("Escolha pelo menos três anos para medir uma tendência.")
else:
    t = tendencia.tendencia_relativa(tendencia.parcela_anual(demanda, "156_EMLURB", anos)).reindex(ind.index)
    dados = pd.DataFrame({"nome": ind["nome"], "tendencia": t * 100}).dropna().sort_values("tendencia")
    extremos = pd.concat([dados.head(10), dados.tail(10)])
    extremos["sentido"] = extremos["tendencia"].map(lambda v: "cresce mais que a cidade" if v > 0 else "cresce menos ou cai")
    extremos["txt"] = extremos["tendencia"].map(lambda v: f"{'+' if v > 0 else ''}{metricas.numero(v, 1)}% ao ano")
    barras = alt.Chart(extremos).mark_bar().encode(
        x=alt.X("tendencia:Q", title="variação da fatia do bairro na cidade (% ao ano)"),
        y=alt.Y("nome:N", sort=extremos["nome"].tolist()[::-1], title=None,
                axis=alt.Axis(labelLimit=220, labelOverlap=False)),
        color=alt.Color("sentido:N", title=None, scale=alt.Scale(domain=["cresce mais que a cidade", "cresce menos ou cai"],
                                                                 range=[DESTAQUE, AZUL]),
                        legend=alt.Legend(orient="top", labelLimit=300)),
        tooltip=[alt.Tooltip("nome:N", title="Bairro"), alt.Tooltip("txt:N", title="Tendência")])
    zero = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color=CINZA).encode(x="x:Q")
    st.altair_chart((barras + zero + regua(barras, "y")).properties(height=alt.Step(24)), width="stretch")
    # Correlação de postos (Spearman) feita à mão: a do pandas exige o scipy, que o deploy não instala.
    correl = t.rank().corr(ind["taxa_defesa_civil"].rank())
    leitura(f"Os 10 bairros que mais ganham e os 10 que mais perdem fatia nos pedidos ao 156, entre os 89 do índice "
            f"({anos[0]}–{anos[1]}). A correlação de postos com a taxa de risco é {metricas.numero(correl, 2)}: esse indicador "
            "costuma puxar para cima bairros diferentes dos que o risco já coloca no topo. Por isso ainda não entrou no "
            "índice. Cuidado ao ler uma queda: menos pedidos pode ser melhora, mas também pode ser gente que desistiu de "
            "pedir. Medida da Emlurb no 156; a Defesa Civil fica de fora porque só vai até 2024.")
