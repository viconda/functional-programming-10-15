"""Демонстрация лабораторной работы 13."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from functools import partial
from datetime import date
from analytics.shell import run
from analytics.images import transform

def main() -> None:
    """Собрать конфигурацию оболочки и показать фильтры."""
    source = Path(__file__).parent / "grades.csv"
    configured = partial(run, load=partial(source.read_text, encoding="utf-8"), now=date.today,
                         save=partial(Path("report.txt").write_text, encoding="utf-8"))
    configured()
    image = ((0, 0, 0), (0, 255, 0), (0, 0, 0))
    print("Размытие:", transform(image))
    print("Границы:", transform(image, "edges", 2))

if __name__ == "__main__":
    main()
