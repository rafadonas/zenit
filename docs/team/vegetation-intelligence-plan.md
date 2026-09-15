# Plano de inteligência vegetal e imagens

## Resultado desejado

Distinguir gramínea/herbácea, arbusto, árvore, mistura e não vegetação; estimar
condição/altura somente quando a evidência permitir; manter incerteza, origem e
revisão humana até a decisão de campo.

O objetivo não é “uma imagem colorida”. É uma evidência reproduzível que permita
responder: **o que foi observado, quando, por qual sensor/método, com qual qualidade
e o que ainda precisa ser inspecionado?**

## Limite científico e operacional

- NDVI indica resposta espectral associada à vegetação, não altura em centímetros.
- Uma imagem óptica pode confundir sombra, solo exposto, vegetação seca, copa e
  gramínea dependendo de resolução, estação e ângulo.
- Copa de árvore vista de cima pode ocultar gramínea e invadir visualmente a faixa
  sem que o tronco esteja nela.
- Altura real normalmente exige ground truth e sensor/método adequado; não deve ser
  deduzida por regra estética.
- Baixa qualidade/confiança retorna `unknown` ou recomendação de inspeção.
- Uma previsão nunca autoriza roçada e não substitui revisão humana.

## Taxonomia candidata

Precisa de validação por especialista antes de virar contrato:

| Classe | Definição operacional candidata | Casos limítrofes |
| --- | --- | --- |
| `unknown` | evidência insuficiente/conflitante | sombra, blur, nuvem, oclusão |
| `grass_herbaceous` | cobertura baixa sem estrutura lenhosa dominante visível | gramínea alta, forração |
| `shrub` | vegetação lenhosa de porte arbustivo | muda, cerca viva, mistura |
| `tree` | copa/tronco de indivíduo arbóreo ou dossel dominante | copa fora da faixa, palmeira |
| `mixed` | mais de um tipo relevante sem dominância aceitável | árvore sobre gramínea |
| `non_vegetation` | pavimento, solo, estrutura ou água | solo com rebrote mínimo |

Além da classe, registrar cobertura percentual/faixa, visibilidade, oclusão,
qualidade e relação espacial com left/right/median/special. Não derive N1/N2/N3 do
tipo de cobertura.

## Fontes complementares

| Fonte | Serve para | Não prova sozinha |
| --- | --- | --- |
| satélite multiespectral | vigor, cobertura ampla, mudança temporal | espécie/tipo fino e altura cm |
| ortofoto/drone aprovado | textura/copa e contexto de alta resolução | altura sem método 3D/escala |
| foto de campo com escala | tipo e altura local revisáveis | cobertura contínua do segmento |
| medição de campo | ground truth pontual de altura | condição de toda a zona |
| LiDAR/estéreo | estrutura/altura quando calibrado | classe botânica sem evidência adicional |
| histórico de serviço | contexto temporal | vegetação atual |

Combinar fontes exige alinhamento temporal, espacial e de versão. Divergência é um
dado a revisar, não algo a esconder por média.

## Protocolo de aquisição e anotação

O protocolo de domínio está em
[`../data-quality/ground-truth-protocol-proposal.md`](../data-quality/ground-truth-protocol-proposal.md),
com a especificação calculável em
[`../data-quality/ground-truth-protocol.md`](../data-quality/ground-truth-protocol.md)
(`GEO-002`, status `proposed`). Eles definem amostragem estratificada por rodovia,
zona, classe histórica e estação; instrumentos e definição única de altura;
metadados obrigatórios de foto, escala, altura e GPS; dupla anotação,
adjudicação e medição de concordância; aprovações de licença, consentimento,
privacidade e retenção; e exclusão de dados demo/simulados.

Nenhuma coleta real começa antes dos gates desse protocolo.

## Pipeline por maturidade

### Estágio 0 — regra/manual, sem modelo

Adicionar taxonomia e rótulo manual revisado permite testar UX, contrato e
qualidade. É preferível a um modelo não validado.

### Estágio 1 — baseline offline

Começar com baseline simples e interpretável usando atributos disponíveis. Em
seguida comparar uma abordagem de classificação por patch e uma de segmentação.
A escolha de biblioteca, pesos, licença, GPU e serviço exige aprovação.

Saída apenas em artefato de avaliação, nunca na decisão operacional.

### Estágio 2 — fusão e temporalidade

Combinar evidência de campo, óptica e histórico somente se resoluções e datas forem
compatíveis. Modelar qualidade por fonte e permitir “inconclusivo”.

### Estágio 3 — shadow mode

Executar previsões versionadas ao lado da revisão humana, invisíveis para
autorização. Medir discordâncias, grupos/locais de erro, drift e latência.

### Estágio 4 — assistência revisada

Somente após gate formal, mostrar sugestão + evidência + limitação ao revisor.
A revisão humana continua obrigatória e pode rejeitar/corrigir.

## Métricas mínimas

- macro-F1 e IoU por classe;
- precision/recall por classe, com atenção a falsos negativos relevantes;
- matriz de confusão incluindo `unknown`;
- calibração/coverage de abstention; “confidence” não é probabilidade de altura;
- resultado por rodovia, zona, sensor, estação e condição de qualidade;
- avaliação em holdout espacial e temporal;
- para altura, MAE/RMSE em cm e distribuição de erro por faixa/zona;
- taxa de envio para inspeção e taxa de correção humana;
- latência/custo apenas depois de validade técnica.

Não fixe um alvo numérico oficial sem especialista/data owner. Registre baseline e
critério aprovado no model card.

## Manifesto de dataset

Cada versão deve conter:

- ID/versão/data de criação;
- fontes, licença/consentimento e responsável;
- checksums e localização fora do Git para bytes grandes;
- SRID, cobertura espacial e temporal;
- taxonomia/guia de anotação;
- critérios de inclusão/exclusão;
- contagens por classe/zona/fonte;
- método de split e prevenção de vazamento;
- transformações com versões;
- limitações e usos proibidos;
- confirmação explícita de que demo/simulado não entrou em treinamento.

## Contrato de inferência candidato

Não implementar antes de ADR e revisão:

```json
{
  "cover_type": "grass_herbaceous",
  "cover_type_method": "human_reviewed|model_estimated",
  "data_status": "real|estimated|inconclusive",
  "source_observation_id": "...",
  "observed_at": "...",
  "valid_until": null,
  "quality_status": "accepted|limited|rejected",
  "confidence_band": "high|medium|low|not_applicable",
  "taxonomy_version": "...",
  "model_version": null,
  "review_status": "pending|accepted|corrected|rejected",
  "limitations": []
}
```

Guardar valor bruto de score internamente pode ser útil; a interface usa faixa e
explicação calibradas. Sempre preservar a observação fonte e a correção humana.

## Organização do futuro worker

`services/ai-worker` deve nascer depois do contrato/dataset, com fronteiras:

```text
datasets/manifest reader (sem bytes versionados no Git)
features/preprocessing versionado
training reproduzível
evaluation e reports
inference adapter
model registry metadata
monitoring/drift
```

Treino, avaliação e inferência não devem compartilhar estado implícito. Modelos
promovidos são imutáveis; rollback seleciona versão anterior, não sobrescreve peso.

## Gates antes de qualquer integração

- taxonomia e ground truth aprovados;
- licença, privacidade e retenção;
- dataset sem dados demo/simulados;
- baseline reproduzível e revisado;
- erros críticos inspecionados;
- model card, versão e rollback;
- contrato API + migração + autorização;
- interface identifica estimativa e limitações;
- baixa confiança gera inspeção;
- nenhum caminho autoriza roçada automaticamente.
