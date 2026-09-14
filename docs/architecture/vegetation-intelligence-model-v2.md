# Modelo multimodal de inteligência vegetal v2

- Status: proposta técnica; ainda não implementada
- Data: 2026-09-13
- Escopo: evolução do baseline explicável para monitoramento, previsão e priorização por segmento e zona
- Uso permitido nesta fase: desenvolvimento, avaliação offline e futuro modo sombra

## Resumo executivo

O modelo atual do ZENIT é uma regra de segurança, não um modelo preditivo. Ele
calcula NDVI, rejeita cenas de baixa qualidade ou dados não reais e somente
produz uma conclusão quando existe uma altura real medida. Esse comportamento é
correto para impedir falsa precisão, mas ainda não estima crescimento nem risco
futuro.

A evolução recomendada é uma pilha multimodal e versionada com quatro partes:

1. um gate de geometria, proveniência, qualidade e atualidade dos dados;
2. um baseline v2 auditável de estado e tendência, útil durante o cold start;
3. modelos supervisionados candidatos para altura, ultrapassagem de limiar e
   tempo até o limiar, treinados somente com medições reais elegíveis;
4. uma política operacional separada que converte evidência em `monitor`,
   `inspect` ou `mowing_review`, sempre com revisão humana.

PlanetScope deve complementar o Sentinel-2 com detalhe espacial e melhor
separação entre faixa vegetada, pavimento, solo, sombra e copa. Não deve substituir
a série Sentinel-2, ser convertido diretamente em centímetros ou autorizar
roçada. A hipótese a testar é que a fusão de Planet, Sentinel, clima, histórico e
campo reduz erro e incerteza em relação a qualquer fonte isolada.

Não é necessário contratar outra API paga para desenhar ou iniciar a fundação do
modelo. Para executar o pipeline multimodal serão necessários:

- `PL_API_KEY`, já prevista, para o acesso Planet autorizado pela conta;
- credenciais Copernicus, já previstas, para Sentinel-2 e futuramente Sentinel-1;
- uma fonte meteorológica histórica e de previsão. A opção de protótipo registrada
  no manual é Open-Meteo, sem segredo no desenho atual; NASA POWER pode servir de
  apoio regional. Termos, limites e endpoints devem ser confirmados antes da
  implementação produtiva.

O principal bloqueio não é outra API: é obter eixo e zonas oficiais, histórico de
serviço confiável e uma campanha longitudinal de alturas reais com protocolo de
medição. Sem isso, o ZENIT pode produzir indicadores e recomendações de inspeção,
mas não deve promover regressão de altura ou previsão de corte como operacional.

## Fontes consolidadas e conflitos resolvidos

Esta proposta consolida o texto fornecido sobre monitoramento e previsão, o
manual mestre, o estado atual do repositório, o plano de inteligência vegetal,
os relatórios de qualidade e as decisões ADR-0005, ADR-0006, ADR-0033, ADR-0066
e ADR-0067.

Quando o texto fornecido sugere segmentos experimentais de 10 a 50 m, prevalece
a regra de domínio do ZENIT: a unidade analítica é sempre o segmento de 100 m,
separado em `left`, `right`, `median` e `special`. Uma grade de 10 ou 20 m pode
existir internamente para pixels e features, mas nunca substitui a identidade do
segmento e da zona.

Também prevalecem estas regras:

- limite geral de 30 cm e limite de 10 cm para zonas especiais/operacionais;
- classes históricas N1 abaixo de 10 cm, N2 de 10 a 30 cm e N3 acima de 30 cm;
- NDVI, Planet, SAR, clima e score de confiança não são altura observada;
- baixa confiança normalmente gera inspeção;
- previsão, score ou recomendação nunca criam autorização de roçada;
- dados `prepared`, `estimated`, `simulated` ou `inconclusive` não podem ser
  usados como ground truth; dados demo/simulados não entram em treinamento nem
  em relatório oficial; features estimadas só podem ser usadas quando derivadas
  de fontes reais elegíveis, com método e linhagem reproduzíveis;
- a classificação histórica de 2025-03-28 não representa condição atual.

## Limitações do baseline atual

O endpoint `POST /v1/analysis/preview` implementa hoje:

- NDVI a partir de vermelho e infravermelho próximo;
- mínimo de 70% de pixels válidos;
- bloqueio de cenas não aceitáveis ou não reais;
- escolha do limiar de 10/30 cm pela zona;
- conclusão apenas quando uma altura real acompanha a observação;
- revisão humana obrigatória em todas as saídas.

Ele não possui ainda:

- série temporal por segmento/zona;
- bandas e índices além de NDVI;
- Planet, clima, relevo ou histórico de manutenção como features;
- previsão de altura, crescimento, ultrapassagem ou dias até o limiar;
- calibração de incerteza, detecção de extrapolação ou comparação de modelos;
- dataset elegível, treino reproduzível, model registry ou monitoramento de drift.

Portanto, o baseline deve permanecer como fallback de segurança. O v2 não deve
alterar silenciosamente suas garantias.

| Dimensão | Baseline atual | Evolução v2 |
| --- | --- | --- |
| Evidência espectral | NDVI de uma observação | bandas, índices, distribuição espacial e séries separadas por sensor |
| Contexto | altura real opcional | clima, sazonalidade, relevo, manutenção e campo |
| Planet | descoberta de catálogo | recortes controlados e features espaciais, após licença/cota e persistência |
| Tempo | estado pontual | tendência, janelas passadas e risco em 7/15/30 dias |
| Incerteza | faixa qualitativa fixa | qualidade por fonte, intervalo calibrado, detecção de extrapolação e abstention |
| Validação | regras unitárias | baselines, ablation, holdout espacial/temporal, model card e modo sombra |
| Operação | inspeção ou revisão com altura real | política separada, explicável e sempre subordinada à revisão humana |

## Objetivos de previsão

Os problemas devem ser separados para evitar targets ambíguos e vazamento de
informação.

### Estado atual

Saídas candidatas:

- distribuição estimada de altura, com mediana e intervalo em centímetros;
- probabilidade de ultrapassar o limiar aplicável na data de referência;
- classe N1/N2/N3 estimada, derivada da distribuição de altura e identificada
  como `estimated`, nunca confundida com a classe histórica observada;
- tipo de cobertura, apenas quando existir taxonomia e dataset aprovados;
- score de desenvolvimento/tendência enquanto altura não for promovida.

### Evolução

Saídas candidatas:

- tendência `decreasing`, `stable`, `increasing` ou `unknown`;
- taxa de crescimento somente quando suportada por observações reais repetidas;
- probabilidade de ultrapassar o limiar em 7, 15 e 30 dias;
- intervalo para dias até ultrapassar o limiar.

### Decisão operacional

A decisão operacional recebe as previsões, a criticidade da zona, a qualidade,
a atualidade e as políticas vigentes. Ela não deve ser o mesmo artefato do modelo
de vegetação.

Saídas permitidas:

- `monitor`: evidência suficientemente atual e abaixo do limiar, sem risco
  relevante dentro da janela aprovada;
- `inspect`: evidência insuficiente, conflitante, fora de distribuição, antiga ou
  próxima do limiar;
- `mowing_review`: evidência estimada ou medida indica ultrapassagem, mas uma
  pessoa ainda precisa revisar e qualquer ordem segue o fluxo de aprovação.

## Arquitetura proposta

```text
Sentinel-2 ─┐
Planet ─────┼─> observações por sensor ─> QA + alinhamento ─┐
Sentinel-1 ─┘                                               │
clima ──────────────────────────────────────────────────────┤
relevo ─────────────────────────────────────────────────────┤
histórico de serviço ───────────────────────────────────────┤
medições reais ─────────────────────────────────────────────┤
                                                            v
                                             feature snapshot versionado
                                                            │
                          ┌─────────────────────────────────┼──────────────────┐
                          v                                 v                  v
                 estado/altura                   risco temporal        anomalia
                          └─────────────────────────────────┼──────────────────┘
                                                            v
                                    política de abstention e confiança
                                                            │
                                                            v
                                    regra operacional + revisão humana
```

O processamento de raster, features e inferência deve ocorrer em batch/worker.
A API serve resultados persistidos e nunca calcula índices ou ML no frontend.

### Gate 1 - elegibilidade espacial

Uma inferência operacional exige:

- eixo rodoviário e geometria de zona aprovados e versionados;
- segmento de 100 m e zona identificados de forma imutável;
- SRID e transformações registrados;
- geometria válida e quantidade suficiente de área/pixels úteis;
- `eligible_for_operations=true` segundo política aprovada.

O eixo e os buffers atuais são estimados. Eles podem alimentar desenvolvimento,
mas devem produzir saídas preparadas ou inconclusivas.

### Gate 2 - qualidade e proveniência

Cada fonte precisa carregar ID, versão do produto, instante de aquisição, instante
de ingestão, checksum ou referência imutável, licença, geometria, algoritmo de
processamento e indicadores de qualidade. Falha de checksum, proveniência ou
licença bloqueia o uso.

Qualidade de dado e confiança de modelo são grandezas diferentes:

- `data_quality` descreve cobertura válida, nuvem/sombra, atualidade, alinhamento,
  disponibilidade e qualidade de campo;
- `model_uncertainty` descreve a dispersão calibrada da previsão;
- `confidence_band` resume ambos pela política versionada, sem ser apresentado
  como probabilidade exata da altura.

### Gate 3 - atualidade e compatibilidade temporal

Cada feature deve ser calculada "as of" o instante da previsão. Nunca usar dados
publicados ou medidos depois dele. Janelas e tolerâncias de associação entre campo,
satélite e clima serão parâmetros versionados, não valores oficiais embutidos.

Quando sensores observarem datas distintas:

- preservar o timestamp de cada fonte;
- criar features explícitas de idade;
- impedir interpolação longa sem validação;
- marcar divergência temporal como limitação;
- favorecer `inspect` quando a evidência recente for insuficiente.

## Papel de cada fonte

| Fonte | Papel recomendado | Features candidatas | Limite principal |
| --- | --- | --- | --- |
| Sentinel-2 L2A | série óptica temporal principal | reflectâncias, NDVI, NDRE, EVI, SAVI, NDMI, percentis, dispersão e deltas | nuvem/sombra, pixels mistos e bandas de resoluções distintas |
| PlanetScope | detalhe espacial complementar e datas adicionais | cobertura, textura, heterogeneidade, bordas, fração vegetada e mudanças dentro da zona | acesso/cota/licença, alinhamento e ausência de altura direta |
| Sentinel-1 | fallback/apoio estrutural futuro | VV, VH, razões, diferenças e tendência temporal | speckle, geometria SAR e necessidade de calibração local |
| Clima histórico | contexto causal anterior à observação | chuva, temperatura, umidade, radiação e evapotranspiração em janelas | resolução e qualidade variam por provedor |
| Previsão do tempo | evolução futura | chuva e temperatura previstas por horizonte | separar forecast disponível no instante da previsão do realizado posterior |
| Relevo | contexto estático | elevação, inclinação e orientação | não mede a vegetação |
| Manutenção | memória operacional | dias desde corte, alturas antes/depois, intervalos e recorrência | eventos incompletos ou decisões logísticas não são rótulos técnicos |
| Campo | ground truth | alturas repetidas, distribuição, foto, GPS e método | exige protocolo, qualidade, privacidade e revisão |

### Uso correto do Planet

O ganho provável do Planet está em reduzir mistura espacial. Dentro de uma zona
estreita ele pode ajudar a separar pavimento, acostamento, solo, vegetação e copa,
além de calcular textura e fração de cobertura com maior detalhe que o Sentinel-2.

O pipeline Planet deve avançar em incrementos separados:

1. validar catálogo, permissões, produtos e cota da conta sem download;
2. persistir metadados com suporte a `planet-scope` e identidade idempotente;
3. criar planejamento de pedido/consumo por AOI, sem execução implícita;
4. baixar somente recortes aprovados, registrar bytes, checksum, licença e
   linhagem;
5. aplicar máscara de qualidade, correção/alinhamento e agregação por zona;
6. avaliar o ganho por ablation antes de incorporar features ao modelo candidato;
7. oferecer tiles somente por proxy/cache backend autenticado, nunca expondo a
   chave no navegador.

Séries Planet e Sentinel permanecem separadas. O modelo recebe identificadores de
sensor e features normalizadas por produto; não se presume equivalência direta de
índice entre sensores. A fusão ocorre depois da QA e do alinhamento, e precisa
deixar faltantes explícitos.

### Resolução e agregação

O segmento de 100 m e suas zonas são a unidade de saída. Internamente:

- bandas Sentinel de 10 e 20 m devem preservar a resolução nativa declarada;
- uma grade analítica comum de 20 m é uma candidata segura para combinações com
  red-edge/SWIR, sujeita a experimento;
- Planet pode gerar estatísticas de maior detalhe antes da agregação por zona;
- reamostragem nunca deve ser descrita como ganho de informação;
- um pixel isolado nunca representa a zona inteira.

Por feature raster, guardar pelo menos contagem válida, média, mediana, desvio,
percentis, mínimo, máximo e fração de cobertura quando fizer sentido. Features de
heterogeneidade são importantes para detectar corte parcial, solo, sombra, copa e
mistura.

## Features do modelo

### Espectrais e espaciais

- reflectâncias das bandas disponíveis por produto e sua versão radiométrica;
- NDVI, variantes de NDRE, EVI, SAVI e NDMI;
- percentis e dispersão, não apenas média;
- fração de pixels válidos e fração vegetada;
- textura e heterogeneidade, primeiro avaliadas com Planet;
- deltas entre observações comparáveis;
- tendência robusta, média móvel e anomalia por sensor;
- flags de nuvem, sombra, borda, saturação e pixels insuficientes.

Não adicionar dezenas de índices por conveniência. Cada grupo entra por ablation,
com documentação de fórmula, bandas, resolução e ganho medido.

### Meteorológicas

- precipitação acumulada em 1, 3, 7, 14 e 30 dias;
- temperatura média/mínima/máxima em janelas;
- umidade, radiação e evapotranspiração quando disponíveis e confiáveis;
- previsão meteorológica por horizonte, com issue time preservado;
- indicadores de dado ausente e distância/representatividade da fonte.

As janelas são computadas em relação à data de referência da previsão. Clima
realizado depois da previsão nunca entra retroativamente na linha de treino.

### Temporais, históricas e estáticas

- seno/cosseno do dia do ano;
- dias desde corte, medição e observação válida por sensor;
- último intervalo e distribuição histórica entre cortes;
- alturas reais antes/depois e tendência real quando elegíveis;
- número de cortes em janelas anteriores;
- elevação, inclinação, orientação, zona e atributos rodoviários aprovados;
- qualidade e atualidade por fonte.

IDs de segmento, equipe ou rodovia não devem virar atalhos para memorização sem
uma justificativa de modelagem. A generalização espacial será testada em grupos
nunca vistos.

### Dados ausentes

Ausência nunca deve virar zero automaticamente. Usar `NULL`, flags de
disponibilidade, idade da última observação e imputação treinada apenas dentro de
cada fold. Se uma fonte essencial estiver ausente, o gate pode abster o modelo.

## Targets e construção do dataset

### Target de altura

O target é uma medição de campo real, revisada e elegível. Para aproximar a escala
do satélite, o protocolo deve coletar múltiplos pontos representativos por zona e
registrar mínimo, mediana, média, máximo e dispersão. A definição de "altura" deve
ser única e ilustrada.

Uma foto com régua ajuda auditoria, mas visão computacional ou aceite visual da
foto não transforma automaticamente uma medida digitada em ground truth.

### Target de ultrapassagem

É derivado exclusivamente da altura real e do limiar aplicável à zona na data:

```text
special: measured_height_cm > 10
left/right/median: measured_height_cm > 30
```

O evento "equipe cortou" não é substituto para `needs_cut`: pode refletir rota,
orçamento, segurança, contrato ou decisão humana.

### Target de tempo até limiar

Preferir análise de sobrevivência ou classificação por horizonte, porque muitos
segmentos não terão um evento observado dentro da janela. Datas de corte só podem
representar evento após confirmar a medição/condição que motivou a intervenção;
casos sem evento são censurados, não descartados.

### Elegibilidade de uma linha

Uma linha de treino precisa conter:

- geometria oficial e vínculo inequívoco com segmento/zona;
- medição `real`, protocolo/método e revisão de qualidade;
- timestamps e disponibilidade histórica reproduzíveis;
- fontes licenciadas para o uso pretendido;
- snapshot de features construído apenas com o que existia no instante;
- checksums, versões e lineage completos;
- ausência explícita de dados demo, preparados, simulados ou inferidos no target.

O manifesto de dataset registra fontes, contagens, período, cobertura espacial,
taxonomia, exclusões, licenças, splits, transformações, hashes e usos proibidos.

## Estratégia de modelos

### Nível 0 - baseline atual

Manter o baseline NDVI + altura real como referência de segurança e fallback.

### Nível 1 - baseline multimodal v2

Antes de ML, criar um score transparente de evidência e crescimento com:

- tendência espectral válida;
- dias desde última intervenção;
- chuva/temperatura recentes;
- sazonalidade;
- classe histórica apenas como contexto datado;
- atualidade e completude das fontes.

Pesos e faixas são propostas configuráveis, nunca valores oficiais da Motiva.
O score não retorna centímetros. Ele produz `low`, `moderate`, `high` ou
`unknown`, fatores explicativos e recomendação de inspeção quando necessário.

### Nível 2 - altura candidata

Comparar, no mínimo:

- mediana histórica condicionada a zona/tempo desde corte;
- regressão regularizada;
- modelo de árvores/gradient boosting;
- variante quantílica ou método calibrado para intervalos.

A biblioteca final, pesos e nova dependência exigem aprovação. Modelos complexos
só avançam se superarem baselines de forma relevante, estável e por subgrupo.

### Nível 3 - risco temporal candidato

Treinar um classificador calibrado por horizonte ou modelo de sobrevivência usando
features observáveis no instante. Evitar encadear apenas um ponto de altura como
entrada; propagar a incerteza da altura ou permitir que o risco use diretamente o
snapshot multimodal.

### Nível 4 - tipo de cobertura e anomalias

Classificação de `grass_herbaceous`, `shrub`, `tree`, `mixed`,
`non_vegetation` e `unknown` depende de taxonomia aprovada e anotações próprias.
Não derivar tipo de cobertura de N1/N2/N3.

Detecção de anomalia é um fluxo separado. Uma queda espectral pode significar
corte, obra, seca, fogo, nuvem residual ou erro. A saída é `possible_event` e pede
confirmação; nunca cria automaticamente um evento de manutenção.

## Treino, validação e incerteza

### Splits obrigatórios

- divisão temporal com treino no passado e teste em períodos posteriores;
- holdout espacial por grupos de segmentos e, quando houver escala, por rodovia;
- agrupamento de amostras vizinhas/repetidas para impedir que o mesmo local apareça
  nos dois lados do split;
- validação por estação, zona, sensor, qualidade e faixa de altura;
- preprocessamento e imputação ajustados somente no conjunto de treino.

Um `random train_test_split` isolado não é avaliação suficiente.

### Métricas

Altura:

- MAE e RMSE em centímetros;
- viés e erro por faixa N1/N2/N3, zona, rodovia, estação e qualidade;
- cobertura e largura do intervalo de previsão;
- erro próximo de 10 e 30 cm.

Ultrapassagem/risco:

- recall e precision, com destaque para falsos negativos;
- PR-AUC, F1 e matriz de confusão;
- Brier score e curva de calibração;
- métricas separadas para zona especial e demais zonas;
- taxa de abstention/inspeção e erro entre casos não abstidos.

Operação:

- taxa de correção humana;
- inspeções geradas, confirmadas e evitadas;
- idade dos dados e frequência do fallback;
- latência, custo por km e consumo de cota Planet;
- drift de features, erro e cobertura por período.

Não há meta numérica oficial suficiente para promoção. Ela deve ser aprovada pelo
data owner e registrada no model card. Em qualquer caso, uma melhora média não
compensa degradação relevante de recall acima do limiar crítico.

### Calibração e abstention

O modelo deve produzir intervalo e probabilidade calibrados fora da amostra. Uma
política candidata é:

- qualidade rejeitada, geometria não operacional ou origem inválida: não executar
  ML e retornar `inspect`/inconclusivo;
- fora da distribuição, fonte essencial ausente ou intervalo excessivamente
  largo: abster e retornar `inspect`;
- intervalo totalmente abaixo do limiar e risco futuro baixo: `monitor`;
- intervalo cruza o limiar: `inspect`;
- evidência calibrada acima do limiar: `mowing_review`, nunca ordem automática.

As faixas e os limites de largura são configuráveis e dependem de aprovação.

## Feature snapshot, registry e previsão

Cada execução deve ser reproduzível por estes artefatos imutáveis:

```text
dataset_manifest
  -> feature_definition_version
  -> feature_snapshot
  -> training_run
  -> model_version
  -> inference_run
  -> prediction
  -> recommendation
  -> human_review
```

Um `feature_snapshot` precisa registrar:

- `segment_zone_id` e instante `as_of`;
- valores, nulos, unidades e qualidade;
- IDs de todas as observações fonte;
- versões de transformações e geometria;
- hash determinístico do conjunto de entradas.

O model registry usa estados equivalentes a `candidate`, `validated`, `shadow`,
`approved`, `retired` e `suspended`. Promoção e rollback são decisões append-only;
pesos aprovados nunca são sobrescritos.

## Contrato candidato de inferência

Não implementar antes de ADR, migração e revisão do OpenAPI.

```json
{
  "segment_zone_id": "uuid",
  "as_of": "2026-09-13T12:00:00Z",
  "data_status": "estimated",
  "zone_type": "left",
  "applicable_threshold_cm": 30,
  "vegetation": {
    "height_median_cm": 28.0,
    "height_interval_cm": [20.0, 38.0],
    "historical_class_estimate": "N2",
    "trend": "increasing",
    "growth_score": 0.72
  },
  "risk": {
    "exceedance_probability_now": 0.36,
    "exceedance_probability_7d": 0.61,
    "exceedance_probability_15d": 0.79,
    "days_until_threshold_interval": [4, 16]
  },
  "quality": {
    "data_quality_band": "limited",
    "confidence_band": "low",
    "abstained": true,
    "reasons": ["Prediction interval crosses the applicable threshold."]
  },
  "recommendation": "inspect",
  "requires_human_approval": true,
  "eligible_for_official_reporting": false,
  "model_version": "vegetation-state-candidate-v1",
  "feature_snapshot_id": "uuid",
  "source_observation_ids": ["uuid"],
  "limitations": ["Estimated height is not a field measurement."]
}
```

Os números acima são apenas exemplo de schema. Não são previsão, calibração ou
parâmetros do ZENIT.

## APIs e dados externos necessários

### Necessários para o primeiro pipeline real

| Recurso | Situação | Ação necessária |
| --- | --- | --- |
| Planet Data/Orders/asset access | catálogo já tem fundação backend-only | confirmar produtos, permissões, licença e cota; manter `PL_API_KEY` somente no worker |
| Copernicus Sentinel Hub/Data Space | Sentinel-2 já foi validado em AOI preparada | manter OAuth backend-only; ampliar features e, depois, Sentinel-1 |
| Clima histórico e forecast | ainda não integrado ao modelo | aprovar Open-Meteo como protótipo ou outro provedor; registrar versão, timezone, issue time e qualidade |

### Complementares, sem urgência

| Recurso | Uso | Decisão |
| --- | --- | --- |
| NASA POWER | validação/contexto meteorológico regional | não tratar a grade regional como estação por segmento |
| INMET ou outra rede observada | validação meteorológica local | avaliar cobertura, licença, disponibilidade e custo operacional |
| Copernicus DEM GLO-30/GLO-90 | elevação, inclinação e orientação | ingestão estática versionada; não exige atualização diária |
| Sentinel-1 | reduzir lacunas ópticas e adicionar estrutura | P2 após baseline óptico/clima/histórico e protocolo SAR |

Não solicitar nem registrar chaves neste documento. Nenhuma credencial pode ir ao
dashboard, mobile, Git, logs ou URLs de tiles.

## Campanha mínima de dados de campo

Antes do treino de altura:

1. homologar eixo, faixa de domínio, zonas e ponto piloto;
2. definir altura operacional: método, referência ao solo, tratamento de folhas
   isoladas e agregação da zona;
3. estratificar amostras por zona, N1/N2/N3, estação, dias desde corte, entorno e
   condição espectral;
4. medir os mesmos segmentos ao longo do ciclo pós-corte, incluindo estados baixo,
   médio, alto e próximo do limiar;
5. coletar múltiplos pontos por zona, GPS com precisão, timestamp, foto de contexto
   e foto com escala quando permitido;
6. revisar qualidade e divergências sem apagar o valor original;
7. associar satélite e clima por regras temporais versionadas;
8. congelar dataset e splits antes de comparar modelos.

O volume mínimo não deve ser inventado antecipadamente. A suficiência é avaliada
por cobertura de estratos, estabilidade das métricas, largura dos intervalos e
curvas de aprendizado, não apenas por número total de linhas.

## Plano incremental de implementação

### Incremento A - fundação sem ML

- aprovar contrato de feature snapshot e terminologia;
- integrar clima histórico com cache, qualidade e proveniência;
- ampliar Sentinel-2 para bandas/índices e série temporal por zona;
- persistir metadados Planet após migração específica;
- implementar baseline multimodal v2 e explicações;
- manter toda saída como preparada/inconclusiva enquanto a geometria não for
  oficial.

### Incremento B - Planet controlado

- validar conta e licença;
- planejar/autorizar pedidos por AOI e controlar cota;
- baixar e verificar recortes mínimos;
- extrair features espaciais por zona;
- executar ablation Sentinel versus Sentinel + Planet.

### Incremento C - dataset real

- homologar protocolo e taxonomia;
- coletar medições longitudinais;
- implementar manifesto e checagens de elegibilidade;
- gerar baseline offline e relatório reproduzível.

### Incremento D - modelos candidatos

- comparar baselines, regressão e boosting;
- calibrar intervalos/probabilidades;
- executar holdouts espacial e temporal;
- publicar model card, relatório de ablation e análise de erros.

### Incremento E - modo sombra

- inferir sem influenciar autorização;
- comparar previsão, medição e decisão humana;
- monitorar drift, abstention e falsos negativos;
- promover somente após gate formal técnico e operacional.

## Critérios de aceitação da proposta

- toda saída mantém segmento de 100 m e zona separada;
- limiares 10/30 cm e classes N1/N2/N3 são preservados;
- nenhuma fonte espectral é apresentada como altura direta;
- Planet é complementar, controlado por backend e avaliado por ablation;
- dados simulados/preparados nunca entram no treino;
- splits impedem vazamento temporal, espacial e entre vizinhos;
- confiança, qualidade, atualidade e incerteza são campos distintos;
- baixa evidência resulta em abstention/inspeção;
- recomendações exigem revisão e não criam ordem automaticamente;
- datasets, features, modelos, previsões e revisões permanecem versionados e
  auditáveis.

## Decisões humanas pendentes

1. eixo, faixa de domínio e geometria oficial das quatro zonas;
2. protocolo e definição de altura por zona;
3. taxonomia de gramínea, arbusto, árvore, mistura e não vegetação;
4. fonte meteorológica primária e condições de uso em produção;
5. produtos/licenças/cotas Planet autorizados para treino, inferência e exibição;
6. política de associação temporal campo-satélite;
7. limiares de qualidade, confiança, abstention e validade temporal;
8. custo relativo de falsos negativos e falsos positivos;
9. métricas e gates oficiais de promoção;
10. privacidade, retenção e uso de foto/GPS para treinamento.

## Próximo passo recomendado

O próximo ticket deve ser a especificação versionada de `feature_snapshot` e do
dataset manifest, sem adicionar ainda uma biblioteca de ML. Em paralelo
organizacional, o projeto deve homologar o protocolo de campo e confirmar os
direitos de uso Planet. Isso permite implementar clima e séries temporais sem
criar um modelo treinado sobre dados inadequados.

## Referências internas

- [Manual mestre atualizado](../manual/README.md)
- [Companheiros das fontes PDF](../reference/README.md)
- [Estado atual e lacunas](../team/current-state-and-gaps.md)
- [Plano de inteligência vegetal](../team/vegetation-intelligence-plan.md)
- [Serviços externos e segredos](../team/external-services-and-secrets.md)
- [ADR-0005 - baseline satelital com gate de qualidade](../decisions/ADR-0005-quality-gated-satellite-baseline.md)
- [ADR-0006 - descoberta satelital neutra por provedor](../decisions/ADR-0006-provider-neutral-satellite-discovery.md)
- [ADR-0033 - camada NDVI cacheada e vinculada por checksum](../decisions/ADR-0033-checksum-bound-cached-ndvi-dashboard-layer.md)
- [ADR-0066 - mapa de vegetação histórico e não operacional](../decisions/ADR-0066-zero-cost-realistic-vegetation-map.md)
- [ADR-0067 - fundação Planet somente no backend](../decisions/ADR-0067-backend-only-planet-provider.md)
- [Validação estatística Sentinel](../data-quality/sentinel-statistical-validation.md)
