# 0003. Agendador externo chamando a API em vez de worker sempre ligado

- **Status:** Aceita
- **Registrada em:** 2026-10-27, sobre decisões do Dia 8 (deploy, PRs #2 e #4)

## Contexto

Localmente, o worker é um processo em loop: roda um ciclo, espera o intervalo e repete. Em produção, o projeto precisa rodar em planos gratuitos, e isso muda as opções:

- No Render, *background workers* não têm instância gratuita. O mais barato é pago mensalmente.
- O serviço web gratuito do Render hiberna depois de um tempo sem requisições.
- O PostgreSQL gratuito do Neon suspende quando fica sem uso e tem limite mensal de computação.

A pergunta era quem dispara cada ciclo.

## Decisão

Um agendador externo gratuito, o [cron-job.org](https://cron-job.org), chama `POST /internal/run-cycle` na API a cada 15 minutos. A rota roda um único ciclo e responde com o resumo (`prices_saved`, `alerts_triggered`, ...).

- A rota exige o cabeçalho `X-Cron-Secret`, um segredo separado da `API_KEY`: se ele vazar, só dá para disparar ciclos, não para gerenciar alertas. Sem `CRON_SECRET` configurado, a rota responde `404`.
- A rota fica fora do `/docs`, porque é chamada por uma máquina, não por pessoas.
- As chamadas também mantêm a API acordada no Render.
- O intervalo de 15 minutos deixa o Neon dormir entre os ciclos, dentro do limite gratuito.
- O mesmo ciclo continua disponível como processo (`python -m app.worker --once`) e como loop (`python -m app.worker`), para rodar localmente.

## Alternativas consideradas

- **Background worker pago no Render:** a solução mais simples, descartada só pelo custo.
- **Agendamento do GitHub Actions (`schedule`):** foi a primeira implementação (PR #2). Num teste de cerca de 20 horas, rodou só 4 das cerca de 80 execuções previstas, com intervalos de 3 a 6 horas. O GitHub trata o agendamento como "melhor esforço", sem garantia de horário. O workflow `worker.yml` ficou só para rodar um ciclo manualmente.
- **Cron Job do Render:** horário confiável, mas também pago (cobrado por minuto, com mínimo mensal).

## Consequências

- Custo zero, com horário confiável.
- O ciclo passa a rodar dentro de uma requisição HTTP, então precisa terminar rápido. Com uma única chamada à CoinGecko por ciclo, ele leva poucos segundos.
- Se o cron-job.org parar, nenhum ciclo roda e nada avisa por conta própria. Por isso existe `GET /health/worker`, que responde `503` quando o preço mais recente passa de 30 minutos (o dobro do intervalo, para tolerar um ciclo perdido). Um monitor externo, como o UptimeRobot, apontado para essa rota, avisa por e-mail.
- Duas chamadas podem chegar ao mesmo tempo (um atraso do agendador, uma chamada manual). Isso levou à [ADR 0004](0004-trava-de-ciclo-no-postgres.md).
