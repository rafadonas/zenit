# Registro de licenças e usos permitidos

- Versão: `licence-register-0.1`
- Data: 2026-09-15
- Status: **base proposta**; nenhuma linha está aprovada
- Escopo: todas as fontes externas e derivadas usadas pelo ZENIT

> Este documento **não concede licença** e não substitui contrato, termo de uso
> de provedor ou decisão jurídica. Ele organiza o que precisa ser aprovado, por
> quem, e qual uso fica bloqueado enquanto isso não acontecer.

## Como usar

1. Cada fonte tem uma linha com o uso pretendido e o uso proibido.
2. Enquanto o status não for `approved`, **o uso correspondente fica bloqueado**,
   mesmo que exista implementação pronta.
3. Aprovar é registrar responsável, data e referência do documento assinado na
   tabela de aprovações, e mudar o status da linha.
4. Nenhuma linha aqui autoriza, por si, treinamento de modelo, relatório oficial
   ou trabalho de campo. Esses usos têm gates próprios.

## Fontes

| # | Fonte | O que o projeto guarda hoje | Uso pretendido | Uso proibido até aprovação | Retenção | Status |
| --- | --- | --- | --- | --- | --- | --- |
| L1 | Planet, catálogo (`PLANET-001`/`003`) | metadados normalizados de cena e checksum | descoberta e persistência limitadas | redistribuição dos metadados e uso comercial | a definir | `pending` |
| L2 | Planet, ativos de Order (`PLANET-004`) | 3 ativos cifrados de uma cena | piloto acadêmico, 30 dias ([ADR-0078](../decisions/ADR-0078-planet-order-download-gate.md)) | treinamento, relatório oficial, redistribuição | 30 dias, a confirmar | `pending` |
| L3 | Planet, tiles e basemap (`PLANET-006`) | nada | proxy autenticado com cache local | qualquer exposição ao navegador antes da licença | a definir | `pending` |
| L4 | Copernicus Sentinel-2 | estatísticas e um recorte NDVI | evidência acadêmica com atribuição | omissão de atribuição; uso oficial | a definir | `pending` |
| L5 | INPE BDC | metadados de catálogo | descoberta comparativa | download em massa | a definir | `pending` |
| L6 | OpenStreetMap | nada localmente; tiles carregados pelo navegador | mapa-base de baixo volume, com atribuição | cache, proxy ou prefetch sem autorização da comunidade | não se aplica | `pending` |
| L7 | Arquivos fornecidos pela Motiva (KMZ e planilhas) | originais imutáveis em `data/raw/` | leitura, normalização e demonstração acadêmica | redistribuição, publicação e uso como rótulo | enquanto durar o projeto, a confirmar | `pending` |
| L8 | Fotos, medições e GPS de campo (`GEO-002`) | nada; coleta bloqueada | ground truth acadêmico | qualquer coleta antes dos gates do protocolo | a definir | `pending` |
| L9 | Artefatos derivados (prévia NDVI, camada do dashboard) | arquivos versionados com checksum | demonstração acadêmica | apresentação como produto oficial | acompanha a fonte | `pending` |
| L10 | Dataset de cobertura (`GEO-004`) | manifesto `blocked`, sem rótulos | treinamento acadêmico futuro | qualquer treinamento antes da aprovação | a definir | `pending` |

## Regras que independem de aprovação

- Arquivos em `data/raw/` nunca são alterados.
- Dados `prepared`, `estimated`, `simulated` ou `inconclusive` não viram ground
  truth nem entram em treinamento.
- Chave de provedor nunca chega ao navegador ou ao aplicativo.
- Toda cópia derivada preserva checksum e linhagem
  ([`../data-quality/asset-checksums-and-lineage.md`](../data-quality/asset-checksums-and-lineage.md)).

## Aprovações

| Linha | Decisão | Responsável | Papel | Data | Referência do documento |
| --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | — |

Responsáveis esperados: data owner do projeto para uso acadêmico, e jurídico ou
a concessionária para qualquer uso que ultrapasse a demonstração.
