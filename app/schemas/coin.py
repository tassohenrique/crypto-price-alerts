from pydantic import BaseModel, ConfigDict


class CoinRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    coingecko_id: str
    symbol: str
    name: str
