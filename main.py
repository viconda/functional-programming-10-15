"""Вход в пример интернет магазина."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/"src"))
from shop.shell import main
if __name__ == "__main__":
    main()
