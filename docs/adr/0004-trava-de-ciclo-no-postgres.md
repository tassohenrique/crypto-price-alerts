# 0004. Trava no PostgreSQL para nunca rodar dois ciclos juntos

- **Status:** Aceita
- **Registrada em:** 2026-10-27, sobre uma decisão do Dia 8 (PR #4)

## Contexto

Com o agendador externo ([ADR 0003](0003-agendador-externo.md)), o ciclo pode ser disparado de vários lugares: a rota chamada pelo cron-job.org, uma chamada manual, o workflow manual do GitHub Actions ou o worker em loop. Se dois ciclos rodarem ao mesmo tempo, os dois podem ler o mesmo aviso pendente e enviá-lo, e a mensagem chega duplicada.

Esses ciclos rodam em processos diferentes, às vezes em máquinas diferentes. Uma trava em memória (`threading.Lock`) não serve, porque cada processo teria a sua. O único ponto em comum entre todos eles é o banco.

## Decisão

Antes de começar, o ciclo pede uma *advisory lock* ao PostgreSQL com `pg_try_advisory_lock`, usando um número fixo (`CYCLE_LOCK_ID`). Se outro ciclo já tem a trava, o pedido volta `false` na hora, sem esperar:

- Na rota `POST /internal/run-cycle`, a resposta é `409` e nada é feito.
- No worker, o ciclo é pulado e registrado no log. Pular não conta como erro.

Detalhes que importam (`cycle_lock` em `app/worker.py`):

- **Conexão própria:** a trava pertence à conexão, e a `Session` do SQLAlchemy devolve a conexão ao pool a cada commit. A trava é pedida e liberada numa conexão separada, que fica aberta durante todo o ciclo.
- **Transação fechada logo após pegar a trava:** a trava é da sessão do Postgres, não da transação. Fechar a transação evita que a conexão fique "idle in transaction" pelo ciclo inteiro.
- **Liberação garantida:** `pg_advisory_unlock` roda num `finally`. Se o processo morrer, o Postgres libera a trava sozinho quando a conexão cai.

## Alternativas consideradas

- **`SELECT ... FOR UPDATE SKIP LOCKED` nos alertas:** protegeria só os avisos, não a gravação de preços. Dois ciclos ainda gravariam o histórico em dobro.
- **Coluna "ciclo em andamento" numa tabela:** se o processo morresse no meio, a coluna ficaria marcada para sempre e exigiria um tempo de expiração. A advisory lock é liberada sozinha quando a conexão cai.
- **`pg_advisory_lock` (que espera):** o segundo ciclo ficaria parado esperando e depois rodaria logo em seguida, sem utilidade. Pular é melhor.

## Consequências

- Nenhum aviso sai em dobro por causa de ciclos simultâneos, em qualquer combinação de processos.
- O ciclo passa a usar duas conexões com o banco. No limite de conexões do plano gratuito do Neon, isso não pesa.
- A garantia depende do PostgreSQL. Trocar de banco exigiria outro mecanismo de trava.
