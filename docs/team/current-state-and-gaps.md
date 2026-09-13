# Estado atual e lacunas do ZENIT

Data do diagnóstico: **2026-09-12**. Este documento descreve o repositório, não
uma implantação produtiva.

## Resumo executivo

O ZENIT já possui uma base ampla: FastAPI, PostgreSQL/PostGIS, MinIO, dashboard
Next.js, app Flutter offline-first, importadores geoespaciais, contratos, trilha
de decisões e testes. O fluxo demonstrativo cobre login, corredor, recomendações,
revisões, ordens preparadas, coleta simulada e sincronização idempotente.

As principais lacunas são de produto e operacionalização:

- a interface web cresceu por telas grandes e CSS global, sem uma biblioteca de
  componentes implementada;
- a linguagem visual existe em PDF, mas ainda não é uma especificação executável
  versionada no código;
- mapa e polígonos históricos já aparecem, porém ainda faltam navegação espacial,
  filtros, semântica visual consistente, lista equivalente e dados atuais;
- árvore, arbusto e gramínea não possuem taxonomia validada nem conjunto de dados
  rotulado; portanto ainda não existe modelo confiável para distingui-los;
- o aplicativo móvel tem boa segurança/offline P0, mas duas classes concentram a
  maior parte da interface e da orquestração;
- usuários, eixo oficial, zonas, limites, equipes, provedores, GPS e políticas de
  operação ainda exigem decisões e evidências reais;
- `services/ai-worker` ainda não contém um pipeline operacional de IA.

## O que já existe

### Plataforma e backend

- monorepo modular com Python 3.12+, Node.js 22+, Flutter e Docker Compose;
- API FastAPI com autenticação, papéis manager/supervisor, CSRF no dashboard,
  correlação de erros e contrato OpenAPI versionado;
- PostGIS com migrações append-only até a versão presente no repositório;
- catálogo de fontes, checksums, proveniência, auditoria e estados de dados;
- importadores para marcos quilométricos, polígonos históricos e planilhas;
- segmentos de 100 m e zonas left/right/median/special representados no domínio;
- recomendações explicáveis, revisão humana e artefatos preparados de campo;
- MinIO e fluxo de manifesto antes do upload de foto;
- testes Python, TypeScript e Flutter, build web/APK e smoke de Compose na CI.

### Dashboard web

Rotas atuais relevantes:

- `/login`;
- `/overview`;
- `/corridor` e a experiência de corredor/mapa;
- `/recommendations`;
- `/photo-reviews`;
- `/mowing-photo-reviews`;
- `/mowing-post-service-summaries`.

O mapa usa MapLibre com base cartográfica OSM e exibe centenas de polígonos
históricos. Login local foi preparado para as experiências de gerente e
supervisor. Há 42 arquivos de teste de dashboard no diagnóstico.

### Aplicativo móvel

- login online por senha e token em armazenamento seguro;
- cofre Hive CE criptografado e dados pendentes preservados no logout;
- download de ordens e planejamento preparados;
- eventos e lotes com UUID persistente e sincronização idempotente;
- fluxo de inspeção e ensaio de roçada offline;
- três medições e manifestos/fotos preparados;
- falha fechada quando elegibilidade ou proveniência é inválida;
- backup e transferência Android desabilitados.

Tudo isso continua marcado como preparado, simulado, não verificado e inelegível
para execução, relatório oficial ou treinamento conforme o fluxo específico.

## Inventário das lacunas

### 1. Produto, governança e dados reais

| Lacuna | Impacto | Prioridade | Condição de saída |
| --- | --- | --- | --- |
| eixo e geometria oficiais não homologados | segmentação pode não representar o contrato real | P1 | aceite formal, SRID e versão registrados |
| mapeamento de `classificacao_rocada.kmz` inferido | classes podem estar interpretadas incorretamente | P0/P1 | validação humana documentada sem alterar o original |
| limites de confiança/qualidade não oficializados | inspeção pode ser disparada de forma inconsistente | P1 | política versionada e aprovada |
| identidade, equipes e papéis são locais/preparados | sem governança de acesso operacional | P1 | IdP/política/recertificação aprovados |
| dados de planilha não atuais | risco de comunicar estado antigo como presente | P0 | data de referência sempre visível |
| não há catálogo validado árvore/grama/arbusto | inviabiliza treinamento e avaliação séria | P1 | taxonomia, guia de anotação e amostra auditada |

### 2. Dashboard e experiência

- `styles.css` global concentra tokens, layout e componentes;
- páginas de revisão e recomendação são extensas e repetem estruturas;
- estados loading, empty, error, stale, unauthorized e partial não têm um
  padrão único;
- navegação, cabeçalhos, filtros e painéis não formam uma biblioteca reutilizável;
- responsividade existe parcialmente, mas precisa de validação real em
  360/768/1024/1280/1440 px e zoom de 200%;
- mapa precisa de busca por rodovia/km, filtros, seleção persistente, legenda
  dupla, detalhes temporais, lista acessível e desempenho por viewport;
- severidade operacional, classe histórica N1/N2/N3 e tipo de cobertura vegetal
  podem ser confundidos visualmente;
- exemplos fictícios do guia visual não podem aparecer como indicadores reais;
- faltam telemetria de UX, testes visuais e critérios de qualidade percebida.

### 3. Vegetação, imagens e precisão

- polígonos atuais são evidência histórica/preparada, não segmentação semântica
  atual de gramínea e árvore;
- NDVI mede vigor relativo e não prova altura nem espécie/tipo isoladamente;
- não há protocolo de foto de campo, escala, ângulo, luz e oclusão homologado;
- não há dataset manifestado, licenciado e separado por rodovia/tempo;
- não há baseline de segmentação/classificação nem métricas por classe e zona;
- não há validação cruzada espacial/temporal, calibração ou monitoramento de drift;
- ausência de árvore/grama deve ser representada como `unknown`, não inferida;
- sensores adequados para altura real (campo, LiDAR, estéreo ou equivalente)
  ainda precisam de decisão e validação.

### 4. Aplicativo móvel

- `lib/main.dart` e `lib/app_controller.dart` concentram UI/estado/orquestração;
- não há pacote de componentes/tokens alinhado ao dashboard;
- navegação e recuperação de estado precisam ser modularizadas;
- GPS real ainda não é coletado; as coordenadas atuais são simuladas;
- falta orientação de captura para distinguir cobertura e garantir escala;
- fila de sincronização precisa de visualização e recuperação orientada ao usuário;
- permissões, privacidade, retenção, assinatura e distribuição produtiva não estão
  aprovadas;
- faltam testes de widget/golden por estados críticos, acessibilidade de campo e
  avaliação em aparelho sob luz externa.

### 5. Arquitetura e manutenção

- módulos grandes elevam risco de conflito entre colaboradores;
- o worker de IA precisa ser criado somente após contrato e dataset aprovados;
- alterações de esquema/OpenAPI exigem coordenação centralizada;
- não há ambiente de staging operacional nem observabilidade/alertas definidos;
- backup/restauração, recuperação de desastre, retenção e resposta a incidentes
  precisam de runbooks testados;
- basemap público exige internet e seus termos/capacidade não são uma solução de
  produção aprovada.

## Classificação correta de dados na interface

Toda tela e exportação deve exibir uma destas condições de maneira legível:

- **real:** coletado por processo e fonte aprovados;
- **estimado:** derivado com método, versão e incerteza conhecidos;
- **simulado:** criado para ensaio e nunca elegível para operação;
- **preparado:** estrutura pronta, ainda sem validação operacional;
- **inconclusivo:** evidência insuficiente ou conflitante.

Uma confiança de modelo não é probabilidade exata de altura. Baixa confiança
normalmente gera recomendação de inspeção, nunca autorização silenciosa de roçada.

## Definição de “pronto” por maturidade

### Demonstrativo confiável

- rotas principais navegáveis e estados de erro compreensíveis;
- dados antigos, simulados e preparados claramente rotulados;
- testes e builds verdes;
- nenhuma ação visual implica autorização operacional.

### Piloto controlado

- fontes, usuários, rodovias, equipes, limites e responsabilidades aprovados;
- coleta real com consentimento/permissões, auditoria e recuperação;
- monitoramento, suporte e rollback;
- evidência de campo e critérios de aceite documentados.

### Produção

- SLOs, segurança, privacidade, backup/restauração e resposta a incidente testados;
- modelos promovidos por gate humano com dataset/model card versionados;
- relatórios oficiais usam somente dados elegíveis e rastreáveis;
- aprovação humana continua sendo requisito para decisão de roçada.
