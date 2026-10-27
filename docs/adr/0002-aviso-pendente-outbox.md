# 0002. Aviso pendente no banco em vez de envio imediato ao Telegram

- **Status:** Aceita
- **Registrada em:** 2026-10-27, sobre uma decisão do Dia 4 (worker)

## Contexto

Quando o preço cruza o alvo, duas coisas precisam acontecer: marcar o alerta como disparado no banco e enviar a mensagem no Telegram. O banco e o Telegram não cabem numa mesma transação. Sempre existe uma janela entre os dois, e o processo pode cair nela, ou o Telegram pode estar fora do ar.

Qualquer ordem tem um lado ruim:

- **Envia e depois grava:** se o commit falhar depois do envio, o alerta continua ativo e a mensagem sai de novo no próximo ciclo (aviso duplicado).
- **Grava e depois envia, sem mais nada:** se o envio falhar depois do commit, o alerta está marcado como disparado e a mensagem nunca sai (aviso perdido).

Para quem configurou um alerta, perder o aviso é pior do que recebê-lo duas vezes.

## Decisão

Disparar e avisar viram duas etapas separadas, ligadas por uma coluna no banco: uma versão simplificada do padrão *Transactional Outbox*.

1. O ciclo grava os preços e marca os alertas atingidos (`triggered_at` e `triggered_price`) numa única transação, e faz o commit.
2. Em seguida, envia todo alerta com `triggered_at` preenchido e `notified_at` vazio (`AlertRepository.list_pending_notifications`). Cada envio bem-sucedido preenche `notified_at` e tem o seu próprio commit.
3. Se o Telegram falhar, o aviso continua pendente e é tentado de novo no ciclo seguinte, mesmo que a CoinGecko esteja fora do ar naquele ciclo.

## Alternativas consideradas

- **Fila externa (Redis, RabbitMQ):** resolve o mesmo problema, mas acrescenta um serviço para manter, sem ganho real para um único usuário e poucos avisos por dia.
- **Enviar dentro da transação e fazer rollback se o envio falhar:** a conexão com o banco ficaria aberta durante a chamada de rede, e um envio que chegou ao Telegram mas teve a resposta perdida seria repetido do mesmo jeito.

## Consequências

- Nenhum aviso se perde: o estado fica no banco e sobrevive a quedas e reinícios do processo.
- A entrega é "pelo menos uma vez". Se o processo cair entre o envio e o commit do `notified_at`, aquele aviso sai de novo. Com um commit por aviso, essa janela fica limitada a uma única mensagem.
- Rearmar um alerta exige que o aviso anterior já tenha sido enviado; senão, o rearme apagaria um aviso pendente (a API responde `409`).
