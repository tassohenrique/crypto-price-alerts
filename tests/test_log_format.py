import json
import logging
import sys

from app.core.log_format import JsonFormatter, make_formatter


def make_record(message="Ciclo concluído: %d preços.", args=(3,), **extra):
    record = logging.LogRecord(
        name="app.worker",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=args,
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_json_has_standard_fields():
    line = JsonFormatter().format(make_record())

    data = json.loads(line)
    assert data["level"] == "INFO"
    assert data["logger"] == "app.worker"
    assert data["message"] == "Ciclo concluído: 3 preços."
    assert data["time"].endswith("+00:00")


def test_json_is_a_single_line():
    line = JsonFormatter().format(make_record("linha 1\nlinha 2", ()))

    assert "\n" not in line


def test_extra_fields_become_json_fields():
    line = JsonFormatter().format(make_record(prices_saved=3, alerts_triggered=1))

    data = json.loads(line)
    assert data["prices_saved"] == 3
    assert data["alerts_triggered"] == 1


def test_internal_record_attributes_stay_out():
    data = json.loads(JsonFormatter().format(make_record()))

    for internal in ("args", "msg", "pathname", "lineno", "exc_info", "created"):
        assert internal not in data


def test_exception_goes_to_its_own_field():
    record = make_record("Erro inesperado.", ())
    try:
        raise RuntimeError("falha simulada")
    except RuntimeError:
        record.exc_info = sys.exc_info()

    data = json.loads(JsonFormatter().format(record))

    assert "RuntimeError: falha simulada" in data["exception"]


def test_non_serializable_extra_does_not_break_logging():
    data = json.loads(JsonFormatter().format(make_record(when=object())))

    assert data["when"].startswith("<object object")


def test_make_formatter_picks_the_format():
    assert isinstance(make_formatter("json"), JsonFormatter)
    assert not isinstance(make_formatter("text"), JsonFormatter)
