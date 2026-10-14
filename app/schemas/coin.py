from pydantic import BaseModel, ConfigDict, Field


class CoinCreate(BaseModel):
    coingecko_id: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9-]+$",
        description="Id da moeda na CoinGecko (aparece na URL da moeda no site).",
        examples=["solana"],
    )


class CoinRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    coingecko_id: str
    symbol: str
    name: str
