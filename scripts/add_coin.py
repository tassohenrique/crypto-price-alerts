"""Cadastra uma moeda para o worker acompanhar.

Uso:
    python -m scripts.add_coin bitcoin BTC Bitcoin

O primeiro argumento é o id da moeda na CoinGecko (aparece na URL da moeda no site).
"""

import argparse

from app.db.session import SessionLocal
from app.models import Coin
from app.repositories.coin import CoinRepository


def main() -> None:
    parser = argparse.ArgumentParser(description="Cadastra uma moeda.")
    parser.add_argument("coingecko_id")
    parser.add_argument("symbol")
    parser.add_argument("name")
    args = parser.parse_args()

    with SessionLocal() as db:
        coins = CoinRepository(db)
        if coins.get_by_coingecko_id(args.coingecko_id) is not None:
            print(f"A moeda {args.coingecko_id} já está cadastrada.")
            return

        coins.add(
            Coin(
                coingecko_id=args.coingecko_id,
                symbol=args.symbol.upper(),
                name=args.name,
            )
        )
        db.commit()
        print(f"Moeda {args.name} cadastrada.")


if __name__ == "__main__":
    main()
