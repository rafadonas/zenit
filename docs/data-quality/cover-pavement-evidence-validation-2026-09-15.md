# Validação de evidência — vegetação versus pavimento

- Ticket: cartão de validação relacionado a GEO-001, GEO-003 e AI-001
- Responsável: Rafael (data owner acadêmico)
- Revisão: `bc01b95`
- Resultado: **BLOQUEADO — não há evidência de classificação validada**

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
- A visualização do corredor e a camada Planet são evidências preparadas ou
  parcialmente cacheadas; não constituem ground truth nem validação visual
  independente.
- O contrato de cobertura é uma leitura versionada e fail-closed. Fixtures de
  teste demonstram invariantes de API, não observações de campo validadas.

Portanto, nenhum resultado atual deve ser chamado de classificação de
vegetação/pavimento, usado para treinamento, relatório oficial ou autorização
de roçada. A ausência de um especialista é uma limitação registrada, não uma
aprovação científica implícita.

## Evidência reproduzível

| Verificação | Resultado |
| --- | --- |
| `python scripts/verify_dataset_manifest.py data/manifests/vegetation-dataset-2026-09-15.json` | **PASS** — manifesto permanece `blocked`, `training_eligible=false` |
| `.venv/bin/pytest -q services/api/tests/test_vegetation_cover.py` | **PASS** — 16 testes |
| `npm --workspace @zenit/dashboard run test -- src/lib/vegetation-map.test.ts` | **PASS** — 3 testes |
| Revisão de origem `zenit-source-review-2026-09-15` | **PASS para protótipo acadêmico; não homologada para operação ou treino** |

Nenhum arquivo em `data/raw/` foi alterado e nenhum dado pessoal ou segredo foi
incluído nesta revisão.

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
