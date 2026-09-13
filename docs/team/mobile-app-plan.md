# Plano do aplicativo móvel

## Missão

Oferecer ao time de campo uma jornada offline-first que preserve identidade,
ordem, evidência, localização, medições, fotos, sincronização e auditoria. A
experiência precisa funcionar sob rede instável e não pode transformar ensaios
simulados em execução real.

## Estado atual preservado

O P0 já possui autenticação online, token seguro, cofre criptografado, ordens
preparadas, UUID/idempotência, eventos offline, manifestos antes dos bytes,
recuperação de upload e logout que não apaga pendências. GPS, roçada e pós-serviço
atuais permanecem simulados/preparados e inelegíveis.

## Problema estrutural

`lib/main.dart` e `lib/app_controller.dart` acumulam milhares de linhas. Isso
aumenta conflitos, mistura composição visual com orquestração e dificulta testes
por feature. A primeira mudança é decomposição comportamentalmente neutra.

## Estrutura alvo incremental

```text
lib/
  app/               # bootstrap, theme, navigation, session boundary
  core/              # errors, clock, connectivity abstractions, utilities
  design_system/     # tokens and reusable widgets
  features/
    auth/
    work_orders/
    inspection/
    mowing_rehearsal/
    post_service/
    sync_center/
  data/              # gateway, secure storage, encrypted vault
  domain/            # immutable models and rules
```

Não mover modelos/gateway/cofre junto com telas sem necessidade. Primeiro extrair
widgets e controladores de feature com testes; depois reduzir arquivos centrais.
Adicionar router/state package é uma decisão de dependência, não pressuposto.

## Navegação alvo

1. Bootstrap seguro: cofre, sessão e pendências.
2. Login quando necessário.
3. Inbox: ordens disponíveis, baixadas e em andamento.
4. Detalhe da ordem: objetivo, local, elegibilidade e dados offline.
5. Execução guiada: confirmação → ponto → medição/foto → revisão.
6. Resumo local antes de finalizar.
7. Central de sincronização.
8. Histórico local permitido e configurações/sessão.

Back impede perda silenciosa. Deep links só abrem dados que o usuário autenticado
pode acessar e que existam no cofre.

## Especificação das telas

### Bootstrap

- progresso curto e acessível;
- falha do secure storage/cofre oferece recuperação sem apagar pendências;
- sessão expirada leva ao login preservando dados locais;
- versão do app e ambiente disponíveis em diagnóstico.

### Login

- senha nunca armazenada;
- mostrar necessidade de conexão;
- erros sem enumerar conta;
- ambiente de demonstração explicitamente rotulado;
- não permitir HTTP em build produtivo.

### Inbox de ordens

- grupos “Em andamento”, “Disponíveis offline”, “Aguardando download” e “Concluídas
  localmente/aguardando envio”;
- status de dado/elegibilidade e última sincronização;
- busca/filtro simples, sem esconder ordens ativas;
- empty/error com próxima ação.

### Detalhe

- rodovia/km/side/zone e segmento de 100 m;
- origem, data, responsável, objetivo e limitações;
- checklist do que ficará disponível offline;
- botão primário específico: “Baixar”, “Continuar” ou “Revisar envio”.

### Coleta

- stepper com exatamente os pontos exigidos pelo contrato vigente;
- número do ponto, localização/precisão e instrução visível;
- campo de altura com unidade e limites de validação;
- captura orientada, preview, refazer e integridade;
- rótulo de cobertura manual apenas após taxonomia aprovada;
- autosave no cofre e confirmação não intrusiva;
- finalizar somente com requisitos satisfeitos.

### Central de sincronização

- contador global e itens por ordem;
- `pending`, `sending`, `accepted`, `rejected`, `conflict` e bytes pendentes;
- mensagem acionável e correlation ID quando disponível;
- retry idempotente; nunca recriar UUID;
- manifesto aceito antes de upload explícito dos mesmos bytes;
- logout explica revogação remota não confirmada e pendências retidas.

## GPS e privacidade

GPS real é P1 e depende de aprovação. Quando implementado:

- solicitar permissão no momento de uso com explicação;
- registrar coordenada, precisão, timestamp e provider;
- rejeitar/inspecionar precisão fora do critério aprovado;
- nunca fingir ponto estimado como coletado;
- minimizar retenção e exposição; aplicar política de dados pessoais;
- testar permissão negada, “apenas durante uso”, provider desligado e mock location
  conforme threat model;
- trabalho fora da zona gera aviso/inspeção, não correção silenciosa.

## Foto e diferenciação árvore/grama

O app não executará classificação local antes da validação do plano de inteligência.
No P1 ele pode coletar rótulo humano, qualidade e evidência conforme protocolo:

- overlay de enquadramento sem alterar o arquivo original;
- checagens técnicas (blur/exposição/tamanho) explicáveis;
- escala visível e ponto correspondente;
- `unknown` e motivo disponíveis;
- arquivo criptografado, SHA-256 local e manifesto rastreável;
- preview/crop nunca substitui o original;
- resultado futuro de IA aparece como sugestão estimada e revisável.

## Offline e recuperação

Testar sistematicamente:

- modo avião antes/depois do login e download;
- processo encerrado em cada etapa;
- reboot e cofre bloqueado;
- token expirado com pendências;
- timeout, resposta parcial, 401, 403, 409 e 5xx;
- manifesto aceito/bytes não enviados;
- um de três pontos rejeitado;
- duplicação de toque/retry;
- logout offline e novo login da mesma/diferente conta.

Nenhuma recuperação apaga automaticamente evidência não reconhecida pelo servidor.

## Design e acessibilidade de campo

- componentes/tokens seguem `design-system.md`;
- alvo mínimo 44 px e controles críticos maiores quando possível;
- contraste testado sob luz forte;
- suporte a escala de fonte e orientação permitida pelo fluxo;
- ícone + texto + cor para status;
- feedback háptico é auxiliar, nunca único;
- mensagens curtas, unidade junto ao valor e ação primária fixa quando não cobrir
  conteúdo/foco;
- semantics labels e ordem de foco testadas com leitor de tela.

## Estratégia de testes

- unitários: regras, reducers/controladores e serialização;
- widgets: todos os estados de tela e navegação;
- integração: cofre, restart, sync e gateway falso;
- golden opcional após decisão de ferramenta/estabilidade de fontes;
- aparelho/emulador: câmera, armazenamento, rede e acessibilidade;
- contrato: fixtures geradas/versionadas contra OpenAPI;
- APK: manifesto, ABIs, SDK, assinatura e evidência já previstas no repositório.

## Fases

1. MOB-001: decomposição neutra.
2. MOB-002: design system e componentes.
3. MOB-003/MOB-004: jornada e central de sync.
4. GEO-002/003 aprovados: captura orientada e rótulo manual.
5. política e piloto aprovados: GPS/câmera real controlados.
6. operação aprovada: assinatura, distribuição, suporte e observabilidade.

## Critério de conclusão P0 redesenhado

- mesmos limites de segurança e contratos;
- nenhum dado pendente perdido;
- jornadas compreensíveis online/offline;
- arquivos centrais reduzidos e features testáveis isoladamente;
- acessibilidade básica e tamanhos alvo;
- format, analyze, test e debug build verdes;
- evidência continua marcada como preparada/simulada/não verificada.
