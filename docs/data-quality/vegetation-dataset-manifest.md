# Manifesto do dataset de cobertura vegetal — GEO-004

Manifesto versionado: [`vegetation-dataset-2026-09-15.json`](../../data/manifests/vegetation-dataset-2026-09-15.json)

Fonte de origem: [`source-data-homologation.md`](source-data-homologation.md)

Verificador: [`verify_dataset_manifest.py`](../../scripts/verify_dataset_manifest.py)

## Estado atual

`zenit-vegetation-cover:v0.1-draft` está `blocked`. O manifesto fornece a
estrutura reproduzível e o gate de segurança, mas contém zero rótulos de
cobertura vegetal e nenhuma unidade de treino. As fontes registradas são
`prepared`/`needs_validation`; os checksums apontam para os bytes imutáveis em
`data/raw/`.

As classes mantidas no espaço de rótulos são `unknown`, `grass_herbaceous`,
`shrub`, `tree`, `mixed` e `non_vegetation`. N1/N2/N3 e categorias de equipamento
não são convertidas em rótulos de cobertura.

## Gate fail-closed

O verificador rejeita manifestos que tentem abrir treinamento ou promoção antes
de todos estes requisitos:

- licença e consentimento documentados por fonte;
- rótulos de cobertura observáveis e guia de anotação versionado;
- duas anotações independentes e adjudicação registrada;
- holdout espacial e temporal com checagem de vazamento;
- checksums, linhagem, exclusões e limitações preservados.

Mesmo quando esses gates forem preenchidos, treinamento e relatório oficial
precisarão de uma revisão explícita. Dados `demo`, `simulated`, `prepared` ou
sem validação não entram no dataset de treinamento deste ticket.

## Critérios de promoção

Uma versão posterior só pode sair de `blocked` após anexar as unidades rotuladas,
contagens por classe/zona/fonte, os grupos de split e a evidência de revisão.
O verificador continua impedindo `status=validated` enquanto a decisão de
promoção não for registrada; nenhum modelo é criado por este incremento.
