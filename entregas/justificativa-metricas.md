# Justificativa das métricas (KPIs) do painel

Modelo da prática de Streamlit de AVD: para cada métrica, a variável, o que mede, por que foi escolhida, o público,
a decisão que ela apoia e o que comunica. Cada página tem de 3 a 5 KPIs, todos recalculados com os filtros da barra
lateral (período, RPA, bairro e categoria).

**Público-alvo comum:** quem gerencia a retaguarda das demandas do cidadão no Recife: a triagem da Ouvidoria e os
gestores dos órgãos executores (Emlurb, URB, Seinfra, Defesa Civil). São pessoas que precisam decidir o que fazer
primeiro, sem ler distribuições ou matrizes.

Os números citados abaixo são do recorte padrão (2021–2025, cidade inteira).

## Início

### Demandas registradas
- **Variável:** contagem de registros das cinco fontes (`demanda.parquet`, coluna `n`); na Defesa Civil, só `iniciativa = CIDADAO`.
- **O que mede:** o volume que chega por todas as portas no recorte (872.716).
- **Por que foi escolhida:** é o contexto das demais; mostra o tamanho do problema e o peso de cada porta.
- **Decisão que apoia:** dimensionar a triagem e comparar regiões e períodos.
- **O que comunica:** "chegam cerca de 175 mil demandas por ano, por cinco portas que não se conversam".

### Indicações respondidas
- **Variável:** `camara_indicacoes.respondida` (resposta registrada na tramitação da Câmara).
- **O que mede:** a parte das indicações de vereadores que volta com resposta da Prefeitura (21%), ao lado da parte enviada (97%).
- **Por que foi escolhida:** é a única medida pública do caminho de volta, e resume a hipótese central (H2): a perda está depois da entrada.
- **Decisão que apoia:** priorizar a integração do retorno (sistema de envio) sobre novos canais de entrada.
- **O que comunica:** "quase tudo chega; 1 em cada 5 volta com resposta registrada".

### Local repetido (156)
- **Variável:** `reincidencia_156.repetidos / registros` (chave local + serviço, 2015–2025, endereço com número).
- **O que mede:** quanto da demanda cai num ponto que já teve pedido do mesmo serviço (52%).
- **Por que foi escolhida:** volume bruto esconde que um ponto com 100 chamados é um problema, não cem (H3).
- **Decisão que apoia:** tratar pontos crônicos com solução definitiva e juntar duplicidades na triagem.
- **O que comunica:** "metade dos pedidos é sobre um problema que já tinha sido pedido".

### Prazo do 156 (p90)
- **Variável:** `prazos_156.dias` ponderado por `n` (pedidos atendidos).
- **O que mede:** o prazo que 90% dos atendidos não ultrapassam (60 dias), com a mediana como contexto (4 dias).
- **Por que foi escolhida:** a média engana numa distribuição tão assimétrica (média ≈ 10 × mediana, N3); o p90 é o que mais piorou (H4).
- **Decisão que apoia:** definir metas de prazo pela cauda e por categoria.
- **O que comunica:** "a maioria resolve rápido, mas 1 em cada 10 espera dois meses ou mais".

## Retorno e fragmentação

| KPI | Variável | O que mede | Decisão que apoia |
|---|---|---|---|
| Indicações de vereadores | contagem de `camara_indicacoes` | volume de pedidos formais à Prefeitura | dimensionar o fluxo Câmara → Prefeitura |
| Chegam à Prefeitura | `enviada` | % com envio registrado (97%) e mediana de dias para enviar (9) | mostrar que a Câmara não é o gargalo |
| Voltam com resposta | `respondida` | % com resposta registrada (21%) | cobrar o registro do retorno por órgão |
| Tempo até a resposta | mediana de `dias_ate_resposta` | quanto demora quando volta (241 dias) | definir prazo de retorno |

Comunica, junto do funil: a perda acontece dentro da Prefeitura, e melhora quando o envio é por sistema (H9).

## Reincidência

| KPI | Variável | O que mede | Decisão que apoia |
|---|---|---|---|
| Em local repetido | `repetidos / registros` | % em chave repetida (com opção de tirar endereços genéricos acima do p99) | onde investir em solução definitiva |
| O problema voltou | `intervalo_reincidencia` | % das repetições com 30+ dias de intervalo (60%) | revisar a qualidade do serviço executado |
| Pedido em dobro | `intervalo_duplicidade` | % das repetições em até 7 dias (23%) | juntar pedidos duplicados na triagem |
| Pontos crônicos | `locais_cronicos_156.pedidos ≥ 10` | quantos locais têm 10+ pedidos do mesmo serviço | lista de vistoria |

## Prazos

| KPI | Variável | O que mede | Decisão que apoia |
|---|---|---|---|
| Metade é atendida em até | mediana de `dias` | o prazo típico (4 dias) | referência geral |
| 1 em cada 10 leva mais de | p90 de `dias` | a cauda longa (60 dias) | meta de prazo |
| Fechados no mesmo dia | % de `dias = 0` | encerramento administrativo (14%) | separar fechamento de execução |
| Mais de 90 dias | % de `dias > 90` | pedidos que ficaram meses (6,8%) | foco da fila |

Mais o estoque aberto (arquivos 2025–2026): pedidos abertos e % que já passou do p90 da própria categoria (54%).

## Território

O detalhe do bairro clicado traz população e % em favela, pedidos ao 156 e ações da Defesa Civil (volume e taxa
por mil habitantes), % em local repetido e % do estoque aberto fora do prazo. A taxa por habitante vem sempre ao
lado do volume, porque bairro grande pede mais só por ser grande, e bairro central e pequeno recebe pedidos de quem
circula (N3, 6.2).

## Prioridade (AHP)

- **Razão de consistência (RC):** coerência dos julgamentos par a par; acima de 10% os pesos não devem ser usados.
- **Pesos dos critérios:** resultado das comparações; aparecem em barras para qualquer pessoa conferir.
- **Índice de prioridade (0 a 10) e posição:** soma ponderada das posições relativas do bairro em cada critério.
- **Bairros mantidos no top 10 (sensibilidade):** se o ranking muda muito quando um peso muda. Apoia a decisão de
  quanto investir na validação dos pesos com especialistas.

Detalhes do método e dos julgamentos em [ahp-julgamentos.md](ahp-julgamentos.md).
