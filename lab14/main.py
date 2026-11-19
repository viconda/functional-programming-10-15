"""Вход в планировщик расписания."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from schedule.shell import main
if __name__ == "__main__":
    main()
