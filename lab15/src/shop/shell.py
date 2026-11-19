import argparse
import json
from pathlib import Path

from .pipeline import process


def run_file(source: Path, target: Path) -> None:
    """Оставить файловые эффекты и печать в оболочке."""
    result = process(json.loads(source.read_text(encoding="utf-8")))
    report = json.dumps(result, ensure_ascii=False, sort_keys=True)
    target.write_text(report, encoding="utf-8")
    print(report)


def main(argv: list[str] | None = None) -> None:
    """CLI для журнала действий и файла заказа."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "source", type=Path, nargs="?", default=Path(__file__).parents[2] / "sample.json"
    )
    parser.add_argument("--output", type=Path, default=Path("order.json"))
    args = parser.parse_args(argv)
    run_file(args.source, args.output)
