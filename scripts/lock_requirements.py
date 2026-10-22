"""Gera requirements.txt e requirements-dev.txt com as versões exatas.

Uso (dentro do container, para usar o mesmo Python da imagem):
    docker compose run --rm app python -m scripts.lock_requirements

Instala cada arquivo .in num ambiente virtual limpo e grava o `pip freeze`.
Assim o build de amanhã instala exatamente o que passou no CI hoje.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEADER = "# Gerado por scripts/lock_requirements.py a partir do {}. Não edite à mão."


def freeze(requirements_in: str) -> set[str]:
    """Instala o arquivo num ambiente virtual novo e devolve o `pip freeze`."""
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([sys.executable, "-m", "venv", tmp], check=True)
        pip = Path(tmp) / "bin" / "pip"
        subprocess.run(
            [pip, "install", "--quiet", "-r", ROOT / requirements_in], check=True
        )
        output = subprocess.run(
            [pip, "freeze", "--exclude", "pip"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    return set(output.split())


def write(path: str, lines: list[str]) -> None:
    (ROOT / path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    prod = freeze("requirements.in")
    dev = freeze("requirements-dev.in")

    write(
        "requirements.txt",
        [HEADER.format("requirements.in"), *sorted(prod, key=str.lower)],
    )
    # O dev reaproveita o arquivo de produção e só lista o que é exclusivo dele.
    write(
        "requirements-dev.txt",
        [
            HEADER.format("requirements-dev.in"),
            "-r requirements.txt",
            *sorted(dev - prod, key=str.lower),
        ],
    )
    print("requirements.txt e requirements-dev.txt atualizados.")


if __name__ == "__main__":
    main()
