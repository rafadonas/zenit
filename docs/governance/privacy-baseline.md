# Base de política de privacidade

- Versão: `privacy-baseline-0.1`
- Data: 2026-09-15
- Status: **base proposta**; nenhuma decisão está aprovada
- Relacionado: [threat model](../security/incremental-threat-model.md) (`MEDIA-02`, `MAP-01`),
  [protocolo de ground truth](../data-quality/ground-truth-protocol.md),
  [registro de licenças](licence-register.md)

> Este documento **não é uma política aprovada** e não substitui parecer de
> encarregado de dados, jurídico ou da concessionária. Ele reúne o que precisa
> ser decidido antes de qualquer tratamento de dado pessoal real e registra o que
> fica bloqueado enquanto isso não acontece.

## 1. Papéis

| Papel | Quem | Status |
| --- | --- | --- |
| Controlador | provavelmente a concessionária, a confirmar | **a definir** |
| Operador | projeto acadêmico ZENIT | **a confirmar** |
| Encarregado (LGPD art. 41) | não designado | **a definir** |
| Responsável técnico de segurança | não designado | **a definir** |

Enquanto controlador e encarregado não existirem, **nenhum dado pessoal real
pode ser coletado, e o piloto de campo continua bloqueado**.

## 2. Dados pessoais previstos

| # | Dado | Origem | Situação hoje | Risco principal |
| --- | --- | --- | --- | --- |
| P1 | identidade de usuário (e-mail, papel, rodovia) | identidade local do MVP | dados de demonstração | atribuição de decisão a pessoa real |
| P2 | localização e horário do coletor | app de campo | coleta bloqueada | rastreamento de trabalhador |
| P3 | fotos de campo com terceiros (rostos, placas) | app de campo | coleta bloqueada | imagem de pessoa que não consentiu |
| P4 | EXIF das fotos (GPS, dispositivo) | app de campo | sem tratamento aprovado | vazamento indireto de localização |
| P5 | IP e contexto de localização do visitante | carregamento de tiles pelo navegador | tiles vão direto ao provedor | exposição a terceiro sem aviso (`MAP-01`) |
| P6 | registros de acesso e auditoria | API e dashboard | retidos sem prazo definido | retenção indefinida |
| P7 | identificação de anotadores | anotação do dataset | pseudonimização prevista, não aprovada | reidentificação por cruzamento |

## 3. Decisões pendentes

| # | Decisão | Responsável exigido |
| --- | --- | --- |
| D1 | finalidade e base legal de cada tratamento | encarregado + jurídico |
| D2 | prazos de retenção por categoria, incluindo logs e cache | controlador |
| D3 | consentimento e termo dos coletores | encarregado |
| D4 | tratamento de terceiros nas fotos: desfoque antes da anotação | encarregado |
| D5 | remoção de EXIF e guarda do original cifrado | encarregado + segurança |
| D6 | uso de proxy de tiles para não expor IP do visitante ao provedor | controlador + segurança |
| D7 | transferência internacional: provedores fora do Brasil | jurídico |
| D8 | direitos do titular: canal, prazo e procedimento | encarregado |
| D9 | resposta a incidente e comunicação à ANPD | controlador |
| D10 | relatório de impacto (RIPD) do piloto de campo | encarregado |

## 4. Princípios que já valem no repositório

Independem de aprovação e já são praticados:

- **Minimização:** só os campos necessários; nenhuma credencial real de
  produção; nenhum dado pessoal em `data/raw/` versionado.
- **Cifra em repouso** dos ativos e das mídias, com checksum verificável.
- **Segregação:** chave de provedor e segredo só no backend.
- **Auditoria append-only** de decisões, acessos e verificações.
- **Pseudonimização** prevista para coletores e anotadores.
- **Nada de dado real de campo** enquanto os gates estiverem abertos.

## 5. Bloqueios em vigor

| Bloqueio | Origem |
| --- | --- |
| coleta de campo real | `GEO-002`, seção 8 |
| mídia real em pipeline não aprovado | `MEDIA-02` |
| exposição pública do mapa ou proxy de tiles | `MAP-01`, `PLANET-006` |
| uso de dado pessoal para treinamento | `GEO-004` |

## 6. Aprovações

| Decisão | Responsável | Papel | Data | Referência |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

Um item só sai da lista de pendências quando aparece nesta tabela com
responsável, data e referência do documento assinado.
