# Proposta de taxonomia de cobertura vegetal

- Status: proposta para revisão
- Versão: `0.1-draft`
- Data: 2026-09-14
- Dono da proposta: trilha geoespacial e inteligência vegetal
- Aprovação necessária: especialista em vegetação e data owner

## Objetivo e limite

Esta proposta descreve como rotular o tipo de cobertura observável em uma zona
de um trecho rodoviário. Ela serve para alinhar anotação manual, revisão de
qualidade e futura evolução de contrato. Não é um schema oficial, não promove
nenhuma fonte a dado real e não autoriza roçada ou qualquer trabalho de campo.

O rótulo de cobertura é independente de:

- classe histórica de altura (`N1`, `N2`, `N3`);
- status operacional ou urgência;
- índice espectral, especialmente NDVI;
- estimativa de altura em centímetros.

Quando a evidência não sustenta uma classe, o rótulo correto é `unknown`.

## Vocabulário candidato

| Valor estável | Definição de anotação | Não confundir com |
| --- | --- | --- |
| `unknown` | Evidência insuficiente, ilegível ou conflitante para identificar o tipo. | “Não há vegetação”. Ausência de evidência não é `non_vegetation`. |
| `grass_herbaceous` | Gramínea, herbácea ou forração sem estrutura lenhosa dominante visível. | Altura, severidade ou classe N1/N2/N3. |
| `shrub` | Vegetação lenhosa de porte arbustivo, incluindo cerca viva quando o arbusto é o objeto dominante. | Uma muda isolada sem evidência suficiente ou copa arbórea. |
| `tree` | Indivíduo arbóreo, palmeira ou dossel claramente arbóreo dominante na evidência. | Uma copa distante que apenas sobrepõe visualmente a faixa. |
| `mixed` | Dois ou mais tipos relevantes, sem dominância confiável para uma classe única. | Mistura causada somente por sombra, blur ou pixels sem resolução. |
| `non_vegetation` | Pavimento, solo exposto, estrutura, água ou outro alvo sem cobertura vegetal relevante observável. | Solo com rebrote que não pode ser descartado; nesse caso usar `unknown` ou a classe observável. |

O valor persistido deve ser exatamente um dos identificadores acima. Rótulos de
interface podem ser traduzidos, mas não devem alterar o identificador.

## Atributos que acompanham o rótulo

O tipo não carrega sozinho a qualidade ou a relação espacial. Uma futura
observação deve manter, no mínimo:

| Atributo | Valores/forma | Regra |
| --- | --- | --- |
| `cover_type` | valor da tabela acima | Obrigatório somente após aprovação do vocabulário. |
| `coverage_band` | `none`, `sparse`, `partial`, `dominant`, ou percentual revisado | Não converter faixa em altura. |
| `visibility` | `clear`, `partially_occluded`, `mostly_occluded`, `illegible` | `illegible` normalmente exige `unknown`. |
| `occlusion_reason` | sombra, nuvem, blur, copa, veículo, estrutura, outro | Registrar o motivo, não esconder a incerteza. |
| `dominance` | `dominant`, `co-dominant`, `not_dominant`, `not_applicable` | Só usar `dominant` com evidência suficiente. |
| `spatial_relation` | `inside_zone`, `overhang`, `adjacent`, `uncertain` | Se a copa está sobre a faixa mas o tronco está fora, preservar `overhang`. |
| `quality_status` | `accepted`, `limited`, `rejected` | `rejected` não alimenta análise nem treinamento. |
| `rationale` | texto curto e controlado | Obrigatório em `unknown`, `mixed` ou conflito. |

Percentual, quando vier a existir, deve guardar método, resolução e referência
espacial. Não é permitido inventar percentual a partir de uma cor de mapa.

## Regras para casos limítrofes

1. **Copa sobre a faixa:** separar a posição da copa da posição do tronco. Uma
   copa visível sobre a zona pode receber `tree`/`overhang`, mas não prova que o
   indivíduo está dentro da faixa nem prova risco ou altura.
2. **Gramínea sob árvore:** se ambos forem relevantes e nenhum dominar com
   confiança, usar `mixed`; se a copa ocultar a camada inferior, usar a classe
   visível e registrar a oclusão, ou `unknown` quando a classe não puder ser
   sustentada.
3. **Arbusto versus árvore:** exigir estrutura ou contexto suficiente. Muda,
   cerca viva e silhueta sem escala permanecem `unknown` quando a distinção não
   for revisável.
4. **Sombra, nuvem e blur:** não usar tonalidade para decidir classe. Se a
   degradação impedir a leitura, `unknown` com `quality_status=limited`.
5. **Pavimento, solo e rebrote:** pavimento limpo pode ser `non_vegetation`;
   solo com rebrote ou vegetação seca ambígua deve ser `unknown` ou a classe
   observável, nunca descarte silencioso.
6. **Conflito entre fontes:** preservar cada observação com sua fonte/data e
   registrar o conflito. Não calcular uma média nem substituir o rótulo por
   maioria sem adjudicação.
7. **Zonas:** avaliar esquerda, direita, canteiro central e áreas especiais
   separadamente. Um rótulo não pode atravessar zonas sem evidência própria.

## Fluxo de revisão proposto

1. Anotador registra classe, atributos, fonte, data, zona e limitação.
2. Segundo anotador revisa uma amostra de calibração e todos os casos de
   `unknown`, `mixed` ou conflito material.
3. Especialista adjudica divergências e aprova exemplos do manual ilustrado.
4. Data owner aprova versão, licença/consentimento, retenção e uso permitido.
5. Só depois do aceite formal uma versão pode ser referenciada por um contrato
   ou dataset; esta proposta não faz essa promoção.

Concordância deve ser publicada por classe, zona e condição de qualidade. Não
fixar meta numérica antes da revisão especializada.

## Usos proibidos nesta proposta

- derivar `N1`/`N2`/`N3` do tipo de cobertura;
- converter NDVI, cor, confiança ou tipo em altura em centímetros;
- treinar modelo com dados `prepared` ou `simulated`;
- usar `tree`, `grass_herbaceous` ou qualquer classe para autorizar roçada;
- apagar uma observação conflitante ou perder sua proveniência;
- chamar a taxonomia de “oficial”, “validada” ou “operacional” antes das duas
  aprovações previstas.

## Critérios para sair de proposta

O status só pode mudar quando houver registro revisável de especialista e data
owner, exemplos aceitos/rejeitados, política de privacidade/licença, versão do
manual de anotação e decisão explícita sobre o contrato. Até lá, consumidores
devem tratar o vocabulário como candidato e manter `unknown` quando houver
dúvida.
