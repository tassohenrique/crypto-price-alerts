import json
import logging
from datetime import UTC, datetime

TEXT_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

# Atributos que todo LogRecord já tem. O que sobrar veio do `extra=` de quem
# registrou o log e vira campo próprio no JSON.
_STANDARD_ATTRS = set(vars(logging.makeLogRecord({}))) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    """Uma linha JSON por log, com os campos do `extra=` separados.

    Exemplo:
        logger.info("Ciclo concluído.", extra={"prices_saved": 3})
        {"time": "...", "level": "INFO", "logger": "app.worker",
         "message": "Ciclo concluído.", "prices_saved": 3}
    """

    def format(self, record: logging.LogRecord) -> str:
        created = datetime.fromtimestamp(record.created, UTC)
        payload = {
            "time": created.isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in vars(record).items():
            if key not in _STANDARD_ATTRS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def make_formatter(log_format: str) -> logging.Formatter:
    if log_format == "json":
        return JsonFormatter()
    return logging.Formatter(TEXT_FORMAT)
