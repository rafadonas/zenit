# Proxy e cache de tiles — PLANET-006

- Ticket: `PLANET-006`
- Decisão: [ADR-0085](../decisions/ADR-0085-authenticated-tile-proxy.md)
- Rota: `GET /v1/tiles/{provider}/{z}/{x}/{y}.png`
- Status: implementado e **desligado por padrão**; licença e privacidade pendentes

## Escopo

| Dentro | Fora |
| --- | --- |
| rota autenticada que serve tile do provedor pelo backend | uso público, alto volume ou operacional |
| cache local com TTL e limite de entradas | proxy ou cache de OpenStreetMap |
| limite de requisições por usuário | troca do mapa-base do dashboard |
| atribuição obrigatória do provedor | cota financeira ou contrato |

## Critérios de aceite

| # | Critério | Status | Evidência |
| --- | --- | --- | --- |
| A1 | Desligado por padrão | atendido | `tile_proxy_enabled` é `false`; teste confirma `404` |
| A2 | Chave do provedor nunca chega ao navegador | atendido | busca feita no backend; teste verifica corpo e cabeçalhos |
| A3 | Rota autenticada | atendido | requisição anônima recebe `401` |
| A4 | Provedor restrito a lista permitida | atendido | `openstreetmap` recebe `404` |
| A5 | Coordenadas validadas | atendido | zoom acima do limite e `x`/`y` fora da faixa recebem `400` |
| A6 | Limite por usuário, nunca por endereço | atendido | terceiro pedido recebe `429` com `Retry-After`; outro usuário mantém saldo próprio |
| A7 | Cache com TTL verificável | atendido | segunda requisição é `hit`; após o TTL volta a ser `miss` |
| A8 | Atribuição sempre presente | atendido | cabeçalho `X-Tile-Attribution`; sem atribuição configurada a rota fica fechada |
| A9 | Falha do provedor não quebra a API | atendido | upstream indisponível vira `503`, sem vazar a mensagem do provedor |
| A10 | Mapa continua usável com o proxy desligado | atendido | o dashboard segue carregando OSM direto; nada mudou nele |

## Dependências e aprovações

| Item | Situação |
| --- | --- |
| `PLANET-005` controle de cota | atendida |
| Licença de tiles, linhas L3 e L6 do [registro](../governance/licence-register.md) | **pendente** |
| Decisão D6 da [base de privacidade](../governance/privacy-baseline.md), endereço do visitante | **pendente** |
| Revisão de segurança da rota | **pendente** |

Enquanto as duas primeiras estiverem pendentes, **manter `TILE_PROXY_ENABLED=false`**.

## Configuração quando for aprovado

```bash
TILE_PROXY_ENABLED=true
TILE_PROXY_UPSTREAM_TEMPLATE=https://<provedor>/{z}/{x}/{y}.png   # precisa ser HTTPS
TILE_PROXY_ATTRIBUTION="© <provedor>"
TILE_PROXY_CACHE_TTL_SECONDS=86400
TILE_PROXY_RATE_LIMIT_PER_MINUTE=60
```

Sem `TILE_PROXY_ATTRIBUTION`, a rota permanece fechada de propósito: servir tile
sem atribuição violaria os termos de uso.

## Limitações conhecidas

- **Cache por processo:** reiniciar esvazia, e cada worker mantém a própria
  cópia. Suficiente para a demonstração acadêmica; um cache compartilhado exigiria
  armazenamento de objetos ou Redis.
- **Limite por processo:** o mesmo vale para a contagem de requisições por
  usuário.
- **OpenStreetMap continua direto**, sem proxy nem cache, porque a política da
  comunidade não autoriza cache de terceiros.
- **O dashboard ainda não usa a rota**; a troca é um ticket próprio, depois da
  licença.

## Verificação executada em 2026-09-15

17 testes cobrem: rota fechada por padrão, fechada sem atribuição, `401` anônimo,
provedor fora da lista, coordenadas inválidas, limite por usuário com
`Retry-After`, saldo independente por usuário, `hit`/`miss` de cache, expiração
por TTL, falha do provedor como `503`, ausência da chave na resposta, template
obrigatoriamente HTTPS e upstream não configurado. O contrato OpenAPI foi
regenerado com a rota nova.
