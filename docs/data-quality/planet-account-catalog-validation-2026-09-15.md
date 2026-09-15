# Validação de conta e catálogo Planet — 2026-09-15

Ticket `PLANET-001` executou uma busca limitada no catálogo Planet Data API
`PSScene` pelo worker backend-only. A chave foi lida do `.env` como segredo e
não aparece em logs, argumentos públicos, URLs ou artefatos versionados.

## Escopo executado

| Parâmetro | Valor |
| --- | --- |
| AOI | `[-46.80, -23.55, -46.76, -23.50]` |
| Janela UTC | `2026-08-01` a `2026-08-07` |
| Coleção | `PSScene` |
| Aquisições retornadas | `13` |
| Próxima página | `false` |
| Download solicitado | `false` |
| Elegível para operação | `false` |

## Interpretação

O retorno confirma que a credencial e a busca de metadados funcionaram para o
recorte escolhido no momento da validação. Os metadados continuam sujeitos à
qualidade do provedor e não medem altura, crescimento ou urgência.

Este ensaio não verificou Orders, assets licenciados, permissões de download,
cota por área, custo, retenção, uso em treinamento, tiles ou processamento.
Nenhuma cena foi persistida ou baixada. Um ticket futuro deve receber uma AOI e
produto aprovados, registrar licença/cota e executar um download pequeno,
reversível e com checksum somente após revisão humana.
