# Лабораторная работа 13

Швачкина Виктория, CSE6742onl. Вариант 3.
Преподаватель: Байкувеков М.Б.

Тема: функциональное ядро, параллелизм, asyncio, Pandas и фильтры изображений.

Нужен Python 3.12. Из этого каталога:

```powershell
py -3 -m pip install -r requirements.txt
py -3 main.py
py -3 -m pytest --cov=analytics --cov-report=term-missing
py -3 -m ruff check src tests
py -3 -m mypy src/analytics
```

`run_windows.cmd` создаёт локальное окружение .venv, устанавливает зависимости,
запускает демонстрацию и тесты. Для первой установки нужен интернет.

Фактические результаты находятся в demo_log.txt, pytest_log.txt,
ruff_log.txt, mypy_log.txt и coverage.json.
Исходники пакета находятся в src/analytics, тесты в tests.
В pyproject.toml включён строгий mypy, Ruff E/F/B/I и каталог тестов.
Все примеры входных данных учебные.

Из общего каталога `python measure.py` повторяет измерения трёх работ.
Графики и measurements.json содержат исходный результат замеров.
Время зависит от нагрузки и компьютера.

Git-репозиторий локальный, папка .git включена в архив.
Комплект опубликован в общем репозитории https://github.com/viconda/functional-programming-10-15.
Результат удалённых проверок доступен во вкладке Actions.
Файл .github/workflows/tests.yml готов для запуска после публикации.
