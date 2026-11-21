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
| Risco | dois subcritérios de mesmo peso, dos atendimentos da Defesa Civil pedidos pelo cidadão: volume por ano e taxa por mil habitantes por ano (um atendimento = mesmo endereço, dia e serviço; conta uma vez mesmo com várias ações) | Defesa Civil, 2021–2024 |
| Vulnerabilidade | dois subcritérios de mesmo peso: % da população em favelas e comunidades urbanas; renda nominal média mensal dos responsáveis pelos domicílios (invertida: renda menor = mais prioridade) | IBGE, Censo 2022 (renda: Agregados por bairros, V06004, maio de 2026) |
| Atraso | % dos pedidos abertos que já passaram do p90 da própria categoria | 156, arquivos 2025–2026; p90 dos atendidos de 2021–2025 |
| Reincidência | % dos pedidos em local + serviço repetido | 156, 2021–2025, endereços com número |

O critério "impacto político" (autoria do vereador), que apareceu numa conversa exploratória com outra IA, foi
deixado de fora: priorizar por quem pediu é questionável em política pública (ver `ahp-e-priorizacao.md` na pasta
Contexto do Drive).

Cada bairro recebe, em cada critério, a sua **posição relativa** (percentil, de 0 a 1) entre os 89 bairros. O índice
é a soma ponderada, uma nota de 0 a 10. Bairro sem dado num critério recebe 0 nele.

## Hierarquia (atualizada em 17/11 e 20/11/2026)

Vulnerabilidade (17/11) e Risco (20/11) ganharam um nível a mais na hierarquia, cada um com dois subcritérios:

```
Prioridade do bairro
├── Risco ............................ 45,5%
│     ├── volume de atendimentos (½) . 22,77%
│     └── taxa por mil hab. (½) ...... 22,77%
├── Vulnerabilidade .................. 26,3%
│     ├── % em favela (½) ............ 13,14%
│     └── renda média, invertida (½) . 13,14%
├── Atraso ........................... 14,1%
└── Reincidência ..................... 14,1%
```

As notas de risco e de vulnerabilidade são a média das duas posições de cada um:
r_R(b) = ½ · r_volume(b) + ½ · r_taxa(b) e r_V(b) = ½ · r_favela(b) + ½ · r_renda(b), em que r_renda ordena da maior
renda para a menor. Em cada critério, o julgamento entre os dois subcritérios é 1 (igual importância), o que dá ½ e ½
e RC = 0.

**Por que a renda entrou:** 19 bairros têm 0% da população em favela pelo recorte do IBGE, entre eles morros antigos
e bairros pobres. Só com esse indicador, eles ficavam com a nota mínima de vulnerabilidade. A renda média corrige
isso sem mudar os pesos dos quatro critérios. A correlação entre o ranking novo e o anterior é 0,97, 8 dos 10
primeiros se mantêm, e bairros como Morro da Conceição, Totó, Mangabeira e Campina do Barreto sobem de 10 a 14
posições.

**Por que o risco ganhou dois subcritérios (20/11, sugestão da Profª Maíra na orientação de 17/11):** a taxa por mil
habitantes sozinha premia o bairro pequeno, em que poucos moradores inflam a conta; o volume sozinho premiaria o bairro
grande (a Cohab tem o maior volume, cerca de 2.200 atendimentos por ano). Juntos, um corrige o outro. Volume e taxa
andam parecido, mas não são a mesma coisa (correlação de postos de 0,84). Efeito: correlação de 0,97 com o ranking
anterior e os mesmos 10 primeiros; bairros grandes com muito atendimento sobem (Boa Viagem +21, Várzea +13, Pina +12) e
bairros pequenos com taxa inflada descem (Torreão −15; Cabanga, Derby e Apipucos −14).

## Como o risco é contado (atualizado em 17/11/2026)

A base aberta da Defesa Civil grava cada **ação** de um atendimento numa linha (vistoria, mapeamento da área,
atendimento social…). Em 2021–2024 são 80.498 ações do cidadão para 51.357 atendimentos, 1,6 ação por atendimento.
Contar linhas premiava o bairro em que um único atendimento gerou muitas ações: em Mangabeira, 49 das 53 ações são
mapeamentos no mesmo endereço e no mesmo dia. Agora o risco conta **atendimentos** (mesmo endereço pseudonimizado, mesmo
dia, mesmo serviço). A taxa passa a ir de 0,1 a 60 por mil habitantes por ano (mediana 1,3; o máximo é Dois Irmãos).

Efeito: correlação de 0,97 com o ranking anterior; os 10 primeiros são os mesmos, só muda a ordem entre eles.
Mangabeira cai 38 posições; Bongi, Pina e Rosarinho caem de 12 a 17; Casa Forte e Porto da Madeira, 8.
O mapa da Defesa Civil na página Território continua mostrando ações, como na EDA (N3).

Ficaram fora do critério, de propósito: o monitoramento por iniciativa da própria Defesa Civil (PROATIVA) e as ações
sem serviço registrado (INDEFINIDA: atendimento social, porta a porta, roçagem, cestas básicas). O critério mede a
demanda do cidadão.

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

Top 5 com esses pesos (com a renda e o risco em volume e taxa por atendimento): Guabiraba, Dois Irmãos, Passarinho,
São José, Jordão. Antes da renda, o quinto era Apipucos; com a renda e o risco só por taxa de ações, Linha do Tiro; com
a taxa por atendimento, Beberibe.

**Sensibilidade:** multiplicando o peso de cada critério por 0,5, 0,75, 1,25 ou 1,5 (e redistribuindo o resto), 6 a 10
dos 10 primeiros continuam no top 10. Os casos mais sensíveis são reduzir à metade o peso do risco (6 de 10) e o da
vulnerabilidade (8 de 10). Os pesos internos do risco e da vulnerabilidade (½ e ½) ficam fixos no teste. O ranking
continua razoavelmente estável. (Antes da renda, o intervalo era de 7 a 10.)

## Limites e próximos passos

1. **Validar os julgamentos** com a Profª Maíra, o Prof. Marcelo e, se possível, quem opera a Defesa Civil e a Emlurb.
   A página deixa refazer as comparações e ver o efeito na hora.
2. Risco e vulnerabilidade se correlacionam em parte: bairros de morro somam pontos nos dois. Com a renda, a
   correlação entre as notas dos dois critérios fica em ρ ≈ 0,49.
3. O índice é por bairro e retrospectivo. Um índice **por pedido aberto** (para ordenar a fila) precisaria de um
   critério de criticidade por serviço, que depende de julgamento da Prefeitura.
4. AHP não é aprendizado de máquina e não conta como o bônus de modelagem preditiva. Uma classificação supervisionada
   de risco (grau R1–R4 da Defesa Civil/SEDEC) poderia servir para comparar com os pesos.
