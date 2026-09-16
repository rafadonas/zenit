# Validação de evidência — vegetação versus pavimento

- Ticket: cartão de validação relacionado a GEO-001, GEO-003 e AI-001
- Responsável: Rafael (data owner acadêmico)
- Revisão: `bc01b95`
- Resultado: **BLOQUEADO — não há evidência de classificação validada**
- Complemento: origem, proveniência, método e limites — revisão `81935b7`

## Conclusão

As entregas existentes distinguem corretamente o vocabulário proposto de
cobertura vegetal das classes históricas de altura, mas não comprovam que as
imagens ou polígonos atuais diferenciem vegetação de pavimento.

- O manifesto [`vegetation-dataset-2026-09-15.json`](../../data/manifests/vegetation-dataset-2026-09-15.json)
  tem `status=blocked`, zero rótulos nas seis classes e
  `label_source_status=missing`.
- `classificacao_rocada.kmz` contém categorias de equipamento e mapeamentos
  inferidos; não são rótulos `tree`, `grass_herbaceous`, `shrub`, `mixed` ou
  `non_vegetation`.
- As planilhas preservam N1/N2/N3 como classes históricas de altura, não como
  cobertura vegetal.
- A visualização do corredor é histórica e inferida, e o recorte NDVI é
  preparado e parcialmente cacheado. Os assets Planet do pedido piloto estão
  cacheados, mas não existe camada Planet no dashboard nem rótulo derivado deles.
  Nenhuma dessas evidências constitui ground truth ou validação visual
  independente.
- O contrato de cobertura é uma leitura versionada e fail-closed. Fixtures de
  teste demonstram invariantes de API, não observações de campo validadas.

Portanto, nenhum resultado atual deve ser chamado de classificação de
vegetação/pavimento, usado para treinamento, relatório oficial ou autorização
de roçada. A ausência de um especialista é uma limitação registrada, não uma
aprovação científica implícita.

## Origem da alegação

O quadro não está no repositório, portanto a entrega que encerrou o cartão
antigo não pode ser confirmada. As entregas abaixo são as candidatas; nenhuma
implementa classificação de vegetação versus pavimento.

| Entrega candidata | Commit / decisão | O que entrega | Relação com a alegação |
| --- | --- | --- | --- |
| Validação estatística Sentinel | `45cc496` · [`sentinel-statistical-validation.md`](sentinel-statistical-validation.md) | NDVI médio de uma AOI preparada | fonte literal da frase sobre possível mistura de pavimento, solo e vegetação; declara que nenhuma interpretação causal foi feita |
| Prévia NDVI e camada do dashboard | `82e4bc8`, `128e03a` · [ADR-0033](../decisions/ADR-0033-checksum-bound-cached-ndvi-dashboard-layer.md) | recorte NDVI georreferenciado com paleta descritiva | a paleta não cria classes de cobertura, altura ou roçada |
| Mapa realista do corredor | `af4111d` · [ADR-0066](../decisions/ADR-0066-zero-cost-realistic-vegetation-map.md) | polígonos históricos associados a N1/N2/N3 | associação inferida por proximidade; não descreve superfície atual |
| Pedido Planet piloto | `636f6c8`, `fdba4a8` · [ADR-0078](../decisions/ADR-0078-planet-order-download-gate.md) | três assets cifrados de uma cena | não cria rótulo de vegetação nem camada visual |

Se o cartão antigo tiver identificador, ele deve ser registrado nesta seção.

## Proveniência e tipo de distinção

| Fonte | Origem dos dados | Status | Tipo de distinção |
| --- | --- | --- | --- |
| NDVI Sentinel-2 L2A | resposta real do provedor sobre AOI estimada | `real` na cena, `prepared` na zona, `inconclusive` | espectral, sem regra de classificação |
| `classificacao_rocada.kmz` | arquivo fornecido, atributos deslocados | `prepared`, `needs_validation` | categorias de equipamento com mapeamento inferido |
| Planilhas N1/N2/N3 | arquivos fornecidos, referência 2025-03-28 | `historical` | classes históricas de altura |
| Associação polígono → classe no mapa | derivada por consulta espacial | `historical`, `inferred_needs_validation` | inferida |
| Assets Planet do pedido piloto | resposta real do provedor | `real`, uso acadêmico | nenhuma; não processados em rótulos |

**Não existe distinção manual.** Nenhuma pessoa rotulou vegetação ou pavimento
nas fontes revisadas, e o manifesto registra zero anotadores.

## Método, qualidade, erros e limites

### NDVI Sentinel

| Item | Valor |
| --- | --- |
| Produto e resolução | Sentinel-2 L2A, pixel de 10 m |
| Data | 2026-07-29, uma única aquisição |
| AOI | segmento de desenvolvimento 195, buffer de 20 m à esquerda, não homologado |
| Recorte | 5 × 11 pixels: 35 válidos e 20 NoData |
| NDVI | médio 0,0800 no GeoTIFF e 0,0974 na Statistical API; mínimo −0,1574; máximo 0,2840 |
| Qualidade | 100% de pixels válidos na Statistical API; conclusão `inconclusive` |

- Não há limiar, classificador, rótulo, ground truth ou matriz de confusão.
- Um pixel de 10 m sobre faixa estreita mistura pavimento, solo e vegetação; a
  mistura é hipótese, não medição.
- `accepted` descreve apenas a validade do pixel, não a classe da superfície.
- Generalização: **nenhuma** — uma AOI, uma data, geometria estimada.

### Mapa histórico

- Cada polígono é associado ao segmento estimado mais próximo e à estação de
  500 m mais próxima na planilha mais recente, usando a classe N1/N2/N3 mais
  conservadora.
- A propriedade `vegetation_class` do mapa guarda N1, N2, N3, X ou `unknown`,
  isto é, classe histórica de altura, não tipo de cobertura.
- Erros possíveis: atributos deslocados do KMZ, eixo estimado, associação por
  proximidade e data de referência antiga.

### Planet

- Uma cena (`20260805_135356_12_253c`) com três assets cifrados, sem
  processamento para índice, máscara ou rótulo.
- O [ADR-0078](../decisions/ADR-0078-planet-order-download-gate.md) registra que
  o download não cria rótulo de vegetação.

## Evidência reproduzível

| Verificação | Resultado |
| --- | --- |
| `python scripts/verify_dataset_manifest.py data/manifests/vegetation-dataset-2026-09-15.json` | **PASS** — manifesto permanece `blocked`, `training_eligible=false` |
| `.venv/bin/pytest -q services/api/tests/test_vegetation_cover.py` | **PASS** — 16 testes |
| `npm --workspace @zenit/dashboard run test -- src/lib/vegetation-map.test.ts` | **PASS** — 3 testes |
| Revisão de origem `zenit-source-review-2026-09-15` | **PASS para protótipo acadêmico; não homologada para operação ou treino** |

Verificações do complemento na revisão `81935b7`:

| Verificação | Resultado |
| --- | --- |
| `python scripts/verify_dataset_manifest.py data/manifests/vegetation-dataset-2026-09-15.json` | **PASS** — `status=blocked`, `training_eligible=false` |
| `.venv/bin/pytest -q services/api/tests/test_vegetation_cover.py` | **PASS** — 16 testes |
| `npm --workspace @zenit/dashboard run test -- src/lib/vegetation-map.test.ts` em contêiner Node | **PASS** — 3 testes |
| SHA-256 da prévia e da camada NDVI contra `data/manifests/sentinel-ndvi-preview.json` | **PASS** — os dois artefatos derivados conferem |
| `.venv/bin/pytest -q tests/test_ndvi_preview.py` | **SKIPPED** — o GeoTIFF de origem fica em `data/processed/`, fora do Git e ausente nesta máquina |

Os resultados PASS comprovam invariantes do contrato, do manifesto e da camada
histórica. **Não comprovam validade de classificação**, porque não existem
rótulos contra os quais medir.

Nenhum arquivo em `data/raw/` foi alterado e nenhum dado pessoal ou segredo foi
incluído nesta revisão.

## Recomendações fora do escopo

- Criar ticket WEB para renomear ou rotular `vegetation_class` e o texto "áreas
  históricas de vegetação" no mapa como classe histórica de roçada, evitando
  leitura como tipo de cobertura.
- Ao reabrir AI-001, medir explicitamente `non_vegetation` contra as classes de
  vegetação, com recall por classe e confusão entre gramínea e pavimento.

## Parecer

| Revisor | Papel | Decisão | Data | Referência |
| --- | --- | --- | --- | --- |
| Rafael | data owner acadêmico; autor das entregas de origem | bloqueado | 2026-09-15 | `ebee37f` |
| Lucas | trilha geoespacial; segunda revisão | pendente | — | — |

## Dependências para desbloqueio

O cartão deve permanecer em **Aguardando dependências** até que exista:

1. fonte de imagem/ground truth com licença e consentimento documentados;
2. rótulos observáveis de cobertura por segmento e zona, incluindo `unknown`
   quando a evidência não sustentar uma classe;
3. duas anotações independentes, adjudicação e guia de anotação versionado; e
4. splits espacial/temporal e checagem de vazamento registrados no manifesto.

Somente depois dessas etapas será possível reavaliar GEO-004 e, posteriormente,
AI-001. A camada atual continua útil como visualização histórica/preparada, mas
não como prova de diferenciação entre vegetação e pavimento.
