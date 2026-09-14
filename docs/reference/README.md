# PDF source companions

This directory provides searchable Markdown companions for the six ZENIT project
documents currently supplied as PDFs. It does not replace immutable source files,
contractual originals, or their legal context.

| PDF source | Pages | SHA-256 | Markdown companion | Treatment |
| --- | ---: | --- | --- | --- |
| `ZENIT_Manual_Mestre_para_Codex.pdf` v1.0 | 44 | `a8d2613c9c57dad5703522ceec871d15b6ec18a5fe16c8354ff31fc5e798c5e2` | [Maintained master manual](../manual/README.md) | Updated living edition, split into chapters. |
| `ZENIT_Design_System_Motiva.pdf` v1.0 | 28 | `cb0c6729d95b0cb2e7379664de070c43707787a10597ea3916310bd2ddd112cf` | [Design-system source companion](design-system-source.md) | Searchable source map plus current governance. |
| `Inovação Aberta_FIAP_04.26.pdf` | 15 | `7bbd8a74c63f89b1e42bec838f2d32fd206c9e39458ddfc35af916631c198958` | [FIAP/Motiva challenge brief](fiap-motiva-challenge-brief.md) | Structured source summary. |
| `ZENIT_Guia_Tecnico_APIs_Sentinel_CBers.pdf` | 38 | `61913c6163d67e9a0e70701440b22ac0b118a2c2cd2d2ed5b1ed75aa18cf7af9` | [Sentinel and CBERS guide](sentinel-cbers-api-guide.md) | Dated guide reconciled with current adapters. |
| ANTT `Programa de Exploração da Rodovia - PER - Volume I - Pós Esclarecimentos.pdf` | 129 | `6b41d221b92c6d685c1a67e5292d25770ec8a2073782ad19efb224bb8a445896` | [ANTT PER reference](antt-per-volume-i.md) | ZENIT-relevant structured extract. |
| ARTESP `LOTE 2 - Anexo 06 - Serviços de Conservação do Sistema Rodoviário.pdf` | 116 | `94f186f5608cfe68e122d729830d6f9f2da8db2f39f9d8ba4481bf65344d62c1` | [ARTESP conservation reference](artesp-conservation-annex.md) | ZENIT-relevant structured extract. |

## Interpretation rules

- Page references point to the PDF page number, not a printed internal page when
  those differ.
- Summaries paraphrase the source; consult the original before contractual or
  legal interpretation.
- The regulatory PDFs apply to their own concession/instrument context. Their
  requirements are not automatically cumulative or universally applicable.
- Current implementation claims belong in source code, ADRs, contracts, and the
  maintained manual, not in a historical source companion.
- Files under `data/raw/` remain immutable and ignored by Git. Do not replace them
  with Markdown or modify them in place.
- A source date, threshold, example AOI, KPI, or API URL is not automatically a
  current operational value.
