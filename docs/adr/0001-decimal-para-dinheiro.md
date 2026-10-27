# 0001. `Decimal` e `NUMERIC` para preços, nunca `float`

- **Status:** Aceita
- **Registrada em:** 2026-10-27, sobre uma decisão do início do projeto (Dias 1 e 2)

## Contexto

O projeto compara preços com preços-alvo para decidir se um alerta dispara. O alvo é exatamente igual ao preço em alguns casos de teste, e o alerta precisa disparar nesse limite. Além disso, há moedas que valem frações de centavo (R$ 0,00001234), e o histórico precisa guardar esses valores sem arredondar.

`float` é binário: `0.1 + 0.2 == 0.3` é `False` em Python. Numa comparação de fronteira (preço igual ao alvo), esse erro de representação decide se o alerta dispara ou não.

## Decisão

Preços são `Decimal` do começo ao fim:

- **Entrada:** a resposta da CoinGecko é lida com `json.loads(..., parse_float=Decimal)`, para o número nunca passar por `float`, e é pedida com `precision=full`.
- **Banco:** colunas `NUMERIC(30, 12)`, que guardam até 12 casas decimais.
- **API:** o JSON recebe e devolve preços como texto (`"600000.00"`), para nenhum cliente converter para `float` no meio do caminho.

## Alternativas consideradas

- **`float` com arredondamento na comparação:** exigiria escolher uma tolerância arbitrária, e o erro continuaria no histórico gravado.
- **Inteiros em centavos:** funciona para reais, mas não para moedas abaixo de um centavo. Exigiria uma escala diferente por moeda.

## Consequências

- A comparação no limite é exata e coberta por testes (preço igual ao alvo dispara nas duas direções).
- Toda entrada de número precisa ser convertida explicitamente para `Decimal`. Um `float` que escapar é um bug, e os testes comparam com `Decimal("...")`, não com texto.
- Preços como texto no JSON surpreendem quem consome a API pela primeira vez; isso está documentado no README e no exemplo do Swagger.
