# Processamento offline do trecho piloto — PLANET-008

- Ticket: `PLANET-008`
- Decisão: [ADR-0083](../decisions/ADR-0083-offline-pilot-processing.md)
- Comando: `zenit-planet-process`
- Migração: **nenhuma**; reutiliza `analysis_run` e `vegetation_analysis`
- Status: implementado; **AOI homologada e licença de processamento pendentes**

## Escopo

| Dentro | Fora |
| --- | --- |
| NDVI por zona a partir de ativos já cacheados e verificados | qualquer chamada ao provedor ou novo download |
| máscara UDM2 de nuvem, sombra e pixel inválido | conversão em altura, N1/N2/N3 ou urgência |
| execução idempotente por cena, zona, checksums e geometria | decisão operacional ou relatório oficial |
| proporção de pixels válidos por zona | fusão com Sentinel, clima ou histórico |

## Critérios de aceite

| # | Critério | Status | Evidência |
| --- | --- | --- | --- |
| A1 | Nenhuma chamada de rede durante o processamento | atendido | o comando só lê armazenamento e banco; resumo traz `provider_calls: 0` |
| A2 | Só processa ativo com auditoria mais recente `verified` | atendido | teste de ativo `mismatch` e de ativo nunca auditado; verificado em banco real |
| A3 | Máscara UDM2 antes de qualquer estatística | atendido | teste com metade da zona encoberta; `valid_pixel_percent` cai para 50 |
| A4 | Proporção de pixels válidos por zona | atendido | execução real registrou 75% com uma linha de nuvem |
| A5 | Resultado sempre `inconclusive`, com revisão humana e sem uso oficial | atendido | linha gravada: `inconclusive`, `inspect`, `low`, `requires_human_approval=true` |
| A6 | Nenhuma conversão em altura ou classe histórica | atendido | `observed_height_cm` e `height_data_status` ficam nulos; explicação declara o limite |
| A7 | Reexecução com a mesma entrada não cria nada novo | atendido | segunda execução real: `analysis_runs_created: 0` |
| A8 | Zona marcada como operacional é recusada | atendido | teste dedicado |
| A9 | Testes com raster sintético, sem provedor | atendido | 11 testes de processamento e 8 do comando |
| A10 | Dependências aprovadas declaradas | atendido | `numpy` e `rasterio` no `pyproject.toml`, autorizados em 2026-09-15 |

## Dependências e aprovações

| Item | Situação |
| --- | --- |
| `PLANET-004` pedido e cache | atendida |
| `PLANET-005` cota | atendida; o processamento não consome cota |
| `PLANET-007` auditoria de integridade | atendida e **exigida em tempo de execução** |
| AOI homologada do trecho piloto (`GOV-003`) | **pendente** |
| Licença de processamento acadêmico dos ativos | **pendente** |
| Revisão do processador por outra pessoa | **pendente** |

## Como executar

```bash
zenit-asset-lineage --verify --database-url postgresql://zenit:<senha>@localhost:5432/zenit
zenit-planet-process \
  --scene-id <cena> \
  --road-code SP021 \
  --from-segment 195 \
  --segments 10 \
  --database-url postgresql://zenit:<senha>@localhost:5432/zenit
```

`--segments 10` cobre o quilômetro do piloto, com dez trechos de 100 m.
`--dry-run` calcula e relata sem gravar. Zonas que não tocam o raster aparecem em
`skipped_zones`, com o motivo, em vez de sumir do relatório.

## Verificação executada em 2026-09-15

Ponta a ponta, com banco descartável nas migrações `0001`–`0045` e ativos
sintéticos cifrados no MinIO local:

| Verificação | Resultado |
| --- | --- |
| Execução com um raster de 4 × 4 pixels e uma linha encoberta | `accepted`, NDVI médio 0,5, `valid_pixel_percent` 75 |
| Linha gravada em `vegetation_analysis` | `inconclusive`, `inspect`, `low`, revisão obrigatória, sem uso oficial |
| Segunda execução idêntica | `analysis_runs_created: 0` |
| Ativo marcado como `mismatch` na auditoria | processamento recusado com a mensagem apontando o `zenit-asset-lineage` |
| Testes unitários: NDVI, máscara, divisão por zero, grades diferentes, geometria fora do raster | 19 testes |
| Suíte completa e `ruff` | 591 passando; lint limpo |

Os ativos usados nessa verificação eram sintéticos e foram removidos do MinIO ao
final. Nenhum dado real de provedor foi processado.
