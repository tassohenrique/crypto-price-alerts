# Registros de decisão de arquitetura (ADRs)

Cada arquivo desta pasta registra uma decisão importante do projeto: o problema, as alternativas consideradas, o que foi escolhido e o preço dessa escolha. A ideia é que quem chegar ao código entenda não só *o que* foi feito, mas *por quê*.

As quatro primeiras foram registradas depois de implementadas, a partir do código, dos commits e do log de desenvolvimento.

| Nº | Decisão | Status |
|---|---|---|
| [0001](0001-decimal-para-dinheiro.md) | `Decimal` e `NUMERIC` para preços, nunca `float` | Aceita |
| [0002](0002-aviso-pendente-outbox.md) | Aviso pendente no banco em vez de envio imediato ao Telegram | Aceita |
| [0003](0003-agendador-externo.md) | Agendador externo chamando a API em vez de worker sempre ligado | Aceita |
| [0004](0004-trava-de-ciclo-no-postgres.md) | Trava no PostgreSQL para nunca rodar dois ciclos juntos | Aceita |

## Modelo

Para uma decisão nova, copie o bloco abaixo num arquivo `NNNN-titulo-curto.md`:

```markdown
# NNNN. Título da decisão

- **Status:** Proposta | Aceita | Substituída por NNNN
- **Registrada em:** AAAA-MM-DD

## Contexto
O problema e as restrições que forçam uma escolha.

## Decisão
O que foi escolhido, em uma ou duas frases.

## Alternativas consideradas
Cada opção descartada e o motivo.

## Consequências
O que fica melhor, o que fica pior e o que passa a ser obrigatório.
```
