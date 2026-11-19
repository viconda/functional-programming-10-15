"""Задание 1. Швачкина Виктория, группа CSE6742onl.

Фильтрация оценок, буквенная шкала и форматирование имён без циклов.
Шкала учебная: A >= 90, B >= 75, C >= 60, D >= 50, иначе F.
Полное имя задаётся в порядке «Фамилия Имя [Отчество]».
"""

SCORES = [0, 49, 50, 59, 60, 74, 75, 89, 90, 100,
          45, 67, 82, 93, 51, 38, 76, 88, 99, 54]
NAMES = [
    "Швачкина Виктория", "Иванов Иван Иванович", "Петрова Анна",
    "Сидоров Павел", "Ким Мария", "Ахметова Алия", "Смирнов Олег",
    "Волкова Елена", "Белов Артём", "Орлова Дарья", "Соколов Илья",
    "Морозова Ольга", "Фёдоров Максим", "Зайцева Ирина",
    "Николаев Роман", "Ли", "Я", "  Пак   София  ", "", "Ким",
]


def to_letter(score: int) -> str:
    """Преобразовать корректный балл от 0 до 100 в учебную букву."""
    return ("A" if score >= 90 else "B" if score >= 75 else
            "C" if score >= 60 else "D" if score >= 50 else "F")


def passed_scores(scores: list[int]) -> list[int]:
    """Вернуть баллы не ниже 50, сохранив порядок."""
    return list(filter(lambda score: score >= 50, scores))


def letters_map(scores: list[int]) -> list[str]:
    """Выполнить отбор и преобразование через filter и map."""
    return list(map(to_letter, filter(lambda s: s >= 50, scores)))


def letters_comp(scores: list[int]) -> list[str]:
    """Выполнить тот же отбор через списковое включение."""
    return [to_letter(score) for score in scores if score >= 50]


def clean_names(names: list[str]) -> list[str]:
    """Убрать крайние и повторяющиеся пробелы в исходных именах."""
    return list(map(lambda name: " ".join(name.split()), names))


def valid_names(names: list[str]) -> list[str]:
    """Отобрать строки от 3 символов, содержащие фамилию и имя."""
    return list(filter(
        lambda name: len(name) >= 3 and len(name.split()) >= 2,
        clean_names(names),
    ))


def format_name(name: str) -> str:
    """Вернуть «Фамилия И.» для уже проверенной полной записи."""
    parts = name.split()
    return f"{parts[0]} {parts[1][0]}."


def format_names(names: list[str]) -> list[str]:
    """Форматировать имена и сортировать без учёта регистра."""
    return sorted(
        map(format_name, valid_names(names)),
        key=lambda name: name.casefold().replace("ё", "е"),
    )


def main() -> None:
    """Показать исходные, промежуточные и итоговые данные."""
    # Comprehension короче для простого правила. map/filter явно
    # разделяют отбор и преобразование и работают с итераторами.
    selected_comp = [score for score in SCORES if score >= 50]
    assert passed_scores(SCORES) == selected_comp
    assert letters_map(SCORES) == letters_comp(SCORES)
    print("Исходные 20 оценок:", SCORES)
    print("Шкала: A=90..100, B=75..89, C=60..74, D=50..59, F=0..49")
    print("Зачётные баллы (filter):", passed_scores(SCORES))
    print("Буквы (map/filter):", letters_map(SCORES))
    print("Зачётные баллы (comprehension):", selected_comp)
    print("Буквы (comprehension):", letters_comp(SCORES))
    print("Результаты двух способов совпадают:",
          letters_map(SCORES) == letters_comp(SCORES))
    print("Исходные имена:", NAMES)
    print("После удаления лишних пробелов:", clean_names(NAMES))
    print("После отбора корректных полных имён:", valid_names(NAMES))
    print("До сортировки:", list(map(format_name, valid_names(NAMES))))
    print("После сортировки:", format_names(NAMES))


if __name__ == "__main__":
    main()
