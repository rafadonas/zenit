# Taxonomia de cobertura vegetal

- Ticket: `GEO-001`
- Versão: `cover-taxonomy-0.1`
- Data: 2026-09-15
- Status: `proposed` — aguarda parecer de especialista e data owner; **não é schema oficial**
- Consumidores: `GEO-002` (protocolo de ground truth), `GEO-003` (contrato de cobertura),
  `GEO-004` (dataset), `AI-*`

## 1. Objetivo e limites

Esta taxonomia define como rotular **o que cobre** uma unidade da faixa rodoviária:
gramínea/herbácea, arbusto, árvore, mistura, ausência de vegetação ou evidência
insuficiente. Ela inclui regras de dominância, estratos, oclusão, copa sobre a
faixa e conflitos.

Limites que não podem ser flexibilizados:

- cobertura, altura e decisão operacional são **eixos independentes** (seção 6);
- nenhuma classe implica N1/N2/N3, necessidade de roçada ou de poda;
- N1/N2/N3 não são usados para derivar tipo de cobertura
  ([modelo v2, nível 4](../architecture/vegetation-intelligence-model-v2.md));
- o anexo de conservação da ARTESP já registra que gramínea, árvore, arbusto,
  urgência e N1/N2/N3 não são o mesmo eixo de classificação
  ([`artesp-conservation-annex.md`](../reference/artesp-conservation-annex.md));
- a taxonomia não autoriza coleta, anotação oficial, treinamento ou roçada;
- valores marcados como **suposição acadêmica** servem para revisão e exigem
  aprovação antes de virar regra.

## 2. Unidade rotulada e princípio geral

Um rótulo descreve **o que ocupa a unidade vista em projeção vertical** (de cima),
classificado pela **estrutura observada** da vegetação — não pela espécie, nome
popular ou porte futuro.

| Unidade | Uso | Observação |
| --- | --- | --- |
| quadrado de campo 0,5 × 0,5 m | anotação de ground truth (`GEO-002`) | unidade de menor escala com foto e medição |
| zona do trecho de 100 m (`left`, `right`, `median`, `special`) | agregação por célula | nunca mistura zonas |
| recorte de imagem (futuro) | avaliação de modelo | depende de fonte, resolução e data registradas |

A classe de uma zona é derivada das **frações de cobertura** das unidades
menores, pelas regras da seção 4. Voto de maioria entre unidades não é usado,
porque esconde mistura.

## 3. Classes

### 3.1 Resumo

| Classe | Definição operacional | Tipo |
| --- | --- | --- |
| `grass_herbaceous` | vegetação enraizada sem caule lenhoso | vegetação |
| `shrub` | vegetação lenhosa ramificada desde a base, sem tronco principal distinto | vegetação |
| `tree` | vegetação lenhosa com tronco principal distinto e copa elevada separada do solo | vegetação |
| `mixed` | duas ou mais classes de vegetação relevantes, nenhuma dominante | vegetação |
| `non_vegetation` | vegetação enraizada abaixo do mínimo de cobertura | não vegetação |
| `unknown` | evidência insuficiente ou conflitante para classificar | **não é tipo de vegetação** |

### 3.2 `grass_herbaceous`

**Definição:** plantas enraizadas sem caule lenhoso — gramíneas, capins,
forrações e ervas.

| Inclui | Exclui |
| --- | --- |
| gramado, capim baixo ou alto | touceira de bambu (colmo lenhoso) → `shrub` |
| forração e ervas espontâneas | resíduo de corte solto, sem planta enraizada → `non_vegetation` |
| vegetação herbácea seca, ainda enraizada | trepadeira lenhosa → `shrub` |
| trepadeira herbácea sobre solo, cerca ou talude | muda lenhosa → `shrub` |

A altura do capim **não muda a classe**: capim alto continua `grass_herbaceous`.

### 3.3 `shrub`

**Definição:** vegetação lenhosa com vários ramos partindo da base ou próximo do
solo, sem um tronco principal distinto e sem copa separada do solo.

| Inclui | Exclui |
| --- | --- |
| arbustos e cerca viva | indivíduo com tronco e copa elevada → `tree` |
| muda lenhosa sem copa formada, mesmo de espécie arbórea | capim alto → `grass_herbaceous` |
| touceira de bambu | copa que avança sobre a faixa → `tree` (seção 5.3) |
| trepadeira lenhosa não apoiada em árvore | trepadeira sobre copa de árvore → parte da copa `tree` |

### 3.4 `tree`

**Definição:** vegetação lenhosa com tronco principal distinto e copa elevada,
separada do solo, inclusive quando só a copa está visível na unidade.

| Inclui | Exclui |
| --- | --- |
| árvores vivas ou mortas em pé | toco ou tronco caído sem copa → `non_vegetation` com nota |
| palmeiras | muda sem copa formada → `shrub` |
| copa projetada sobre a zona com tronco fora dela (seção 5.3) | arbusto podado em forma de copa, sem tronco distinto → `shrub` |

A distinção entre `tree` e `shrub` usa **somente estrutura** (tronco e copa).
Não existe limiar em centímetros ou metros nesta taxonomia.

### 3.5 `mixed`

**Definição:** a unidade contém duas ou mais classes de vegetação e nenhuma atinge
a dominância da seção 4.

| Inclui | Exclui |
| --- | --- |
| gramínea e arbusto em proporções próximas | uma classe dominante → rotular a dominante e registrar secundárias |
| árvore esparsa sobre gramínea sem dominância | mistura que não pode ser estimada → `unknown` |

`mixed` é uma mistura **conhecida e estimada**. Incerteza sobre o que existe na
unidade é `unknown`.

### 3.6 `non_vegetation`

**Definição:** a vegetação enraizada ocupa menos que o mínimo de cobertura da
seção 4.

| Inclui | Exclui |
| --- | --- |
| pavimento, acostamento, cascalho, solo exposto e rocha | solo com rebrota acima do mínimo → classe da vegetação |
| água, drenagem, defensas, placas e outras estruturas | sombra sobre vegetação → `unknown` ou qualidade limitada |
| resíduo de corte, palha solta, lixo, toco sem copa | vegetação seca enraizada → classe da vegetação |

### 3.7 `unknown`

**Definição:** a evidência não permite classificar com segurança. Não é um tipo
de vegetação e **exige motivo** de lista fechada:

| Motivo | Quando usar |
| --- | --- |
| `shadow` | sombra impede identificar a estrutura |
| `blur` | foto ou imagem sem nitidez suficiente |
| `occlusion` | mais de 50% da unidade oculta (seção 5.2) |
| `cloud` | nuvem ou névoa em fonte remota |
| `resolution` | resolução da fonte insuficiente para a unidade |
| `out_of_frame` | a unidade não está inteiramente enquadrada |
| `source_conflict` | fontes divergem e a adjudicação não resolveu (seção 5.4) |
| `annotator_conflict` | anotadores divergem e a adjudicação não resolveu |
| `understory_not_observable` | sub-bosque não pode ser observado (seção 5.1) |
| `other` | outro motivo, com nota obrigatória |

## 4. Cobertura e dominância

### 4.1 Estimativa de cobertura

- Cobertura é a fração da unidade ocupada em **projeção vertical** por cada
  classe, somando no máximo 100% por estrato.
- Registrar por faixa, não por valor contínuo:

| Faixa | Intervalo |
| --- | --- |
| `0` | nenhuma cobertura |
| `1-10` | maior que 0 e menor que 10% |
| `10-25` | de 10% a menos de 25% |
| `25-50` | de 25% a menos de 50% |
| `50-75` | de 50% a menos de 75% |
| `75-100` | 75% ou mais |

A faixa `1-10` existe para que o limiar de `non_vegetation` seja anotável.

Faixas sempre se referem à **fração da unidade**. A dominância da seção 4.2 usa a
**participação de cada classe na cobertura vegetal** da unidade.

### 4.2 Regra de classe principal

Suposições acadêmicas, aplicadas nesta ordem:

1. vegetação enraizada total **abaixo de 10%** da unidade visível →
   `non_vegetation`;
2. a classe de vegetação com maior participação que tenha **pelo menos 60% da
   cobertura vegetal** → essa classe;
3. nenhuma classe atinge 60% → `mixed`;
4. classes com **pelo menos 10%** da cobertura vegetal que não sejam a principal
   → registradas como `secondary_classes`, com faixa.

Exemplos:

| Unidade observada | Participação na vegetação | Rótulo |
| --- | --- | --- |
| 5% capim, 95% pavimento | capim 100% | `non_vegetation`; secundária `grass_herbaceous` `1-10` |
| 56% capim, 24% arbusto, 20% solo | capim 70%, arbusto 30% | `grass_herbaceous`; secundária `shrub` `10-25` |
| 36% capim, 32% arbusto, 12% árvore, 20% solo | capim 45%, arbusto 40%, árvore 15% | `mixed`; secundárias `grass_herbaceous` `25-50`, `shrub` `25-50`, `tree` `10-25` |

## 5. Estratos, oclusão, copa e conflitos

### 5.1 Estratos

Um rótulo tem dois campos independentes:

| Campo | Significado | Regra |
| --- | --- | --- |
| `cover_class` | estrato superior visível de cima | aplica a seção 4 ao que é visto em projeção vertical |
| `understory_class` | vegetação sob copa ou arbusto | só quando observada em campo; caso contrário `unknown` com `understory_not_observable` |

Sub-bosque **nunca** é deduzido de imagem vista de cima.

### 5.2 Oclusão

Oclusão é tudo que impede ver a unidade: veículo, pessoa, placa, equipamento,
sombra forte ou a própria régua.

| Fração oculta da unidade (suposição acadêmica) | Tratamento |
| --- | --- |
| menos de 20% | classificar normalmente; `occlusion_level: ok` |
| de 20% a 50% | classificar a parte visível; `occlusion_level: limited` com motivo |
| mais de 50% | `unknown` com `occlusion` |

Copa ou arbusto sobre o solo **não** é oclusão para `cover_class`, porque é o
próprio estrato superior. Afeta apenas `understory_class`.

### 5.3 Copa sobre a faixa

Árvore com tronco fora da zona e copa projetada sobre ela:

- a área da copa dentro do polígono da zona conta como `tree` em `cover_class`;
- registrar `canopy_overhang: true`;
- registrar `trunk_location`: `inside_zone`, `outside_zone` ou `not_visible`;
- o sub-bosque sob a copa segue a seção 5.1.

A classe **não decide** a intervenção. Poda e roçada são atividades distintas, e
nenhuma delas é inferida de `tree` ou `canopy_overhang`.

### 5.4 Conflitos

| Situação | Tratamento |
| --- | --- |
| dois anotadores divergem | adjudicação conforme `GEO-002` (`docs/data-quality/ground-truth-protocol.md`, seção 7.3); sem resolução → `unknown` com `annotator_conflict` |
| fontes da mesma data divergem (campo, foto, drone, satélite) | não fazer média nem descartar fonte; registrar `source_conflict` e adjudicar; sem resolução → `unknown` com `source_conflict` |
| fontes de datas diferentes | observações distintas, não conflito; cada uma mantém sua data e validade |
| objeto na divisa entre zonas | cada zona conta a parte projetada dentro do seu polígono |
| classe diverge de altura, N1/N2/N3 ou recomendação | **não é conflito**; eixos independentes (seção 6) |

Força da evidência para **tipo de cobertura**, usada pelo adjudicador e não como
substituição automática:

```text
observação de campo com foto > foto ou drone de alta resolução > satélite
```

## 6. Cobertura, altura e autorização operacional

| Eixo | Pergunta | Fonte válida | Proibido |
| --- | --- | --- | --- |
| cobertura (`cover_class`) | o que ocupa a zona? | anotação humana revisada; modelo apenas como estimativa rotulada | derivar N1/N2/N3, urgência ou necessidade de intervenção |
| altura (`height_cm` → N1/N2/N3) | quão alta está a vegetação? | somente medição de campo real e elegível (`GEO-002`) | inferir por classe de cobertura, NDVI ou score |
| decisão operacional | monitorar, inspecionar ou revisar roçada? | política versionada e revisão humana | ser disparada automaticamente por classe, altura estimada ou modelo |

Consequências:

- `grass_herbaceous` não significa “precisa roçar”;
- `tree` ou `canopy_overhang` não significa “precisa podar”;
- `non_vegetation` não significa “não precisa inspecionar”;
- uma cor ou ícone de classe na interface não carrega significado operacional;
- `cover_type_method` distingue `human_reviewed` de `model_estimated`.

## 7. Campos de um rótulo

Requisitos para `GEO-003`; **não alteram schema** neste ticket. Os nomes seguem o
contrato candidato do [plano vegetal](../team/vegetation-intelligence-plan.md).

| Campo | Regra |
| --- | --- |
| `taxonomy_version` | obrigatório; `cover-taxonomy-0.1` enquanto `proposed` |
| `unit_type` | `field_quadrat`, `zone_cell` ou `image_patch` |
| `cover_class` | uma das seis classes |
| `secondary_classes` | lista de classe + faixa da seção 4.1 |
| `understory_class` | classe ou `unknown` com `understory_not_observable` |
| `occlusion_level` | `ok`, `limited` |
| `occlusion_reason` | obrigatório quando `limited` |
| `canopy_overhang` | booleano |
| `trunk_location` | `inside_zone`, `outside_zone`, `not_visible`; obrigatório quando `canopy_overhang` |
| `unknown_reason` | obrigatório quando `cover_class` ou `understory_class` for `unknown` |
| `evidence_sources` | lista de observação/fonte com data |
| `cover_type_method` | `human_reviewed` ou `model_estimated` |
| `data_status` | `real`, `estimated`, `prepared`, `simulated` ou `inconclusive` |
| `review_status` | `pending`, `accepted`, `corrected` ou `rejected` |

## 8. Catálogo de exemplos

O guia de anotação ilustrado exige imagens reais aprovadas quanto a licença e
privacidade. Nenhuma imagem é inventada ou incluída nesta versão. Cada caso
abaixo precisa de pelo menos um exemplo aceito e um rejeitado:

| ID | Caso | Classe esperada | Imagem aceita | Imagem rejeitada |
| --- | --- | --- | --- | --- |
| EX-01 | capim alto em talude | `grass_herbaceous` | pendente | pendente |
| EX-02 | herbácea seca enraizada | `grass_herbaceous` | pendente | pendente |
| EX-03 | resíduo de corte sobre solo | `non_vegetation` | pendente | pendente |
| EX-04 | cerca viva | `shrub` | pendente | pendente |
| EX-05 | muda lenhosa sem copa | `shrub` | pendente | pendente |
| EX-06 | touceira de bambu | `shrub` | pendente | pendente |
| EX-07 | palmeira | `tree` | pendente | pendente |
| EX-08 | copa sobre a faixa com tronco fora | `tree` + `canopy_overhang` | pendente | pendente |
| EX-09 | árvore esparsa sobre gramínea | `mixed` ou classe dominante | pendente | pendente |
| EX-10 | solo com rebrota abaixo de 10% | `non_vegetation` | pendente | pendente |
| EX-11 | sombra forte sobre a zona | `unknown` (`shadow`) | pendente | pendente |
| EX-12 | veículo cobrindo mais de 50% | `unknown` (`occlusion`) | pendente | pendente |
| EX-13 | trepadeira sobre defensa | `grass_herbaceous` ou `shrub` | pendente | pendente |

## 9. Pacote de revisão

### 9.1 Perguntas para especialista e data owner

| # | Decisão | Pergunta |
| --- | --- | --- |
| Q1 | classes | As seis classes bastam para a faixa rodoviária? Falta alguma, como trepadeira ou vegetação aquática? |
| Q2 | estrutura | Separar `tree` e `shrub` apenas por tronco e copa, sem altura, é aceitável? |
| Q3 | bambu | Touceira de bambu deve ficar em `shrub`? |
| Q4 | mudas | Muda lenhosa sem copa formada deve ser `shrub`, mesmo de espécie arbórea? |
| Q5 | resíduo | Resíduo de corte e palha solta devem ser `non_vegetation`? |
| Q6 | mínimo | Vegetação enraizada abaixo de 10% deve ser `non_vegetation`? |
| Q7 | dominância | 60% da cobertura vegetal é um limiar adequado para classe principal? |
| Q8 | secundárias | 10% é um mínimo adequado para registrar classe secundária? |
| Q9 | faixas | As faixas `0`, `1-10`, `10-25`, `25-50`, `50-75`, `75-100` são anotáveis em campo? |
| Q10 | oclusão | Os cortes de 20% e 50% de oclusão são adequados? |
| Q11 | copa | Copa com tronco fora da zona deve contar como `tree` na zona? |
| Q12 | sub-bosque | `understory_class` separado é necessário para a operação? |
| Q13 | evidência | A ordem de força da evidência (campo > alta resolução > satélite) é adequada? |
| Q14 | geometria | As zonas homologadas no `GOV-003` são compatíveis com projeção vertical e divisão proporcional? |

### 9.2 Registro de parecer

| Pergunta | Decisão | Responsável | Papel | Data | Referência |
| --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | — |

### 9.3 Bloqueios

Enquanto Q1 a Q14 não tiverem parecer registrado:

- esta versão permanece `proposed`;
- `GEO-003` não cria schema, migração ou API de cobertura;
- `GEO-004` não publica rótulos como dataset;
- anotações feitas com esta versão são exercícios e mantêm
  `taxonomy_version: cover-taxonomy-0.1`.

## 10. Fora de escopo

- schema, migração, OpenAPI, autorização e interface (`GEO-003`);
- dataset versionado e anotação real (`GEO-004`);
- modelo de classificação ou segmentação (`AI-*`);
- imagens reais para o catálogo de exemplos;
- regras de intervenção, poda ou roçada.
