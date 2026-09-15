# Validação de permissão de download Planet — PLANET-002

O worker pode repetir uma busca `PSScene` com `PermissionFilter` de
`assets:download`. Esse filtro é opt-in e mantém a consulta limitada à AOI e à
janela temporal informadas; ele não cria Order nem baixa bytes.

Na validação de 2026-09-15, com a AOI `[-46.80, -23.55, -46.76, -23.50]` e a
janela UTC `2026-08-01`–`2026-08-07`, o filtro retornou 13 aquisições e nenhuma
próxima página. Os flags foram `order_requested=false`,
`download_requested=false` e `operationally_eligible=false`.

O resultado deve registrar apenas contagem, paginação e os flags
`order_requested=false`, `download_requested=false` e
`operationally_eligible=false`. Não registrar chave, corpo bruto, URL de asset,
token ou identificador de pedido.

Mesmo com resultados, a permissão filtrada não confirma produto/bundle, licença
acadêmica, cota disponível, custo, retenção, processamento ou autorização de
operação. Esses gates pertencem ao próximo ticket de planejamento/aquisição.
