from enum import StrEnum


class AlertDirection(StrEnum):
    ABOVE = "above"  # dispara quando o preço sobe até o alvo ou acima
    BELOW = "below"  # dispara quando o preço cai até o alvo ou abaixo
