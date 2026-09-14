# Protocolo de ground truth de vegetação

- Ticket: `GEO-002`
- Versão do protocolo: `gt-protocol-0.1`
- Data: 2026-09-14
- Status: `proposed` — desenho para revisão; **não autoriza coleta real**
- Predecessor: `GEO-001` (taxonomia), ainda não aprovado
- Consumidores: `GEO-003`, `GEO-004`, `MOB-005`, `AI-001` a `AI-003`

## 1. Objetivo e limites

Este protocolo define como coletar e anotar observações de campo que possam servir
como ground truth de altura e de cobertura vegetal por rodovia, trecho de 100 m,
zona e estação. Ele define amostragem, instrumentos, metadados, dupla anotação,
adjudicação, medição de concordância, aprovações de licença/privacidade/retenção
e regras de exclusão.

Limites que não podem ser flexibilizados:

- ground truth de altura é **somente** medição de campo real, revisada e elegível;
- NDVI, Planet, SAR, score ou leitura visual de foto não são altura observada;
- uma foto com régua apoia auditoria, mas não transforma uma medida digitada em
  ground truth por si só;
- nenhuma observação, rótulo ou métrica deste protocolo autoriza roçada;
- dados `prepared`, `estimated`, `simulated` ou `inconclusive` não são ground
  truth, e dados demo/simulados não entram no piloto nem em treinamento;
- a classificação histórica de 2025-03-28 não representa condição atual;
- nenhum alvo numérico deste documento é oficial. Valores marcados como
  **suposição acadêmica** servem para desenhar o piloto e exigem aprovação.

Autoridade: quando houver conflito, prevalecem lei, contrato e política formal,
depois ADRs aceitos e contratos versionados, conforme
[`docs/manual/README.md`](../manual/README.md).

## 2. Gates antes de qualquer coleta real

A coleta real só começa quando **todos** os itens abaixo estiverem concluídos e
registrados com responsável, data e versão:

| Gate | Evidência exigida | Dono |
| --- | --- | --- |
| AOI do piloto | geometria/eixo/zonas homologados (`GOV-003`) | data owner |
| Taxonomia | `GEO-001` aprovado e versão fixada | especialista + data owner |
| Definição de altura | seção 5.2 revisada e ilustrada | especialista |
| Licença, consentimento, privacidade e retenção | tabela da seção 8 aprovada | privacy owner + data owner |
| Segurança de campo | procedimento da concessão para acesso à faixa | responsável de segurança de campo |
| Controles de mídia | pendências `MEDIA-02` do [threat model](../security/incremental-threat-model.md) resolvidas para o piloto | segurança |
| Protocolo | esta versão passa de `proposed` para `approved` | Rafael (escopo acadêmico) + donos acima |

Enquanto algum gate estiver aberto, a coleta permanece `blocked`. Um ensaio de
treinamento de equipe é permitido somente com dados rotulados `simulated`, que
ficam fora do dataset (seção 9).

## 3. Unidade de observação e identidade

| Nível | Identificador | Regra |
| --- | --- | --- |
| Campanha | `campaign_id` | uma janela de coleta dentro de uma única estação |
| Célula | `road_code` + `segment_index` + `zone` + `campaign_id` | zona nunca é misturada com outra |
| Ponto planejado | `planned_point_id` | sorteado antes da campanha; estável entre campanhas |
| Observação | `observation_id` (UUID) | imutável; correções criam nova versão, nunca sobrescrevem |
| Foto | `photo_id` + SHA-256 | vinculada a uma observação |
| Anotação | `annotation_id` | uma por anotador por observação; imutável |
| Rótulo adjudicado | `adjudication_id` | referencia as anotações de origem |

Zonas seguem as regras de domínio: `left`, `right`, `median` e `special`.

## 4. Amostragem

### 4.1 Estratificação

Cada célula é classificada nos estratos abaixo antes do sorteio:

| Estrato | Valores | Observação |
| --- | --- | --- |
| rodovia | `road_code` homologado | holdout pode reservar rodovias inteiras |
| zona | `left`, `right`, `median`, `special` | limiar de 10 cm em `special`/operacional e 30 cm nas demais |
| classe histórica | N1, N2, N3, sem classe | **apenas estratificação**; nunca é rótulo nem alvo |
| estação | chuvosa (out–mar), seca (abr–set) | ajustar ao regime climático aprovado para a AOI |
| entorno | urbano, rural, talude, canteiro, área especial | lista fechada revisável |
| iluminação | registrada na captura | usada na análise, não no sorteio |

### 4.2 Seleção de pontos

- sortear pontos com gerador pseudoaleatório e **semente registrada** no
  manifesto da campanha;
- sortear dentro do polígono da zona, respeitando recuo mínimo de segurança da
  borda de pista definido pelo procedimento de campo;
- mínimo de **3 pontos por célula**, alinhado ao fluxo de três medições já
  existente no aplicativo; o especialista pode aumentar esse número se a dispersão
  observada no piloto for alta;
- os mesmos `planned_point_id` são revisitados em cada campanha para permitir
  série temporal;
- incluir células difíceis (sombra, copa, talude, mistura), não apenas casos
  limpos.

### 4.3 Substituição e perdas

- ponto inacessível, inseguro ou fora da zona real: registrar motivo em lista
  fechada (`unsafe`, `no_access`, `outside_zone`, `flooded`, `other`) e usar o
  **próximo substituto sorteado** para a mesma célula;
- é proibido substituir ponto por conveniência ou escolher visualmente o local;
- célula sem ponto válido permanece registrada como perda, com motivo.

### 4.4 Holdout e prevenção de vazamento

- dividir por **blocos contíguos de trechos** e por **campanha inteira**;
- observações do mesmo ponto planejado ou de trechos vizinhos nunca ficam em
  splits diferentes;
- o split é definido antes da anotação e registrado no manifesto.

### 4.5 Tamanho do piloto

**Suposição acadêmica:** 1 km do trecho piloto aprovado × 4 zonas × 3 pontos ×
2 estações:

```text
10 trechos × 4 zonas × 3 pontos × 2 campanhas = 240 observações planejadas
```

O número é suficiente para exercitar o processo e estimar concordância com
intervalo de confiança largo; não é suficiente para validar um modelo. O relatório
do piloto deve publicar os intervalos em vez de conclusões pontuais.

## 5. Instrumentos e método de medição

### 5.1 Instrumentos

| Instrumento | Especificação mínima | Controle |
| --- | --- | --- |
| régua de medição | ≥ 150 cm, resolução 1 cm, faixas de alto contraste a cada 10 cm, base plana | conferência contra trena de referência no início de cada campanha; registrar `instrument_id` e data |
| quadrado de amostragem | 0,5 × 0,5 m, cor contrastante | usado para cobertura e enquadramento da foto |
| dispositivo móvel | registrado no ZENIT, relógio sincronizado, GNSS com precisão reportada | `device_id`, `app_version` e fonte de horário registrados |
| cartão de referência | identificador do ponto e escala impressa | aparece na foto de contexto, sem cobrir a vegetação |

Dispositivo sem precisão GNSS reportada não pode registrar observação elegível.

### 5.2 Definição única de altura (candidata)

Precisa de revisão e ilustração por especialista antes da aprovação:

> `height_cm` é a distância vertical, sem compressão da vegetação, entre o solo e
> o topo do dossel predominante num raio de 10 cm ao redor da régua, ignorando
> hastes isoladas e inflorescências que ultrapassem o dossel.

- régua na vertical, apoiada no solo, sem pressionar a vegetação;
- leitura no centímetro inteiro mais próximo;
- vegetação acamada é medida como está e recebe flag `lodged`;
- se o solo não for visível ou acessível, registrar `height_cm` ausente e motivo;
- o **alvo de ultrapassagem** é derivado depois, exclusivamente da altura real e do
  limiar aplicável à zona na data; o coletor não classifica N1/N2/N3 em campo.

Por célula, o dataset calcula mínimo, mediana, média, máximo e dispersão das
alturas válidas. Uma média nunca esconde divergência entre pontos.

### 5.3 Fotos por ponto

| Foto | Enquadramento | Obrigatória |
| --- | --- | --- |
| contexto | zona inteira visível, cartão do ponto, sentido da via registrado | sim |
| medição | régua vertical e escala legível, topo do dossel e base visíveis | sim |
| cobertura | vista de cima do quadrado de 0,5 × 0,5 m | sim quando a célula for anotada para cobertura |

Antes de aceitar a captura, o coletor verifica blur, exposição, oclusão da régua e
integridade do arquivo. Foto rejeitada é refeita, e a rejeição fica registrada.

## 6. Metadados obrigatórios

Campos já existentes nos contratos atuais estão marcados com ✓; os demais são
requisitos para `GEO-003` e `MOB-005` e não alteram schema neste ticket.

| Grupo | Campo | Regra |
| --- | --- | --- |
| identidade | `observation_id`, `campaign_id`, `planned_point_id` | UUID/IDs imutáveis |
| versão | `protocol_version`, `taxonomy_version`, `app_version` | obrigatórios em toda observação |
| local planejado | `road_code`, `segment_index`, `zone`, coordenadas planejadas | SRID 4326 explícito |
| local observado | `latitude` ✓, `longitude` ✓, `horizontal_accuracy_m`, `heading_deg` | precisão > 5 m gera flag `low_gnss_accuracy` (suposição acadêmica) |
| tempo | `captured_at` ✓, `time_source`, `received_at` | fuso `America/Sao_Paulo` para exibição; armazenamento com offset |
| dispositivo | `device_id` ✓ | dispositivo registrado |
| coletor | `collector_pseudonym` | nunca nome ou e-mail no dataset |
| instrumento | `instrument_id`, `instrument_checked_at` | conferência da campanha |
| medição | `height_cm` ✓, `height_method`, `height_missing_reason`, flags (`lodged`, `soil_not_visible`) | `height_method` referencia a definição 5.2 |
| status | `height_data_status` ✓, `data_status` | só `real` é elegível (seção 9) |
| fotos | `photo_id`, `photo_role`, `sha256`, dimensões, `exif_stripped_copy_sha256` | original cifrado; cópia sem EXIF para anotação |
| qualidade | `blur`, `exposure`, `occlusion`, `scale_visible` | lista fechada `ok`/`limited`/`rejected` |
| ambiente | `weather`, `lighting`, `recent_mowing_evidence` | lista fechada |
| governança | `consent_record_id`, `license_record_id`, `retention_class` | ausentes = observação inelegível |
| perdas | `discard_reason` | obrigatório quando não houver medição |

## 7. Anotação, adjudicação e concordância

### 7.1 O que é anotado

| Alvo | Valores | Observação |
| --- | --- | --- |
| classe de cobertura | taxonomia `GEO-001` (candidata: `unknown`, `grass_herbaceous`, `shrub`, `tree`, `mixed`, `non_vegetation`) | até aprovação, versão `taxonomy-candidate-0` |
| cobertura | faixa percentual por classe no quadrado | faixas fixadas no guia de anotação |
| oclusão e qualidade | `ok`, `limited`, `rejected` | com motivo |
| motivo de `unknown` | lista fechada (sombra, blur, oclusão, conflito, fora de escala) | obrigatório quando a classe for `unknown` |
| leitura de altura na foto | cm ou `not_readable` | **controle de qualidade** da medição de campo, não substitui `height_cm` |
| relação espacial | dentro da zona, copa sobre a zona, fora da zona | conforme regras de oclusão do `GEO-001` |

`unknown` é um rótulo de anotação válido e deve aparecer no dataset. Ele não se
confunde com `data_status = inconclusive`, que torna a observação inelegível.

### 7.2 Dupla anotação

- dois anotadores independentes por observação;
- anotadores não veem a anotação do outro, a classe histórica, recomendações nem
  saída de modelo;
- anotação feita sobre a cópia sem EXIF e com rostos/placas tratados;
- **rodada de calibração** antes do piloto, com conjunto de referência e guia
  ilustrado de exemplos aceitos e rejeitados;
- no piloto, **100% das observações** recebem dupla anotação;
- após o piloto, sobreposição mínima de **20%** sorteada por estrato
  (suposição acadêmica), mantendo a medição contínua de concordância;
- anotações são imutáveis; correção gera nova anotação vinculada.

### 7.3 Adjudicação

Uma observação vai para adjudicação quando ocorrer qualquer condição:

- classes de cobertura diferentes;
- faixas de cobertura não adjacentes;
- leituras de altura na foto com diferença maior que 5 cm (suposição acadêmica);
- leituras em lados opostos de 10 cm ou 30 cm;
- leitura na foto diverge de `height_cm` de campo em mais de 5 cm ou cruza um
  limiar;
- qualquer anotador marca `rejected`.

Regras:

- o adjudicador é especialista e não pode ter anotado a mesma observação;
- vê as duas anotações, as fotos e os metadados, e registra justificativa;
- produz o rótulo final com `adjudication_id`, preservando as anotações originais;
- conflito de altura entre foto e campo **não corrige** `height_cm` por leitura
  visual: o adjudicador mantém, marca `height_disputed` ou exclui a medição do
  alvo com motivo;
- caso sem resolução vira classe `unknown` com motivo `conflict`.

### 7.4 Medição de concordância

Métricas publicadas com cada versão do dataset e no relatório do piloto:

| Alvo | Métrica | Complemento |
| --- | --- | --- |
| classe de cobertura | Cohen's κ entre os dois anotadores; Krippendorff's α quando houver dados faltantes ou mais anotadores | matriz de confusão incluindo `unknown` |
| N1/N2/N3 derivado das leituras | κ ponderado quadrático | contagem de discordâncias por limiar |
| cruzamento de limiar | proporção de acordo em `> 10 cm` e `> 30 cm` | por zona |
| altura foto × foto e foto × campo | ICC(2,1) e Bland–Altman (viés médio e limites de concordância de 95%) | distribuição por faixa de altura |
| qualidade | κ sobre `ok`/`limited`/`rejected` | taxa de rejeição por estrato |

Regras de reporte:

- calcular geral e por classe, zona, estação, rodovia e condição de iluminação;
- intervalos de confiança de 95% por bootstrap estratificado por célula;
- publicar taxa de adjudicação e taxa de `unknown`;
- **gate provisório** para encerrar a calibração: κ ≥ 0,6 na classe de cobertura
  (suposição acadêmica, não alvo oficial). Abaixo disso, revisar o guia e repetir
  a calibração com nova amostra.

## 8. Licença, consentimento, privacidade e retenção

As decisões abaixo são **propostas**. Nenhuma está aprovada. Este documento não
concede autorização legal, contratual ou de privacidade; a aprovação cabe aos
donos indicados.

| Item | Decisão proposta | Dono exigido | Status |
| --- | --- | --- | --- |
| titularidade das fotos e medições | cessão de uso ao projeto/concessão definida em termo antes da campanha | data owner + jurídico | `pending` |
| licença do dataset | uso interno acadêmico/piloto; redistribuição proibida sem nova aprovação | data owner | `pending` |
| imagens de provedores | uso conforme contrato de cada fonte; não embutidas no dataset de campo sem licença | data owner | `pending` |
| consentimento dos coletores | termo explícito sobre identidade, GPS e horário, com finalidade e retenção | privacy owner | `pending` |
| pseudonimização | `collector_pseudonym` e `annotator_pseudonym`; tabela de ligação cifrada e restrita | privacy owner | `pending` |
| terceiros capturados | rostos e placas desfocados na cópia de anotação; original cifrado e restrito | privacy owner | `pending` |
| EXIF | removido da cópia de anotação; original preservado com checksum | privacy owner + segurança | `pending` |
| precisão de localização | coordenadas completas restritas; dataset de treino pode usar `segment_index` + `zone` | privacy owner | `pending` |
| retenção de originais | prazo **a definir**; cifrados em bucket privado com acesso auditado | privacy owner + data owner | `pending` |
| retenção de cópias anonimizadas e rótulos | prazo **a definir**; vinculado à versão do dataset | data owner | `pending` |
| legal hold | suspende exclusão por solicitação formal registrada | jurídico | `pending` |
| exclusão | procedimento de remoção de bytes com registro no manifesto (tombstone com checksum, sem conteúdo) | privacy owner | `pending` |
| segurança de campo | nenhum coletor entra na faixa de rolamento; procedimento da concessão prevalece | responsável de segurança de campo | `pending` |

Registro de aprovação (preencher ao aprovar; uma linha por item ou bloco):

| Item | Versão aprovada | Responsável | Data | Referência do documento assinado |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

Sem `consent_record_id` e `license_record_id` válidos, a observação não é elegível.

## 9. Exclusão de dados demo e simulados

### 9.1 Regra de elegibilidade

Uma observação só entra no **piloto de anotação** ou em qualquer **treinamento ou
avaliação** quando todas as condições forem verdadeiras:

```text
data_status == "real"
AND campaign_id pertence a campanha aprovada
AND protocol_version está approved
AND consent_record_id e license_record_id válidos
AND device_id registrado
AND height_data_status == "real" (somente para alvo de altura)
```

A regra é aplicada por **inclusão explícita**. Qualquer campo ausente ou valor
desconhecido exclui a observação.

### 9.2 Exclusões obrigatórias

| Origem | Motivo |
| --- | --- |
| `data_status` `prepared`, `estimated`, `simulated` ou `inconclusive` | não é ground truth |
| três pontos estimados da ordem de inspeção preparada | geometria estimada na linha central |
| fluxo de roçada simulada e fotos pós-serviço simuladas | ensaio demonstrativo |
| planilhas de 2025-03-28 | referência histórica, não condição atual nem rótulo |
| recorte NDVI e cenas `discovered`/`partially_cached` | evidência espectral, não altura |
| eixo candidato e segmentos `needs_validation` | geometria não homologada |
| fixtures, seeds, usuários e rodovias de teste ou ambiente local | dados de desenvolvimento |
| ensaios de treinamento de equipe | rotulados `simulated` |
| imagens do guia de anotação | material didático, nunca amostra |

### 9.3 Evidência de exclusão

Cada manifesto de campanha e de dataset registra:

- contagem de observações candidatas, incluídas e excluídas por motivo;
- lista dos `data_status` encontrados;
- confirmação explícita: “nenhum dado demo, preparado, estimado, simulado ou
  inconclusivo foi usado como ground truth, no piloto ou em treinamento”;
- responsável pela verificação e data.

## 10. Piloto de anotação

### 10.1 Sequência

1. aprovar os gates da seção 2;
2. sortear pontos e registrar sementes, estratos e splits;
3. conferir instrumentos e treinar equipe com material `simulated`;
4. executar a campanha da primeira estação;
5. rodar a calibração de anotação até o gate provisório;
6. anotar 100% das observações em dupla e adjudicar conflitos;
7. publicar o relatório de concordância;
8. repetir na segunda estação com os mesmos pontos;
9. revisar o protocolo e versionar as mudanças antes de ampliar a amostra.

### 10.2 Relatório do piloto

- versão do protocolo, taxonomia, guia e ferramentas;
- AOI, campanhas, sementes e splits;
- observações planejadas, realizadas, perdidas e excluídas por motivo;
- métricas da seção 7.4 com intervalos de confiança;
- taxa de adjudicação, `unknown` e rejeição por estrato;
- divergências foto × campo e casos `height_disputed`;
- incidentes de segurança, privacidade ou qualidade;
- confirmação de exclusão da seção 9.3;
- limitações e mudanças propostas ao protocolo.

## 11. Decisões em aberto

- homologação da AOI, eixo e zonas (`GOV-003`);
- taxonomia de cobertura e regras de oclusão (`GEO-001`);
- definição e ilustração finais de altura;
- faixas de cobertura e ferramenta de anotação;
- número de pontos por célula após a dispersão observada no piloto;
- limite de precisão GNSS, tolerância de 5 cm e gate de κ;
- prazos de retenção, legal hold e responsáveis de privacidade, dados e segurança;
- procedimento de segurança de campo da concessão.

## 12. Fora de escopo

- schema, migração, API e autorização dos campos novos (`GEO-003`);
- manifesto e dataset versionado (`GEO-004`);
- captura guiada no aplicativo (`MOB-005`);
- cálculo automatizado de concordância, que depende de dados reais;
- qualquer modelo, treinamento ou uso operacional.
