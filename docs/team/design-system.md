# ZENIT design system — especificação executável v2

Este guia traduz a direção visual existente em regras aplicáveis ao dashboard e
ao app. Ele não concede autorização para usar a marca Motiva e não transforma
exemplos fictícios em dados oficiais.

## 1. Princípios

1. **Movimento com propósito:** cada tela leva a uma decisão ou próximo passo.
2. **Dados antes do ornamento:** fonte, data, estado e limitação acompanham o valor.
3. **Calma operacional:** hierarquia forte, pouco ruído e ações irreversíveis lentas.
4. **Humano no controle:** recomendação não é autorização; aprovação é explícita.
5. **Entendimento em dez segundos:** situação, atenção e ação aparecem primeiro.
6. **Acessível por construção:** WCAG 2.2 AA, teclado e alternativa ao mapa.

Distribuição visual de referência: 70% superfícies claras, 20% identidade e 10%
cores de dados/status. Não é uma fórmula rígida de pixels.

## 2. Tokens de base

### Cores neutras e de marca

| Token | Valor inicial | Uso |
| --- | --- | --- |
| `--color-brand-600` | `#5A26FF` | ação primária e identidade |
| `--color-brand-800` | `#35129A` | hover/pressed em superfície clara |
| `--color-brand-100` | `#EEE9FF` | seleção e destaque discreto |
| `--color-canvas` | `#F7F7FA` | fundo da aplicação |
| `--color-surface` | `#FFFFFF` | cards, drawers e modais |
| `--color-text` | `#202024` | texto principal |
| `--color-text-muted` | `#68686F` | texto secundário aprovado por contraste |
| `--color-border` | `#E4E3EC` | separadores e bordas |

### Status operacional

| Status | Cor inicial | Sempre acompanhado por |
| --- | --- | --- |
| normal | `#148A45` | ícone + “Normal” |
| attention | `#D8A900` | ícone + “Atenção” |
| near_limit | `#F06A32` | ícone + “Próximo ao limite” |
| critical | `#D82C55` | ícone + “Crítico” |
| unknown | neutro/textura | ícone + “Inconclusivo” |

Cor nunca é o único sinal. Testar texto e controles contra a superfície real.

### Tipografia, espaço e forma

- família: Inter quando empacotada/aprovada; fallback `system-ui, sans-serif`;
- corpo padrão: 16 px/24 px; mínimo operacional: 14 px/20 px;
- títulos seguem escala 20/24, 24/32, 32/40, sem reduzir para caber;
- pesos: 400 corpo, 500 rótulo, 600 título/ênfase;
- espaçamento: múltiplos de 4 px, preferindo 8, 12, 16, 24, 32, 40 e 48;
- raio: 8 px controles, 12 px cards, 16 px painéis importantes;
- sombra discreta; não usar sombra para substituir borda/foco;
- alvo interativo mínimo: 44 × 44 px.

### Movimento

- 120 ms microfeedback; 180 ms controles; 240 ms painéis; 300 ms transições raras;
- animar opacidade/transform quando necessário;
- evitar movimento ornamental no mapa e em indicadores;
- `prefers-reduced-motion: reduce` remove transições não essenciais.

## 3. Três semânticas que não podem se misturar

### Status operacional

Normal, atenção, próximo ao limite e crítico descrevem necessidade de atenção.

### Classe histórica de altura

- N1: `< 10 cm`;
- N2: `10–30 cm`;
- N3: `> 30 cm`.

N1/N2/N3 são preservadas por compatibilidade histórica. A interface mostra data,
fonte e rótulo “histórico” quando aplicável. Em zona especial, o limite geral de
30 cm não substitui o limiar de 10 cm.

### Tipo de cobertura vegetal

`unknown`, gramínea/herbácea, arbusto, árvore, misto e não vegetação descrevem o
objeto, não a urgência. Use ícones, padrões/contornos e texto; não reutilize a
escala verde-amarelo-vermelho de severidade.

Exemplo: uma árvore pode estar “normal”; uma gramínea pode estar “crítica”.

## 4. Layout responsivo

- 360–767 px: uma coluna, navegação inferior ou drawer, painel do mapa em sheet;
- 768–1023 px: sidebar compacta de 72 px e conteúdo fluido;
- 1024+ px: sidebar de 240 px, painel contextual lado a lado quando couber;
- referências de teste: 360, 768, 1024, 1280 e 1440 px;
- zoom 200% deve reflow sem rolagem horizontal de conteúdo principal, exceto
  tabelas/mapas que possuam mecanismo acessível de navegação.

Grid desktop recomendado: 12 colunas; tablet: 8; mobile: 4. Use container máximo
somente em formulários/texto; mapas e tabelas operacionais podem ocupar largura.

## 5. Hierarquia de tela

Cada rota segue:

1. contexto: ambiente, papel, rodovia e referência temporal;
2. título e descrição curta;
3. situação resumida;
4. exceções/atenção;
5. ação primária única;
6. exploração e detalhes progressivos;
7. fonte, método, versão e limitações.

Não coloque quatro botões primários no mesmo bloco. Ações destrutivas ou que
alteram decisão exigem linguagem específica, justificativa quando aplicável e
confirmação proporcional ao risco.

## 6. Componentes obrigatórios

- `Button` e `IconButton` com loading/disabled/focus;
- `DataStatus` para real/estimated/simulated/prepared/inconclusive;
- `OperationalStatus` separado de `HistoricalHeightClass` e `CoverType`;
- `Card`, `PageHeader`, `SectionHeader` e `Metric` com fonte/data;
- `EmptyState`, `ErrorState`, `StaleState`, `Skeleton` e `InlineAlert`;
- `FilterBar` responsiva com limpar filtros e contagem;
- `Drawer/Dialog` com foco contido, Escape e retorno de foco;
- tabela com caption, cabeçalhos, ordenação anunciada e alternativa mobile;
- imagem/evidência com alt contextual, zoom por controles e metadados;
- `ProvenancePanel` com origem, checksum/ID, método, versões e validação.

Estados mínimos de todo componente assíncrono: idle, loading, empty, partial,
success, stale, forbidden e error/retry.

## 7. Mapa

O mapa é protagonista, mas nunca a única forma de acessar a informação.

- base discreta com rótulos legíveis; termos/licença/atribuição sempre visíveis;
- segmentos/zonas têm halo/contorno suficiente sobre qualquer tile;
- seleção tem estilo independente de severidade;
- hover nunca é a única interação; foco e clique abrem o mesmo detalhe;
- legenda persistente separa status, N1/N2/N3 e cobertura;
- filtro mostra quais camadas/datas/fontes estão ativas;
- lista/tabela equivalente sincroniza seleção e serve como fallback;
- falha de tiles mantém lista, filtros e detalhes funcionais;
- tooltip curto; evidência completa em drawer/painel;
- clusters apenas para pontos; polígonos são simplificados por zoom sem alterar o
  dado armazenado;
- padrões/ícones distinguem cobertura; cores indicam status apenas quando esse é o
  modo ativo;
- “última observação” e validade temporal ficam visíveis.

## 8. Conteúdo e vocabulário

Preferir frases curtas e concretas:

- “Recomendar inspeção” em vez de “Processar”;
- “Aguardando revisão humana” em vez de “Pendente” sem contexto;
- “Estimativa histórica de 28/03/2025” em vez de “Altura atual”;
- “Não foi possível carregar os tiles; a lista continua disponível” em vez de
  “Erro desconhecido”.

Não usar “IA decidiu”, “100% preciso”, “altura confirmada” ou “roçada autorizada”
sem evidência e ato humano correspondentes.

## 9. Imagens e marca

- fotos reais precisam de origem, permissão, data, localidade com política de
  privacidade e texto alternativo;
- ilustrações geradas por IA são rotuladas e não servem como evidência ou treino;
- não criar fotografias sintéticas para preencher estados de dados;
- miniaturas mantêm proporção; crop nunca remove régua/evidência relevante;
- logotipo tem área de respiro e versão monocromática definidas somente após
  aprovação de marca;
- exemplos conceituais de rodovia, KPI ou vegetação usam claramente “Exemplo” ou
  “Simulado”, nunca aparência de telemetria real.

## 10. Acessibilidade e validação

Antes do merge:

- navegar toda a jornada só por teclado;
- foco visível com contraste;
- landmarks e títulos únicos;
- mensagens de erro associadas ao campo;
- atualização assíncrona anunciada sem excesso;
- contraste WCAG 2.2 AA;
- zoom 200%, texto ampliado e reduced motion;
- mapa com lista equivalente;
- gráficos com resumo textual e tabela quando necessária.

## 11. Governança de mudança

Tokens e componentes compartilhados têm dono de revisão. Uma alteração semântica
exige changelog e migração dos consumidores. Novos padrões entram primeiro neste
guia, depois no código e por fim nas telas. Ferramentas como Storybook, bibliotecas
de componente, fonte externa ou serviço de mapa são decisões de dependência e
licença; não devem ser adicionadas automaticamente.
