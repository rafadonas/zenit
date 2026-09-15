# DATA-DEMO-002 — ensaio de feature snapshots simulados

## Objetivo

Este ticket transforma a série temporal mockada de `DATA-DEMO-001` em snapshots
diários e reproduzíveis para demonstrar o contrato de features proposto para o
ZENIT. Nenhum modelo é treinado, validado, calibrado ou promovido.

Os artefatos continuam **simulados** e servem somente para ensaiar o pipeline e
explicar a arquitetura na apresentação. Eles não são evidência de campo,
previsão de IA, ground truth nem resultado operacional.

## Artefatos

- `data/simulated/sp021-195/feature-snapshots.csv`: 664 snapshots, cobrindo 166
  datas após um aquecimento de 14 dias e mantendo as quatro zonas separadas;
- `data/simulated/sp021-195/feature-snapshots.manifest.json`: versão da definição,
  checksum, origem, partições de ensaio, elegibilidade e limitações;
- `scripts/build_simulated_feature_snapshots.py`: transformação determinística.

Cada snapshot registra os IDs das 15 observações necessárias para cobrir o dia
corrente e o `lag` de 14 dias, hash da janela de entrada, valores atuais e
defasados, chuva e crescimento acumulados, dias desde o corte roteirizado,
classe histórica N1/N2/N3 e estado frente ao limiar. As janelas usam somente o
dia do snapshot e o passado, evitando vazamento do futuro.

## Divisão temporal de ensaio

As datas são divididas em 70% `development_rehearsal`, 15%
`validation_rehearsal` e 15% `holdout_rehearsal`. Os nomes deixam claro que a
separação demonstra a mecânica, mas não autoriza treino. Como o cenário contém
apenas um trecho simulado, não existe holdout espacial válido.

## Reproduzir

```bash
python scripts/build_simulated_feature_snapshots.py
```

O processo verifica o checksum e os gates do manifesto de origem antes de ler
os dados e recusa destinos sob `data/raw/`.

## Como apresentar

> Estes snapshots foram derivados de seis meses de dados artificiais para
> demonstrar transformações temporais e rastreabilidade. Nenhum modelo foi
> treinado com eles e os resultados não representam uma rodovia real.

Não chamar as partições de treino oficial, os estados de previsão ou as classes
de classificação do modelo. N1/N2/N3 são apenas a aplicação determinística da
taxonomia histórica às alturas simuladas.

## Gates preservados

Todos os registros e o manifesto mantêm `data_status=simulated`,
`eligible_for_model_training=false`, `eligible_for_official_reporting=false`,
`eligible_for_operations=false`, `authorizes_mowing=false` e
`model_fitted=false`. AI-001 permanece bloqueado até existir base real,
licenciada/consentida, adjudicada e apta a holdouts espacial e temporal.
