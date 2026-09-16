# Controle de cota Planet — PLANET-005

- Ticket: `PLANET-005`
- Decisão: [ADR-0081](../decisions/ADR-0081-planet-quota-control.md)
- Migração: `0044_planet_quota_budget.sql`
- Comandos: `zenit-planet-quota`, verificação embutida em `zenit-planet-order`
- Status: implementado; **valores do orçamento pendentes de aprovação**

## Escopo

| Dentro | Fora |
| --- | --- |
| orçamento aprovado por período, com área, bytes e número de pedidos | custo financeiro e contrato comercial |
| consumo derivado dos pedidos já registrados | cota e consumo de tiles (`PLANET-006`) |
| recusa antes de qualquer chamada externa | processamento dos ativos (`PLANET-008`) |
| extrato legível de saldo | autorização operacional ou relatório oficial |

## Critérios de aceite

| # | Critério | Status | Evidência |
| --- | --- | --- | --- |
| A1 | Orçamento versionado, com responsável e referência de aprovação | atendido | `planet_quota_budget`, colunas `approval_reference`, `approved_by`, `approved_at` |
| A2 | Um único orçamento vigente por instante | atendido | restrição de exclusão GiST; smoke recusa período sobreposto |
| A3 | Orçamento aprovado é imutável | atendido | gatilho append-only; smoke recusa `UPDATE` e `DELETE` |
| A11 | Reverso possível, porém deliberado | atendido | exige `SET zenit.confirm_destructive = 'planet_quota_budget'` na mesma sessão |
| A4 | Consumo derivado de `planet_order`, sem contador paralelo | atendido | `PostgresPlanetQuota.status` soma área e bytes dos pedidos do período |
| A5 | Pedido cancelado não consome orçamento | atendido | `CONSUMING_ORDER_STATES`; verificado em banco real |
| A6 | Falha fechada sem orçamento aprovado | atendido | `QuotaError` quando nenhum período cobre o instante |
| A7 | Recusa antes da chamada externa, informando o saldo | atendido | `ensure_capacity` roda antes da busca de catálogo e do Order |
| A8 | Extrato sem escrever no banco | atendido | `zenit-planet-quota` executa apenas consultas |
| A9 | Destino de banco explícito nos comandos Planet | atendido | `--database-url` e `resolve_database_url` compartilhado |
| A10 | Chave Planet disponível para os comandos no Compose | atendido | `PL_API_KEY` repassado ao serviço `api` |

## Dependências

| Dependência | Situação |
| --- | --- |
| `PLANET-003` persistência de catálogo | atendida |
| `PLANET-004` gate de Order e download ([ADR-0078](../decisions/ADR-0078-planet-order-download-gate.md)) | atendida |
| Migrações `0001`–`0044` aplicadas no destino | responsabilidade de quem executa |
| Valores de área, bytes, pedidos e período do orçamento | **pendente de aprovação** |

## Aprovações

| Aprovação | Responsável exigido | Status |
| --- | --- | --- |
| Valores e período do orçamento, com base no contrato da conta | data owner | pendente |
| Revisão da migração `0044` | revisor diferente do autor | pendente |
| Aceite do cartão | Rafael | pendente |

Enquanto o orçamento não for aprovado e registrado, **nenhum Order pode ser
criado**: o comando falha fechado por ausência de orçamento.

## Como registrar um orçamento aprovado

O registro é um ato de aprovação e não tem comando dedicado, para não permitir
que alguém crie o próprio orçamento sem deixar rastro de quem aprovou:

```sql
INSERT INTO planet_quota_budget (
    period_start, period_end, max_area_m2, max_bytes, max_orders,
    approval_reference, approved_by, approved_at, notes
) VALUES (
    '2026-09-01+00', '2026-10-01+00', 30000.00, 314572800, 3,
    '<referência da aprovação>', '<quem aprovou>', now(), '<limitações>'
);
```

## Extrato

```bash
zenit-planet-quota --database-url postgresql://zenit:<senha>@localhost:5432/zenit
```

A saída traz o período, os limites, o consumo, o saldo restante e os estados de
pedido contados. Nenhum número dela é oficial nem autoriza operação.

## Verificação executada em 2026-09-15

| Verificação | Resultado |
| --- | --- |
| Migrações `0001`–`0044` em Postgres/PostGIS descartável | aplicadas |
| `tests/sql/verify_planet_quota_budget.sql` | PASS: sobreposição, `UPDATE`, `DELETE` e período invertido recusados |
| Consumo em banco real com pedidos `success`, `failed` e `cancelled` | PASS: 2 pedidos contados, 10 000 m², cancelado ignorado |
| Recusa por área acima do saldo | PASS, com saldo na mensagem |
| Instante sem orçamento | PASS: falha fechada |
| `zenit-planet-quota` contra o banco real | PASS |
| Testes unitários e suíte completa | 560 testes passando |
