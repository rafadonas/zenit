export interface DemoGuideStep {
  title: string;
  body: string;
  note?: string;
  action?: { label: string; href: string };
}

export const DEMO_GUIDE_CONTEXT = [
  "Hoje, o monitoramento da vegetação em rodovias ainda é manual, demorado e sem um padrão único. Identificar os trechos que realmente precisam de atenção depende de inspeção e acompanhamento humano.",
  "O ZENIT é uma plataforma de apoio à decisão: reúne as informações da rodovia, organiza os trechos e mostra, de forma visual, onde pode existir necessidade de atenção.",
] as const;

export const DEMO_GUIDE_HUMAN_DECISION =
  "O ZENIT não substitui a decisão humana. Ele dá mais clareza, rastreabilidade e organização ao processo.";

export const DEMO_GUIDE_STEPS: readonly DemoGuideStep[] = [
  {
    title: "Entenda como a rodovia é dividida",
    body: "A rodovia é dividida em trechos de cerca de 100 metros, o que deixa a análise mais detalhada e fácil de interpretar. Cada trecho é observado por zonas: lado esquerdo, lado direito, canteiro central e áreas especiais.",
  },
  {
    title: "Abra o mapa da rodovia",
    body: "No menu superior, clique em Mapa. A tela mostra a rodovia dividida em segmentos sobre o mapa-base.",
    action: { label: "Abrir o mapa", href: "/corridor" },
  },
  {
    title: "Selecione um trecho",
    body: "Clique em um segmento no mapa, escolha-o na Lista equivalente ao mapa ou digite a rodovia, o km ou o trecho no campo de busca e clique em Localizar. As informações daquele ponto aparecem em Detalhes do trecho; quando o trecho tem observação satelital registrada, o painel mostra também a zona observada.",
  },
  {
    title: "Analise a rodovia parte por parte",
    body: "Em vez de olhar a rodovia inteira de uma vez, compare os trechos um a um. Use o filtro Classe histórica (N1, N2 ou N3) e a legenda do mapa para ver a classificação de vegetação registrada em cada trecho.",
    note: "A classe histórica tem referência em 28/03/2025 e associação espacial inferida: ela organiza a leitura, mas não representa a condição atual da vegetação.",
  },
  {
    title: "Priorize os trechos que precisam de atenção",
    body: "Volte à Visão geral. O quadro Atenção e próxima ação indica o próximo trecho a revisar; clique em Revisar decisão para registrar a decisão humana sobre ele.",
    action: { label: "Ir para as decisões", href: "/recommendations" },
  },
  {
    title: "Identifique o que é real e o que é simulado",
    body: "Algumas etapas usam dados simulados, porque ainda dependem de uma base histórica maior, de imagens devidamente rotuladas e de medições de campo validadas. Cada informação traz um selo — Real, Estimado, Preparado, Simulado ou Inconclusivo — e os dados simulados ficam separados dos reais.",
  },
  {
    title: "Leia o resultado com o limite certo",
    body: "Nesta etapa, a simulação mostra de forma transparente e reproduzível como a plataforma funciona; ela não prova um resultado operacional real. Quando chegarem dados operacionais e evidências de campo, os mesmos fluxos, controles de qualidade e revisão humana continuam valendo.",
  },
];

export const DEMO_GUIDE_SUMMARY =
  "Em resumo, o ZENIT apoia o monitoramento da vegetação em rodovias com segmentação, mapa e visualização clara das informações, transformando dados em uma ferramenta prática para apoiar a decisão.";
