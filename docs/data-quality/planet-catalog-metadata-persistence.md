# Persistência de metadados Planet — PLANET-003

- Ticket: `PLANET-003`
- Decisão: [ADR-0077](../decisions/ADR-0077-planet-catalog-metadata-persistence.md)
- Implementação: `0d36d57` (PR #26), migração `0041`
- Status do gate: **formalizado após a implementação**; aprovações pendentes

## Escopo

| Dentro | Fora |
| --- | --- |
| metadados normalizados de cenas PlanetScope em AOI e janela limitadas | bytes de asset, Order e download |
| gravação idempotente no catálogo existente `satellite_scene` | cota de área, bytes ou custo (`PLANET-005`) |
| migração reversível do domínio de sensor | proxy ou cache de tiles (`PLANET-006`) |
| confirmação explícita antes de escrever | linhagem e auditoria de integridade (`PLANET-007`) |
| — | processamento, índice, altura ou uso operacional (`PLANET-008`) |

## Critérios de aceite

| # | Critério | Status | Evidência |
| --- | --- | --- | --- |
| A1 | Migração aplica e reverte; o reverso falha enquanto houver cenas Planet | atendido | `0041_planet_scene_persistence.sql` e `.down.sql` |
| A2 | Gravar exige a confirmação `--persist` | atendido | `test_persistence_refuses_writes_without_confirmation` |
| A3 | A chave é exigida antes de qualquer chamada de rede | atendido | `test_persistence_checks_key_before_network_after_confirmation` |
| A4 | Idempotência por `(provider, external_scene_id)`, preservando o checksum do primeiro snapshot | atendido | `test_repeating_the_same_search_creates_no_duplicate` e `tests/sql/verify_planet_scene_persistence.sql` |
| A5 | Nenhum byte, Order ou elegibilidade operacional; `cache_status=discovered` | atendido | ADR-0077 e saída do comando |
| A6 | Saída sem chave, URL de asset, corpo bruto ou ID de Order | atendido | `planet_persistence_cli.run` devolve apenas contagens e flags |
| A7 | Banco de destino explícito, sem reescrita implícita de host | atendido | `--database-url` e `resolve_database_url`; host de Compose exige destino explícito |
| A8 | Testes automatizados de persistência e do reverso da migração | atendido | 8 testes do comando; smoke SQL no CI; passo de CI aplica o reverso real com e sem cenas Planet |
| A9 | Snapshot parcial declarado quando houver paginação | atendido | seção "Snapshot parcial" abaixo; `has_next_page` sempre na saída |

## Dependências

| Dependência | Situação |
| --- | --- |
| `PLANET-001` conta e catálogo ([ADR-0075](../decisions/ADR-0075-planet-account-catalog-validation.md)) | atendida |
| `PLANET-002` filtro de permissão ([ADR-0076](../decisions/ADR-0076-planet-download-permission-filter.md)) | atendida |
| Migrações `0001`–`0043` aplicadas no banco de destino | responsabilidade de quem executa |
| Retenção e licença dos metadados de catálogo | **pendente**; o [ADR-0078](../decisions/ADR-0078-planet-order-download-gate.md) define 30 dias apenas para assets |

## Aprovações

| Aprovação | Responsável exigido | Status |
| --- | --- | --- |
| Revisão da migração `0041` por pessoa diferente do autor | trilha geoespacial | pendente |
| Retenção e licença dos metadados persistidos | data owner | pendente |
| Aceite do cartão | Rafael | pendente |

O PR #26 foi integrado pelo próprio autor. Esta seção registra a revisão que
faltou; enquanto ela estiver pendente, o cartão não pode ser tratado como
concluído.

## Riscos conhecidos

- **Aplicação da migração:** os arquivos montados no Compose só rodam em volume
  novo; bancos existentes seguem o procedimento manual do README.
- **Destino do banco:** resolvido. O comando não reescreve mais o host. Dentro do
  Compose, onde `postgres` resolve, ele é usado normalmente. Fora do Compose, onde
  o nome não resolve, o comando falha e pede `--database-url`, em vez de gravar
  num banco vizinho que responda em `localhost`.

## Snapshot parcial

A busca é limitada por `--limit`, padrão 25, e **não segue paginação**. O
conjunto persistido é um recorte da janela, não o catálogo completo. A saída
sempre informa `has_next_page`; quando ela for `true`, existem cenas elegíveis
fora do snapshot. Ampliar a cobertura exige nova execução com janela ou limite
diferentes, e o consumo correspondente entra no controle de cota (`PLANET-005`).

## Comportamento implementado

`zenit-planet-persist` usa a busca limitada com `assets:download` e o catálogo
idempotente existente. A confirmação `--persist` é obrigatória para escrever no
banco local.

Cada registro guarda o identificador externo, sensor `planet-scope`, coleção,
horário, footprint, nuvem normalizada, snapshot de propriedades e checksum do
catálogo. O estado é `cache_status=discovered`: nenhum asset ou byte é baixado.

A mesma cena `(provider, external_scene_id)` não é duplicada. O resultado do
comando informa somente contagens e flags de segurança; não expõe chave, URL de
asset, corpo bruto ou ID de Order. A migração reversa só remove o suporte ao
sensor quando não existirem linhas Planet.

Execução validada em 2026-09-15 na AOI/janela documentadas: primeira execução
`catalog_acquisitions=13`, `scenes_created=13`, `scenes_existing=0`; repetição
imediata `scenes_created=0`, `scenes_existing=13`. A consulta no banco confirmou
13 linhas `planet-scope` como `discovered`, com `cached_at` nulo e checksum de
catálogo presente.
