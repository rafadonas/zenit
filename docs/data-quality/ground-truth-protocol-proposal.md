# Proposta de protocolo de ground truth vegetal

- Status: proposta para desenho e revisão
- Versão: `zenit-ground-truth-v0.1-draft`
- Data: 2026-09-14
- Data owner do projeto: Rafael
- Escopo atual: documentar o protocolo; nenhuma coleta real foi iniciada

## Objetivo e limites

O protocolo define como uma observação de campo poderá produzir rótulos e
medições revisáveis para a taxonomia `zenit-cover-taxonomy-v0.1-draft`. Ele foi
desenhado para alimentar uma futura avaliação ou treinamento de IA, sem
transformar uma previsão em altura, urgência ou autorização de roçada.

O repositório continua usando dados `prepared`/`simulated` no demonstrador. Esses
dados servem para testar a jornada, mas são proibidos em treinamento, avaliação
oficial ou relatório. A coleta real descrita aqui só começa depois de uma
decisão de piloto, consentimento e política de retenção.

## Unidade e estratificação

- Unidade espacial: segmento rodoviário de 100 m e uma zona por vez — esquerda,
  direita, canteiro central ou especial.
- Unidade de observação: ponto planejado ou ponto real associado ao segmento,
  com sequência, direção/side, zona e relação espacial preservadas.
- Estratos mínimos: rodovia, zona, classe histórica disponível, estação/período,
  iluminação, condição climática, sensor/dispositivo e qualidade esperada.
- Casos difíceis entram deliberadamente na amostra: sombra, blur, oclusão,
  mistura, pavimento/solo ambíguo e evidências conflitantes.
- Pontos vizinhos do mesmo local não podem ser divididos entre treino e teste.
  Holdout espacial por trecho/rodovia e holdout temporal por período devem ser
  definidos no manifesto do dataset.

Não usar a data de referência da planilha (2025-03-28) como data de coleta ou
condição atual.

## Captura de campo candidata

Cada coleta real deve guardar, em manifesto separado dos bytes de mídia:

| Campo | Regra |
| --- | --- |
| `observation_id` | UUID persistente e imutável. |
| segmento/zona/side | Identificação do trecho de 100 m e da zona observada. |
| `captured_at` | Data/hora com fuso e origem do dispositivo. |
| `gps_status` | `real`, `simulated` ou `unavailable`. O app atual permanece `simulated`. |
| latitude/longitude | Somente quando permissão e consentimento forem válidos; preservar SRID. |
| `gps_accuracy_m` | Precisão informada pelo dispositivo, sem arredondar para criar falsa exatidão. |
| `location_consent_reference` | Referência da autorização/política, sem guardar texto pessoal desnecessário. |
| `device_reference` | Identificador pseudonimizado e rotacionável; nunca IMEI ou segredo. |
| foto de contexto | Enquadramento da zona e do entorno, com origem e checksum. |
| foto de medição | Vegetação e escala/régua visíveis quando altura for medida. |
| orientação | Direção de captura, side e zona; registrar ausência quando desconhecida. |
| qualidade | Exposição, foco, oclusão, integridade e motivo de rejeição. |

Rostos, placas e outros dados pessoais devem ser evitados no enquadramento e
tratados conforme uma política aprovada. Não substituir uma foto real por imagem
sintética para parecer evidência; uma imagem de demonstração deve permanecer
explicitamente simulada/preparada.

## Anotação da cobertura

O anotador registra o valor da taxonomia e os atributos complementares:

- `cover_type`: `unknown`, `grass_herbaceous`, `shrub`, `tree`, `mixed` ou
  `non_vegetation`, extensível apenas por nova versão;
- `unknown_reason` específico quando aplicável (`shadow`, `blur_or_exposure`,
  `canopy_occlusion`, `source_conflict`, `insufficient_resolution` ou outro
  valor controlado);
- `coverage_band`, `visibility`, `dominance`, `spatial_relation` e
  `quality_status`;
- altura medida separadamente, com unidade, método, escala e incerteza — nunca
  inferida do tipo de cobertura;
- fonte, data, versão da taxonomia e justificativa curta.

Copa sobre a faixa e tronco fora dela são relações espaciais distintas e devem
ser decididas caso a caso. Gramínea sob árvore pode ser `mixed` quando ambos
forem relevantes; oclusão que impeça a leitura deve manter `unknown` com motivo.
Esquerda, direita, mediana e especial não compartilham rótulo por conveniência.

## IA assistida e revisão humana

Um modelo poderá sugerir `cover_type` e `unknown_reason`, mas a sugestão deve
ser marcada `model_estimated`, manter versão/confiança/limitações e aguardar
revisão humana. A interface não deve mostrar confiança como probabilidade exata
de altura.

O protocolo de produção de rótulo exige:

1. dois anotadores independentes em uma amostra de calibração;
2. registro de cada decisão e justificativa, sem sobrescrever o rótulo original;
3. adjudicação dos conflitos por uma regra definida pelo projeto quando não
   houver especialista dedicado;
4. publicação de concordância por classe, zona e condição de qualidade;
5. separação entre rótulo humano, sugestão do modelo e rótulo final aceito.

Enquanto o piloto de concordância não existir, qualquer conjunto permanece
`draft`/`prepared` e não pode ser tratado como ground truth validado.

## Privacidade, consentimento e retenção

Antes de capturar GPS ou foto real, o data owner deve registrar uma política
mínima de finalidade, consentimento, acesso, anonimização, retenção e descarte.
O protótipo pode exercitar esses campos com valores simulados, mas não deve
coletar dados pessoais reais sem essa decisão. Bytes grandes ficam fora do Git;
manifestos preservam checksum, linhagem, licença/consentimento e status.

## Critérios de aceite do protocolo

- amostragem cobre rodovia, zona, período e condições difíceis;
- GPS real possui permissão, precisão, consentimento e SRID registrados;
- fotos têm contexto, escala quando necessária, qualidade e checksum;
- dupla anotação/adjudicação e métrica de concordância estão planejadas;
- divisão espacial/temporal evita vazamento entre treino e teste;
- dados demo/simulados são excluídos do dataset de treinamento;
- taxonomia, método de IA, versão, limitações e revisão humana são rastreáveis;
- nenhuma saída cria autorização de campo ou relatório oficial.

O próximo passo seguro é um piloto pequeno e reversível, após as políticas de
privacidade/permissão. Até lá, consumidores devem exibir `gps_status=simulated`
e manter a classificação como preparada ou estimada.
