# Crypto Price Alerts

[![CI](https://github.com/tassohenrique/crypto-price-alerts/actions/workflows/ci.yml/badge.svg)](https://github.com/tassohenrique/crypto-price-alerts/actions/workflows/ci.yml)
![Cobertura](https://img.shields.io/badge/cobertura-95%25-brightgreen)

![Python](https://img.shields.io/badge/python-3.14-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-336791)

Monitor de preços de criptomoedas com alertas no Telegram. Um worker consulta os preços na CoinGecko em intervalos regulares, guarda o histórico e, quando uma moeda cruza o preço-alvo de um alerta, envia uma mensagem no Telegram. Os alertas são gerenciados por uma API REST.

```text
Bitcoin (BTC) subiu para R$ 612.345,67.
Seu alerta: acima de R$ 600.000,00.
```

## Funcionalidades

- **Monitoramento contínuo:** um worker busca os preços em reais de todas as moedas cadastradas numa única chamada à CoinGecko, a cada 5 minutos (configurável)
- **Histórico de preços:** cada busca grava um registro por moeda, indexado por moeda e data
- **Alertas de alta e de baixa:** dispara quando o preço sobe até o alvo ou acima (`above`), ou cai até o alvo ou abaixo (`below`)
- **Avisos no Telegram** com os valores formatados em reais; moedas abaixo de R$ 1 mantêm até 8 casas decimais
- **Entrega garantida:** se o Telegram falhar, o aviso fica pendente e é reenviado no ciclo seguinte
- **Rearme:** um alerta que já disparou pode ser reativado pela API
- **API protegida por chave** (`X-API-Key`) para listar, criar, rearmar e apagar alertas

## Tecnologias

- **Python 3.14** e **FastAPI**
- **PostgreSQL 17**, **SQLAlchemy 2.0** e **Alembic** (migrations)
- **httpx** (clientes da CoinGecko e do Telegram) e **Pydantic Settings** (configuração)
- **pytest** e **pytest-cov** (mais de 50 testes, com as APIs externas simuladas)
- **Ruff** (lint e formatação)
- **Docker** e **Docker Compose**

## Como funciona

O projeto tem dois processos que compartilham o mesmo banco: a **API**, que gerencia os alertas, e o **worker**, que roda em loop. Cada ciclo do worker:

```mermaid
flowchart LR
    A[Busca os preços<br/>na CoinGecko] --> B[Grava o histórico<br/>price_snapshots]
    B --> C[Marca os alertas<br/>atingidos como disparados]
    C --> D[(commit)]
    D --> E[Envia os avisos<br/>pendentes no Telegram]
    E --> F[Marca cada aviso<br/>como enviado]
```

Disparar o alerta e enviar o aviso são etapas separadas. Um alerta disparado (`triggered_at` preenchido) com `notified_at` vazio é um aviso pendente, e o worker tenta enviá-lo a cada ciclo até conseguir.

## Modelo de dados

```mermaid
erDiagram
    COINS ||--o{ PRICE_SNAPSHOTS : "tem histórico"
    COINS ||--o{ ALERTS : "é monitorada por"

    COINS {
        int id PK
        string coingecko_id UK
        string symbol
        string name
    }
    PRICE_SNAPSHOTS {
        int id PK
        int coin_id FK
        numeric price
        string currency
        datetime fetched_at
    }
    ALERTS {
        int id PK
        int coin_id FK
        string direction
        numeric target_price
        bool is_active
        datetime triggered_at
        numeric triggered_price
        datetime notified_at
    }
```

## Rotas

Todas as rotas de `/alerts` exigem o cabeçalho `X-API-Key` com o valor de `API_KEY` do `.env`.

| Método | Rota | Descrição |
|---|---|---|
| GET | `/health` | Verifica se a API e o banco estão no ar |
| GET | `/alerts` | Lista os alertas, do mais recente para o mais antigo |
| GET | `/alerts?active=true` | Só os ativos (`false` para os já disparados) |
| GET | `/alerts/{id}` | Busca um alerta |
| POST | `/alerts` | Cria um alerta |
| POST | `/alerts/{id}/rearm` | Reativa um alerta que já disparou e já teve o aviso enviado |
| DELETE | `/alerts/{id}` | Apaga um alerta |

Exemplo de criação:

```bash
curl -X POST http://localhost:8001/alerts \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"coin_id": 1, "direction": "above", "target_price": "600000"}'
```

Envie o `target_price` como texto para não perder precisão. A documentação interativa fica em [`/docs`](http://localhost:8001/docs).

## Decisões técnicas

**Dinheiro sem `float`.** Preços são `Decimal` do começo ao fim: a resposta da CoinGecko é lida com `parse_float=Decimal` e pedida com `precision=full`, e o banco usa `NUMERIC(30, 12)`, suficiente para moedas que valem frações de centavo.

**Aviso pendente em vez de envio imediato.** O worker primeiro confirma no banco quais alertas dispararam e só depois envia as mensagens, cada uma com o seu commit. Se o Telegram estiver fora do ar ou o worker cair no meio do ciclo, nenhum aviso se perde: ele continua pendente e sai no próximo ciclo.

**O token do bot nunca vai para o log.** A URL da API do Telegram contém o token. Os erros do cliente nunca incluem a URL, e o log de requisições do httpx fica restrito a avisos e erros.

**Worker resiliente.** Uma falha na CoinGecko (incluindo o limite de requisições, HTTP 429) pula só a busca de preços daquele ciclo; os avisos pendentes continuam sendo enviados. Qualquer erro inesperado faz rollback e o worker segue para o próximo ciclo. Ao receber `SIGTERM` ou `SIGINT`, ele termina o ciclo atual e encerra sem cortar nada pela metade.

**Arquitetura em camadas.** Routers (HTTP), services (regras de negócio) e repositories (acesso ao banco). Os services não conhecem HTTP: lançam exceções da aplicação, que um único handler converte em 401, 404 ou 409. A mesma regra de disparo é usada pelo worker e coberta pelos testes, inclusive o caso do preço exatamente igual ao alvo, que dispara.

**Regras protegidas também no banco.** Preço-alvo e preços do histórico positivos são garantidos por constraints no PostgreSQL, além da validação na API. A chave de API é comparada em tempo constante (`secrets.compare_digest`).

## Como rodar localmente

Pré-requisitos: Docker, uma chave gratuita da [CoinGecko](https://www.coingecko.com/en/api) (plano Demo) e um bot do Telegram.

**1. Configure o ambiente**

```bash
git clone https://github.com/tassohenrique/crypto-price-alerts.git
cd crypto-price-alerts
cp .env.example .env
```

No `.env`, troque a senha do banco (nas três variáveis em que ela aparece) e preencha:

| Variável | Como obter |
|---|---|
| `COINGECKO_API_KEY` | Crie em [coingecko.com/en/api](https://www.coingecko.com/en/api) |
| `TELEGRAM_BOT_TOKEN` | Converse com o [@BotFather](https://t.me/BotFather) no Telegram e use `/newbot` |
| `TELEGRAM_CHAT_ID` | Mande uma mensagem para o seu bot e abra `https://api.telegram.org/bot<TOKEN>/getUpdates`; o id está em `message.chat.id` |
| `API_KEY` | Qualquer valor secreto, por exemplo `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `POLL_INTERVAL_SECONDS` | Opcional. Intervalo entre os ciclos do worker; o padrão é 300 |

**2. Suba os serviços e crie as tabelas**

```bash
docker compose up -d --build
docker compose exec app alembic upgrade head
```

A API sobe em http://localhost:8001 e o banco fica exposto na porta 5433.

**3. Cadastre as moedas que quer acompanhar**

O primeiro argumento é o id da moeda na CoinGecko, o mesmo que aparece na URL da moeda no site:

```bash
docker compose exec app python -m scripts.add_coin bitcoin BTC Bitcoin
docker compose exec app python -m scripts.add_coin ethereum ETH Ethereum
```

Depois disso, crie alertas pela API. Para acompanhar o worker:

```bash
docker compose logs -f worker
```

### Desenvolvimento sem Docker para a API

```bash
docker compose up -d db
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
fastapi dev app/main.py        # API
python -m app.worker           # worker, em outro terminal
```

Fora do Docker, as variáveis `DATABASE_URL` e `TEST_DATABASE_URL` do `.env` apontam para `localhost:5433`.

## Testes

Os testes usam um banco separado. Crie ele uma única vez:

```bash
docker compose exec db createdb -U crypto crypto_test
```

Depois:

```bash
docker compose exec app python -m pytest -v
docker compose exec app python -m pytest --cov=app --cov-report=term-missing   # com cobertura
```

As chamadas à CoinGecko e ao Telegram são simuladas com `httpx.MockTransport`, então os testes não precisam de internet nem de chaves reais.

## Autor

**Tasso Rodrigues** · [LinkedIn](https://www.linkedin.com/in/tassorodrigues/) · [GitHub](https://github.com/tassohenrique)
