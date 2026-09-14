# GOV-001 — inventário visual e funcional

**Responsável:** rafadonas

**Revisão avaliada:** `5cca67b`

**Data da captura:** 2026-09-14

**Classificação:** evidência preparada/simulada, não operacional

## Resultado

As sete rotas do dashboard foram verificadas em `360`, `768`, `1024` e
`1440` px, sempre com viewport de `900` px de altura. O inventário também cobre
os estados globais `loading`, `empty`, `error` e `success`. As imagens e os
manifestos ficam em `data/processed/gov-001/`, que é ignorado pelo Git; somente
os capturadores e esta matriz são versionados.

Nenhuma captura autoriza trabalho de campo, valida altura por satélite ou serve
como relatório oficial. As identidades, filas, fotos e coordenadas exibidas são
fixtures locais preparadas ou simuladas e não podem ser usadas para treino de
modelo.

## Matriz do dashboard

| Rota | Responsável | Loading | Empty | Error | Success | Larguras |
| --- | --- | --- | --- | --- | --- | --- |
| `/login` | rafadonas | global | n/a | capturado | capturado (idle) | 360/768/1024/1440 |
| `/overview` | rafadonas | capturado e global | estrutural | global | capturado | 360/768/1024/1440 |
| `/corridor` | rafadonas | local e global | local | local e global | capturado | 360/768/1024/1440 |
| `/recommendations` | rafadonas | global | local | global | capturado | 360/768/1024/1440 |
| `/photo-reviews` | rafadonas | global | capturado | global | capturado | 360/768/1024/1440 |
| `/mowing-photo-reviews` | rafadonas | global | capturado | global | capturado | 360/768/1024/1440 |
| `/mowing-post-service-summaries` | rafadonas | global | capturado | local e global | capturado | 360/768/1024/1440 |

`global` significa que o estado é fornecido por `app/loading.tsx` ou
`app/error.tsx`; `local` significa que a própria rota apresenta o estado;
`estrutural` significa que a composição permanece válida com contadores sem
dados, mas não há uma tela vazia separada. O estado de sucesso inclui respostas
vazias válidas: a rota foi carregada com sessão e contrato válidos, ainda que a
fixture não contenha itens na fila.

## Jornadas mobile

O capturador Flutter usa gateway e cofre em memória, viewport `390 x 844` e
gera 21 imagens mais um manifesto com SHA-256. O conjunto cobre:

- bootstrap e login (`idle` e erro fixture);
- ordens vazias e carregadas;
- detalhe, três medições e três fotos preparadas de inspeção;
- lote local, falha de transporte, recuperação idempotente e recibos de upload;
- plano de roçada explicitamente não executável, pausa e retomada simuladas;
- medições e fotos pós-serviço simuladas;
- logout offline e recuperação;
- conflito/rejeição de sincronização;
- lista de ordens com escala de texto de 200%.

Os controles renderizados no manifesto mobile são medidos e sinalizados quando
possuem largura ou altura inferior a 44 px. Na execução registrada, os controles
interativos capturados não apresentaram esse desvio.

## Auditoria de rótulos e segurança

- A data de referência da planilha continua apresentada como histórica
  (`28/03/2025`), nunca como data atual.
- Eixo e geometria estimados aparecem como não operacionais.
- Filas e dados preparados permanecem identificados como demonstração, fixture,
  preparados ou simulados, conforme o contexto.
- Baixa confiança conduz à inspeção/revisão humana; a interface não promove a
  recomendação a autorização automática de roçada.
- Fotos e medições simuladas permanecem inelegíveis para treino e relatório
  oficial.
- O manifesto registra hashes de fontes e imagens, mas não cookies, tokens,
  senhas, cabeçalhos ou valores de variáveis de ambiente.
- A identidade `manager@example.com` é fixture local documentada, não dado
  pessoal real.

## Evidências e reprodução

Dashboard:

```bash
node apps/dashboard/scripts/capture-gov-001.mjs
```

O capturador espera dois servidores locais: um bootstrap de sessão fixture em
`http://127.0.0.1:3000` e a revisão atual sem sessão fixa em
`http://127.0.0.1:3100`. O segundo deve usar os mesmos nomes de cookie do
bootstrap. URLs diferentes podem ser fornecidas pelas variáveis
`GOV_001_UNAUTHENTICATED_BASE_URL`,
`GOV_001_AUTHENTICATED_BOOTSTRAP_BASE_URL` e
`GOV_001_AUTHENTICATED_CAPTURE_BASE_URL`; o script rejeita destinos que não
sejam loopback HTTP.

Mobile:

```bash
cd apps/mobile
flutter test tool/gov_001_capture_test.dart
```

Saídas ignoradas:

- `data/processed/gov-001/web/manifest.json` e 33 PNGs (28 estados principais,
  quatro erros de login e o loading global em 360 px);
- `data/processed/gov-001/mobile/manifest.json` e 21 PNGs.

## Débitos encaminhados

| Débito observado | Destino | Prioridade |
| --- | --- | --- |
| Cores, espaçamento, raios, sombras, movimento, breakpoints e z-index ainda não formam uma camada única de tokens. | WEB-001 | P0 |
| A navegação de 360 px cabe na viewport, mas fica densa e precisa continuar coberta por regressão após a extração de tokens. | WEB-001 | P0 |
| Capturas de viewport não substituem navegação completa por teclado, leitor de tela ou dispositivo físico. | QA/a11y subsequente | P1 |
| O mapa depende de geometria estimada e não pode ser usado para ordem ou geofence. | Pipeline geoespacial oficial | bloqueador operacional |

## Limitações

- As capturas web são de viewport, não de página inteira.
- Chrome headless não substitui teste de teclado, leitor de tela ou contraste em
  dispositivo representativo.
- O harness Flutter não cobre câmera, GPS, TalkBack, teclado de plataforma,
  encerramento de processo ou armazenamento seguro real.
- Tiles e geometria do mapa não são evidência oficial.
