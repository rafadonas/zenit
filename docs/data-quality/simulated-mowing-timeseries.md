# DATA-DEMO-001 — série temporal simulada de crescimento e corte

## Objetivo

Este dataset demonstra como o ZENIT pode organizar uma série temporal de
vegetação para ingestão, gráficos e ensaio do pipeline. Ele cobre o trecho
preparado `SP021/195` durante 30 dias, sempre separando `left`, `right`, `median`
e `special`.

Todos os valores são **mockados**. Altura, crescimento, chuva e eventos de corte
foram gerados por algoritmo e não representam medição de campo, imagem Planet,
condição atual ou serviço executado.

## Conteúdo

- `data/simulated/sp021-195/mowing-timeseries.csv`: 120 registros, um por
  dia e zona;
- `data/simulated/sp021-195/mowing-timeseries.manifest.json`: parâmetros,
  checksum do CSV, finalidade, elegibilidade e limitações;
- `scripts/generate_simulated_mowing_timeseries.py`: gerador determinístico.

O cenário preserva o limiar geral de 30 cm e o limiar de 10 cm para a zona
`special`. Os eventos de corte são entradas roteirizadas da simulação, nunca uma
recomendação ou autorização automática.

## Reproduzir

```bash
python scripts/generate_simulated_mowing_timeseries.py
```

A mesma seed e os mesmos parâmetros produzem os mesmos registros e checksum.
Para outro ensaio local:

```bash
python scripts/generate_simulated_mowing_timeseries.py \
  --start-date 2026-08-01 \
  --days 30 \
  --road-code SP021 \
  --segment-index 195 \
  --seed 20260915 \
  --output-directory data/simulated/sp021-195
```

O gerador recusa destinos sob `data/raw/`.

## Como apresentar

Formulação recomendada:

> Esta série foi criada artificialmente para demonstrar a organização temporal
> do produto. Ela mostra o formato esperado de crescimento e intervenções, mas
> não treinou nem validou o modelo e não representa uma rodovia real.

Não chamar a série de ground truth, previsão, observação ou resultado de IA. Ela
pode ensaiar leitura de CSV, transformações, gráficos e splits do pipeline, mas
deve permanecer separada do manifesto GEO-004.

## Gates preservados

Cada linha e o manifesto mantêm:

- `data_status=simulated`;
- `eligible_for_model_training=false`;
- `eligible_for_official_reporting=false`;
- `eligible_for_operations=false`; e
- `authorizes_mowing=false`.

AI-001 permanece bloqueado até existir dataset real, licenciado/consentido,
duplamente anotado, adjudicado e dividido com holdout espacial e temporal.
