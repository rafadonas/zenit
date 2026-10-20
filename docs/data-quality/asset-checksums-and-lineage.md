# Checksums e linhagem dos ativos — PLANET-007

- Ticket: `PLANET-007`
- Decisão: [ADR-0082](../decisions/ADR-0082-satellite-asset-integrity-audit.md)
- Migração: `0045_satellite_asset_lineage_verification.sql`
- Comando: `zenit-asset-lineage`
- Status: implementado; **política de divergência pendente de aprovação**

## Escopo

| Dentro | Fora |
| --- | --- |
| cadeia cena → pedido → ativo → artefato derivado | novo download ou correção automática |
| auditoria que recalcula o SHA-256 a partir do armazenamento | aplicação de retenção e exclusão de ativos |
| registro append-only de cada verificação | processamento dos ativos (`PLANET-008`) |
| manifesto determinístico de exportação | elegibilidade operacional ou oficial |

## Onde a linhagem fica

A tabela `data_lineage` **continua sem uso para ativos de provedor**, e isso é
deliberado: a restrição dela exige um pai `source_file` ou `import_run`, que
descrevem documentos importados. Um ativo Planet não tem nenhum dos dois; ele
vem de uma cena de catálogo e de um pedido. A linhagem então fica onde a
entidade vive:

```text
satellite_scene (provider, external_scene_id, checksum do catálogo)
  └── satellite_asset (papel, storage_uri, checksum, versão do objeto, tamanho, source_order_id)
        ├── planet_order (AOI, área, bytes, licença, retenção)
        └── satellite_asset_verification (auditoria append-only)
artefatos derivados declarados em data/manifests/*.json
  └── ligados pelo checksum do raster de origem
```

## Critérios de aceite

| # | Critério | Status | Evidência |
| --- | --- | --- | --- |
| A1 | Linhagem registrada ou ausência justificada | atendido | seção acima e ADR-0082 |
| A2 | Ativo com checksum, papel, tipo, tamanho, origem e versão do objeto | atendido | migração `0045`; o fluxo de Order passa a gravar versão e tamanho |
| A3 | Auditoria recalcula o checksum a partir do armazenamento | atendido | `read_plaintext` decifra e `verify_asset` recalcula |
| A4 | Auditoria não altera nem apaga ativos | atendido | só `INSERT` na tabela de verificação; `--dry-run` não grava nada |
| A5 | Divergência marca o ativo como não utilizável, sem correção automática | atendido | `summarize` lista `unusable_asset_ids`; comando sai com erro |
| A6 | Estados distintos para ausente, ilegível e divergente | atendido | `missing`, `unreadable`, `mismatch` |
| A7 | Registro de auditoria imutável | atendido | gatilho append-only; smoke recusa `UPDATE` e `DELETE` |
| A8 | Exportação determinística | atendido | ordenação estável por cena e papel; testada com entrada invertida |
| A9 | Artefatos derivados aparecem como filhos da origem | atendido | manifesto liga prévia e camada ao checksum do raster |
| A10 | Nenhum resultado torna o ativo oficial | atendido | `eligible_for_official_reporting: false` no manifesto |
| A11 | Divergência só de tamanho é gravável como evidência | atendido | restrição aceita `mismatch` com checksum igual; verificado em banco real |
| A12 | Reverso possível, porém deliberado | atendido | exige `SET zenit.confirm_destructive` na mesma sessão |

## Dependências e aprovações

| Item | Situação |
| --- | --- |
| `PLANET-003` e `PLANET-004` | atendidas |
| Migrações `0001`–`0045` aplicadas no destino | responsabilidade de quem executa |
| Política de divergência: reter, rebaixar ou apagar | **pendente**, data owner |
| Revisão da migração `0045` | **pendente**, revisor diferente do autor |

## Reverter a migração

O gatilho append-only impede `UPDATE` e `DELETE`, então o reverso não pode
simplesmente apagar as linhas. Ele exige confirmação explícita na mesma sessão:

```bash
psql -c "SET zenit.confirm_destructive = 'satellite_asset_verification'" \
     -f infra/migrations/0045_satellite_asset_lineage_verification.down.sql
```

Sem essa confirmação, o reverso falha e a evidência permanece.

## Uso

```bash
# Auditoria completa: relê, decifra, recalcula e registra
zenit-asset-lineage --verify --database-url postgresql://zenit:<senha>@localhost:5432/zenit

# Diagnóstico sem gravar evidência
zenit-asset-lineage --verify --dry-run --database-url ...

# Manifesto de linhagem, sem tocar no armazenamento
zenit-asset-lineage --export --database-url ... > lineage.json
```

O comando sai com erro quando algum ativo não está utilizável, para que um
pipeline não siga usando bytes divergentes.

## Verificação executada em 2026-09-15

| Verificação | Resultado |
| --- | --- |
| Migrações `0001`–`0045` em Postgres/PostGIS descartável | aplicadas |
| `tests/sql/verify_satellite_asset_verification.sql` | PASS: `verified` com checksum divergente, `missing` com checksum observado, `UPDATE` e `DELETE` recusados |
| Reverso da `0045` sem confirmação | bloqueado |
| Reverso da `0045` com `SET zenit.confirm_destructive` e reaplicação | aplicado |
| Ida e volta real no MinIO: gravar, decifrar e recalcular | `verified` |
| Mesma leitura com checksum registrado errado | `mismatch` |
| Objeto inexistente | `missing` |
| Testes unitários e suíte completa | 572 passando |
