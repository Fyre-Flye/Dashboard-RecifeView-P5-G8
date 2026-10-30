# Índice de prioridade por bairro (AHP): critérios, julgamentos e resultado

Sugestão da Profª Maíra (19/10/2026): priorizar as denúncias com o **AHP** (Analytic Hierarchy Process, Saaty),
como alternativa a classificadores complexos, e mostrar o resultado num mapa do Recife. O código está em
`src/ahp.py` (com testes em `tests/test_ahp.py`) e a página em `views/prioridade.py`.

## Objetivo, critérios e alternativas

- **Objetivo:** decidir em quais bairros a retaguarda deve agir primeiro.
- **Alternativas:** os 89 bairros com 1.000 moradores ou mais (os menores distorcem a taxa por habitante, como na EDA).
- **Critérios** (os candidatos que saíram da EDA, N3 seção 8.2):

| Critério | Indicador | Fonte e janela |
|---|---|---|
| Risco | ações da Defesa Civil pedidas pelo cidadão por mil habitantes por ano | Defesa Civil, 2021–2024 |
| Vulnerabilidade | % da população em favelas e comunidades urbanas | IBGE, Censo 2022 |
| Atraso | % dos pedidos abertos que já passaram do p90 da própria categoria | 156, arquivos 2025–2026; p90 dos atendidos de 2021–2025 |
| Reincidência | % dos pedidos em local + serviço repetido | 156, 2021–2025, endereços com número |

O critério "impacto político" (autoria do vereador), que apareceu numa conversa exploratória com outra IA, foi
deixado de fora: priorizar por quem pediu é questionável em política pública (ver `ahp-e-priorizacao.md` na pasta
Contexto do Drive).

Cada bairro recebe, em cada critério, a sua **posição relativa** (percentil, de 0 a 1) entre os 89 bairros. O índice
é a soma ponderada, uma nota de 0 a 10. Bairro sem dado num critério recebe 0 nele.

## Julgamentos padrão (proposta inicial do grupo, NÃO validada)

Escala de Saaty: 1 = igual, 3 = moderadamente, 5 = fortemente, 7 = muito, 9 = extremamente mais importante.

| Par | Julgamento | Por quê (hipótese para discussão) |
|---|---|---|
| Risco × Vulnerabilidade | Risco 2× | risco é ameaça à vida e ao patrimônio; vulnerabilidade agrava, mas não é urgência por si |
| Risco × Atraso | Risco 3× | um deslizamento não espera; atraso de serviço urbano costuma ser reversível |
| Risco × Reincidência | Risco 3× | idem |
| Vulnerabilidade × Atraso | Vulnerabilidade 2× | o mesmo problema pesa mais onde a capacidade de se recuperar é menor; o volume de pedidos não mostra isso |
| Vulnerabilidade × Reincidência | Vulnerabilidade 2× | idem |
| Atraso × Reincidência | igual | os dois medem falha de atendimento no 156 |

**Resultado:** Risco 45,5% · Vulnerabilidade 26,3% · Atraso 14,1% · Reincidência 14,1%; **RC = 0,4%** (coerente).

Top 5 com esses pesos: Guabiraba, Dois Irmãos, São José, Passarinho, Apipucos.

**Sensibilidade:** multiplicando o peso de cada critério por 0,5, 0,75, 1,25 ou 1,5 (e redistribuindo o resto), 7 a 10
dos 10 primeiros continuam no top 10. Os casos mais sensíveis (7 de 10) são reduzir o peso do risco (× 0,5 ou × 0,75)
e aumentar o da reincidência (× 1,5). O ranking é razoavelmente estável.

## Limites e próximos passos

1. **Validar os julgamentos** com a Profª Maíra, o Prof. Marcelo e, se possível, quem opera a Defesa Civil e a Emlurb.
   A página deixa refazer as comparações e ver o efeito na hora.
2. Risco e vulnerabilidade se correlacionam em parte (ρ ≈ 0,37): bairros de morro somam pontos nos dois.
3. O índice é por bairro e retrospectivo. Um índice **por pedido aberto** (para ordenar a fila) precisaria de um
   critério de criticidade por serviço, que depende de julgamento da Prefeitura.
4. AHP não é aprendizado de máquina e não conta como o bônus de modelagem preditiva. Uma classificação supervisionada
   de risco (grau R1–R4 da Defesa Civil/SEDEC) poderia servir para comparar com os pesos.
