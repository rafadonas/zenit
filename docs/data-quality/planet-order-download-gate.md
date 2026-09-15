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

## Execução do piloto

Em 2026-09-15, o worker reutilizou o único Order aprovado:

- Order Planet: `f830d7d4-b4fd-4b58-a0a8-d54898096d35` (`success`);
- cena selecionada: `20260805_135356_12_253c`, adquirida em 2026-08-05,
  com nuvem normalizada em 0%;
- AOI: 6.950,55 m²; catálogo limitado a 9 resultados em uma página;
- download: 27.266 bytes, três assets, sem nova criação de Order;
- checksums SHA-256:
  - `ortho_analytic_4b` — 12.094 bytes —
    `2a902336f8a9b4c4c65df3f58e35cf24d5f8af0b7a7e93b5beb60434f82b1df1`;
  - `ortho_analytic_4b_xml` — 9.996 bytes —
    `e7d3ab4e4a3598ebd27218b365b0d9c14878295d3513f3234071a9fc4e26c8a7`;
  - `ortho_udm2` — 5.176 bytes —
    `2f8980410144112413e6d21278fb2d0a01baa03bf6d2b27bf6fe85594d36cef2`.

Os três objetos estão no prefixo privado `s3://zenit-raw/planet/orders/`,
cifrados com AES-GCM e versionamento MinIO. A cena ficou `cache_status=cached`,
mas permanece `eligible_for_operations=false` e
`eligible_for_official_reporting=false`. A API de Orders não forneceu uma
estimativa monetária no fluxo; o limite de custo zero foi mantido como regra
operacional e deve ser confirmado no painel/contrato da conta antes de ampliar o
uso.
