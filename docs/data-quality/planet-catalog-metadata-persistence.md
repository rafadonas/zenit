# Persistência de metadados Planet — PLANET-003

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
