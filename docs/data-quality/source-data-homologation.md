# Homologação acadêmica dos dados de origem — GOV-003

Review identifier: `zenit-source-review-2026-09-15`

Data owner: Rafael (project owner)

Decision: [`ADR-0080`](../decisions/ADR-0080-source-data-academic-homologation.md)

Manifest: [`source-homologation-2026-09-15.json`](../../data/manifests/source-homologation-2026-09-15.json)

## Resultado

O pacote foi revisado e aceito para o protótipo acadêmico reprodutível. Isso
não é homologação operacional: eixo, zonas, atributos inferidos e relação entre
datas continuam `estimated`/`prepared`/`needs_validation`. Nenhuma derivação
deste pacote é elegível para operação, relatório oficial ou treinamento de
modelo.

Os bytes originais continuam protegidos em `data/raw/`. O inventário e os
checksums de referência estão em
[`initial-audit.md`](initial-audit.md) e no manifesto inicial
[`initial-source-audit.json`](../../data/manifests/initial-source-audit.json).

## Decisões de origem

| Fonte/entidade | Observação confirmada | Estado controlado |
| --- | --- | --- |
| `Marco km_rodoanel 2.kmz` | 30 pontos `SP021`, km 0–29; conteúdo `doc.kml`; coordenadas WGS 84 | eixo candidato `estimated`, `needs_validation` |
| Eixo/segmentos derivados | distância/área métrica somente em `EPSG:31983`; segmento de 100 m | preparado, inelegível |
| Zonas ZENIT | `left`, `right`, `median`, `special` avaliadas separadamente | geometrias oficiais ausentes; `needs_validation` |
| `classificacao_rocada.kmz` | 642 polígonos; extensão indica KMZ, conteúdo é KML; nomes são categorias de equipamento | geometrias preservadas; mapeamento de campos inferido |
| Atributos do KML | `classe` parece latitude, `KM` longitude e `Latitude` área | `inference_status=needs_validation` |
| Planilhas `RA-RET-ROÇ-LIMP-*` | 480 observações por versão; serial 45744 = 2025-03-28 | versões documentais, não série temporal |

### Regras de uso

- A análise mantém uma unidade de 100 m e não mistura as quatro zonas.
- A data `2025-03-28` é uma referência interna dos documentos, não uma medição
  atual. As datas nos nomes dos arquivos identificam versões.
- Categorias históricas N1/N2/N3 permanecem independentes de tipo de cobertura,
  NDVI, confiança e geometria inferida.
- A taxonomia vegetal do protótipo pode ser sugerida por IA, mas qualquer
  resultado é estimado, versionado e sujeito a revisão humana; não autoriza
  roçada silenciosamente.

## Exceções registradas

1. O marcador não possui km 29+300 e tem ordem de origem não sequencial; km 2 e
   km 3 estão invertidos, e há grandes gaps entre alguns marcadores.
2. Treze polígonos possuem auto-interseção. A topologia inválida é preservada
   em staging com aviso estruturado; nenhuma geometria bruta foi reparada.
3. O arquivo de polígonos usa extensão `.kmz` para conteúdo KML sem compressão.
4. O mapeamento de atributos do polígono é inferido e não foi promovido; alguns
   valores de quilômetro não aparecem nas descrições de categoria.
5. Não foi fornecido eixo oficial, limite oficial da faixa ou data de vistoria
   que permita declarar condição atual.

## Critérios para nova versão

Antes de promover dados, uma revisão posterior deve anexar a fonte oficial ou
correção confirmada, manter os checksums, documentar SRID e stationing, resolver
as zonas e o mapeamento dos campos, definir a relação das datas e registrar
responsável, licença, retenção e evidência de validação. Até lá, consumidores
devem mostrar o estado e a limitação junto com qualquer mapa, recomendação ou
exportação.
