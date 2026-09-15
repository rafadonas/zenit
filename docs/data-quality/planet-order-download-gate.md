# Gate para Order e download Planet — PLANET-004

O catálogo Planet e o filtro `assets:download` foram validados para o segmento
preparado `SP021/195`. O proprietário confirmou o manifesto abaixo para um único
teste acadêmico controlado:

| Campo | Pergunta que precisa de resposta |
| --- | --- |
| `item_ids` | Uma cena com permissão de download, escolhida pela menor nuvem disponível no intervalo validado. |
| `product_bundle`/assets | `analytic_udm2`: `ortho_analytic_4b`, XML de metadados e `ortho_udm2`. |
| AOI recortada | Buffer de 25 m do segmento estimado de 100 m, área calculada de 6.950,55 m². |
| orçamento | No máximo 10.000 m², 100 MiB, uma cena, um bundle e um Order; sem cobrança paga. |
| licença/consentimento | Uso acadêmico do projeto, sem redistribuição pública; retenção aprovada por 30 dias. |
| retenção/destino | Bucket local criptografado `zenit-raw`, prefixo do Order, SHA-256 e linhagem no Postgres. |
| aprovação | Rafael confirmou explicitamente a criação do único Order e o download limitado. |

O worker mantém `eligible_for_operations=false` e
`eligible_for_official_reporting=false`. Links temporários da Planet não são
armazenados como evidência permanente; somente os bytes cifrados, seus checksums,
metadados e eventos de Order são persistidos.
