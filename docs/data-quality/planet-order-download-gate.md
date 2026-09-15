# Gate para Order e download Planet — PLANET-004

O catálogo Planet e o filtro `assets:download` já foram validados para a AOI de
desenvolvimento. Antes de criar um Order, preencher todos os campos abaixo no
manifesto revisado:

| Campo | Pergunta que precisa de resposta |
| --- | --- |
| `item_ids` | Quais das 13 cenas serão usadas? Uma cena piloto ou mais? |
| `product_bundle`/assets | Qual bundle e quais assets serão baixados (`visual`, `analytic_sr`, `analytic_udm2` ou outro disponível para a conta)? |
| AOI recortada | O recorte continua a AOI documentada ou será um trecho menor de 100 m/1 km? |
| orçamento | Qual limite máximo de área, bytes/custo e tentativas? |
| licença/consentimento | O uso acadêmico, armazenamento e treinamento estão cobertos pelos termos da conta? |
| retenção/destino | Onde guardar, por quanto tempo, com qual criptografia e checksum? |
| aprovação | Quem confirma a criação do Order e aceita consumo de cota? |

Sem respostas, o estado é `blocked`. Não criar Order só porque a chave funciona;
não usar links temporários como armazenamento permanente; não expor URLs,
tokens ou bytes no dashboard/mobile. A execução futura deve ser uma operação
única, limitada, auditável e reversível, mantendo `eligible_for_operations=false`
até os gates do projeto.
