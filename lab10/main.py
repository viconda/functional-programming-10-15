"""Персистентные структуры и эксперименты лабораторной работы 10."""

from __future__ import annotations

import copy
import operator
import random
import tracemalloc
from collections import deque
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Self

from pyrsistent import InvariantException, PRecord, field, freeze, pmap, pset, pvector, thaw


@dataclass(frozen=True, slots=True)
class PList:
    """Узел списка. None обозначает пустой хвост."""

    head: Any
    tail: PList | None = None

    @staticmethod
    def cons(value: Any, tail: PList | None = None) -> PList:
        """Добавить голову с разделением хвоста."""
        return PList(value, tail)

    @classmethod
    def from_iterable(cls, values: Iterable[Any]) -> PList | None:
        """Построить список в порядке следования значений."""
        result = None
        for value in reversed(tuple(values)):
            result = cls.cons(value, result)
        return result

    def __iter__(self) -> Iterator[Any]:
        """Пройти по узлам без рекурсии."""
        node = self
        while node is not None:
            yield node.head
            node = node.tail

    def __eq__(self, other: object) -> bool:
        """Сравнить последовательности по значениям."""
        from itertools import zip_longest

        missing = object()
        return isinstance(other, PList) and all(
            a == b for a, b in zip_longest(self, other, fillvalue=missing)
        )

    def __hash__(self) -> int:
        """Вычислить хеш последовательности хешируемых значений."""
        return hash(tuple(self))

    def to_list(self) -> list[Any]:
        """Вернуть обычный список."""
        return list(self)

    def length(self) -> int:
        """Посчитать узлы."""
        return sum(1 for _ in self)

    def nth(self, index: int) -> Any:
        """Найти элемент по индексу с нуля."""
        if index < 0:
            raise IndexError(index)
        node = self.drop(index)
        if node is None:
            raise IndexError(index)
        return node.head

    def take(self, n: int) -> PList | None:
        """Скопировать до n начальных узлов."""
        from itertools import islice

        return self.from_iterable(islice(self, max(n, 0)))

    def drop(self, n: int) -> PList | None:
        """Вернуть существующий хвост после n узлов."""
        node = self
        for _ in range(max(n, 0)):
            if node is None:
                break
            node = node.tail
        return node

    def map(self, fn: Callable) -> PList | None:
        """Преобразовать значения."""
        return self.from_iterable(map(fn, self))

    def filter(self, predicate: Callable) -> PList | None:
        """Оставить значения, прошедшие проверку."""
        return self.from_iterable(filter(predicate, self))

    def fold_left(self, fn: Callable, seed: Any) -> Any:
        """Свернуть список слева направо."""
        for value in self:
            seed = fn(seed, value)
        return seed

    def fold_right(self, fn: Callable, seed: Any) -> Any:
        """Свернуть список справа налево."""
        for value in reversed(tuple(self)):
            seed = fn(value, seed)
        return seed

    def reverse(self) -> PList:
        """Развернуть список за линейное время."""
        return self.fold_left(lambda tail, value: PList.cons(value, tail), None)

    def append(self, other: PList | None) -> PList:
        """Скопировать левую часть и разделить правую."""
        return self.fold_right(PList.cons, other)


@dataclass(frozen=True, slots=True)
class Queue:
    """FIFO с прямым передним и обратным задним стеком."""

    front: PList | None = None
    back: PList | None = None
    size: int = 0

    def enqueue(self, value: Any) -> Queue:
        """Вернуть очередь с новым последним элементом."""
        if self.front is None:
            return Queue(PList(value), None, 1)
        return Queue(self.front, PList(value, self.back), self.size + 1)

    def dequeue(self) -> tuple[Any, Queue]:
        """Вернуть первый элемент и следующую версию."""
        if self.front is None:
            raise IndexError("Пустая очередь")
        tail = self.front.tail
        if tail is None and self.back is not None:
            return self.front.head, Queue(self.back.reverse(), None, self.size - 1)
        return self.front.head, Queue(tail, self.back, self.size - 1)

    def peek(self) -> Any:
        """Прочитать первый элемент."""
        if self.front is None:
            raise IndexError("Пустая очередь")
        return self.front.head

    def is_empty(self) -> bool:
        """Проверить, пуста ли очередь."""
        return self.size == 0

    def __len__(self) -> int:
        """Вернуть сохранённый размер очереди."""
        return self.size


@dataclass(frozen=True)
class Maybe:
    """Значение или отсутствие значения."""

    value: Any

    @classmethod
    def unit(cls, value: Any) -> Self:
        """Упаковать значение."""
        return cls(value)

    def map(self, fn: Callable) -> Maybe:
        """Преобразовать присутствующее значение."""
        return self.bind(lambda x: Maybe.unit(fn(x)))

    def bind(self, fn: Callable) -> Maybe:
        """Продолжить вычисление при наличии значения."""
        return self if self.value is None else fn(self.value)


@dataclass(frozen=True)
class ListM:
    """Упорядоченные альтернативы вычисления."""

    values: tuple

    @classmethod
    def unit(cls, value: Any) -> Self:
        """Создать единственную альтернативу."""
        return cls((value,))

    def map(self, fn: Callable) -> ListM:
        """Преобразовать альтернативы."""
        return self.bind(lambda x: ListM.unit(fn(x)))

    def bind(self, fn: Callable) -> ListM:
        """Объединить альтернативы в порядке обхода."""
        return ListM(tuple(y for x in self.values for y in fn(x).values))


@dataclass(frozen=True)
class Writer:
    """Результат с неизменяемым журналом."""

    value: Any
    log: tuple[str, ...] = ()

    @classmethod
    def unit(cls, value: Any) -> Self:
        """Упаковать значение с пустым журналом."""
        return cls(value)

    def map(self, fn: Callable) -> Writer:
        """Преобразовать результат, сохранив журнал."""
        return self.bind(lambda x: Writer.unit(fn(x)))

    def bind(self, fn: Callable) -> Writer:
        """Продолжить вычисление и склеить журналы."""
        next_value = fn(self.value)
        return Writer(next_value.value, self.log + next_value.log)


def check_laws(unit: Callable, values: Iterable, funcs: tuple[Callable, ...]) -> int:
    """Проверить три закона монады и два закона функтора."""
    count = 0
    for x in values:
        m = unit(x)
        assert m.bind(unit) == m
        assert m.map(lambda y: y) == m
        for f in funcs:
            assert m.bind(f) == f(x)
            for g in funcs:
                assert m.bind(f).bind(g) == m.bind(lambda y: f(y).bind(g))
                assert m.map(lambda y: y + 1).map(lambda y: y * 2) == m.map(lambda y: (y + 1) * 2)
                count += 2
            count += 1
        count += 2
    return count


def triples(limit: int) -> tuple:
    """Найти пифагоровы тройки, комбинируя ветви только через bind."""
    return (
        ListM(tuple(range(1, limit + 1)))
        .bind(
            lambda a: ListM(tuple(range(a, limit + 1))).bind(
                lambda b: ListM(tuple(range(b, limit + 1))).bind(
                    lambda c: ListM.unit((a, b, c)) if a * a + b * b == c * c else ListM(())
                )
            )
        )
        .values
    )


def factorial(n: int) -> Writer:
    """Вычислить факториал и собрать журнал умножений."""
    if n < 0:
        raise ValueError(n)
    value = Writer.unit(1)
    for i in range(1, n + 1):
        value = value.bind(lambda x: Writer(x * i, (f"{x} × {i} = {x * i}",)))
    return value


class Student(PRecord):
    """Запись студента с обязательным именем и оценкой от 0 до 100."""

    name = field(type=str, mandatory=True, invariant=lambda s: (bool(s.strip()), "Имя"))
    score = field(type=int, mandatory=True, invariant=lambda n: (0 <= n <= 100, "Балл"))


def add_edge(graph: Any, u: str, v: str) -> Any:
    """Вернуть новую версию неориентированного графа."""
    return graph.set(u, graph.get(u, pset()).add(v)).set(v, graph.get(v, pset()).add(u))


def bfs(graph: Any, start: str) -> tuple[str, ...]:
    """Обойти достижимые вершины в ширину."""
    pending = deque([start])
    seen = {start}
    order = []
    while pending:
        node = pending.popleft()
        order.append(node)
        for neighbor in sorted(graph.get(node, ())):
            if neighbor not in seen:
                seen.add(neighbor)
                pending.append(neighbor)
    return tuple(order)


@dataclass(frozen=True, slots=True)
class BST:
    """Узел персистентного множества целых чисел."""

    key: int
    left: BST | None = None
    right: BST | None = None


def insert(tree: BST | None, key: int) -> BST:
    """Скопировать путь к новому ключу."""
    path = []
    node = tree
    while node is not None:
        if key == node.key:
            return tree
        left = key < node.key
        path.append((node, left))
        node = node.left if left else node.right
    updated = BST(key)
    for node, left in reversed(path):
        updated = BST(node.key, updated, node.right) if left else BST(node.key, node.left, updated)
    return updated


def inorder(tree: BST | None) -> Iterator[int]:
    """Пройти по ключам в отсортированном порядке."""
    stack = []
    node = tree
    while stack or node is not None:
        while node is not None:
            stack.append(node)
            node = node.left
        node = stack.pop()
        yield node.key
        node = node.right


def contains(tree: BST | None, key: int) -> bool:
    """Проверить наличие ключа."""
    while tree is not None:
        if key == tree.key:
            return True
        tree = tree.left if key < tree.key else tree.right
    return False


def union(first: BST | None, second: BST | None) -> BST | None:
    """Добавить ключи второго множества к первому."""
    for key in inorder(second):
        first = insert(first, key)
    return first


def intersection(first: BST | None, second: BST | None) -> BST | None:
    """Построить сбалансированное дерево общих ключей."""
    keys = tuple(key for key in inorder(first) if contains(second, key))

    def build(left: int, right: int) -> BST | None:
        if left >= right:
            return None
        mid = (left + right) // 2
        return BST(keys[mid], build(left, mid), build(mid + 1, right))

    return build(0, len(keys))


@dataclass(frozen=True)
class Version:
    """Корень множества и ссылка на предыдущую версию."""

    tree: BST | None = None
    parent: Version | None = None

    def add(self, key: int) -> Version:
        """Сохранить прежний корень в цепочке истории."""
        return Version(insert(self.tree, key), self)

    def combine(self, other: Version, operation: Callable) -> Version:
        """Сохранить объединение или пересечение новой версией."""
        return Version(operation(self.tree, other.tree), self)


@dataclass(frozen=True)
class Zipper:
    """Фокус дерева и контекст из родителя и направления."""

    focus: BST
    context: tuple[tuple[BST, bool], ...] = ()

    def down_left(self) -> Zipper:
        """Перейти к левому ребёнку."""
        if self.focus.left is None:
            raise IndexError("Нет левого узла")
        return Zipper(self.focus.left, self.context + ((self.focus, True),))

    def down_right(self) -> Zipper:
        """Перейти к правому ребёнку."""
        if self.focus.right is None:
            raise IndexError("Нет правого узла")
        return Zipper(self.focus.right, self.context + ((self.focus, False),))

    def up(self) -> Zipper:
        """Воссоздать родителя с обновлённым ребёнком."""
        parent, left = self.context[-1]
        updated = (
            BST(parent.key, self.focus, parent.right)
            if left
            else BST(parent.key, parent.left, self.focus)
        )
        return Zipper(updated, self.context[:-1])

    def replace(self, tree: BST) -> Zipper:
        """Заменить поддерево в фокусе."""
        return Zipper(tree, self.context)

    def root(self) -> BST:
        """Восстановить корень одним проходом по пути."""
        tree = self.focus
        for parent, left in reversed(self.context):
            tree = (
                BST(parent.key, tree, parent.right) if left else BST(parent.key, parent.left, tree)
            )
        return tree


def measure(factory: Callable, update: Callable, count: int) -> tuple[float, float]:
    """Измерить время и пиковую память при удержании всех версий."""
    initial = factory()
    tracemalloc.start()
    start = perf_counter()
    history = [initial]
    try:
        for i in range(count):
            history.append(update(history[-1], i))
        elapsed = perf_counter() - start
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    return elapsed, peak / (1024 * 1024)


def deep_set(data: dict, key: int) -> dict:
    """Скопировать словарь рекурсивно и изменить копию."""
    result = copy.deepcopy(data)
    result[key] = -key - 1
    return result


def queue_check(n: int) -> float:
    """Сравнить очередь с deque на воспроизводимой серии операций."""
    rng = random.Random(310)
    queue, oracle = Queue(), deque()
    snapshots = []
    start = perf_counter()
    for i in range(n):
        if not oracle or rng.random() < 0.52:
            queue = queue.enqueue(i)
            oracle.append(i)
        else:
            assert queue.peek() == oracle[0]
            value, queue = queue.dequeue()
            assert value == oracle.popleft()
        assert len(queue) == len(oracle)
        assert queue.is_empty() == (not oracle)
        if i % 1000 == 0:
            snapshots.append((queue, tuple(oracle)))
    elapsed = perf_counter() - start
    for old, expected in snapshots:
        actual = []
        while not old.is_empty():
            value, old = old.dequeue()
            actual.append(value)
        assert tuple(actual) == expected
    return elapsed


def main() -> None:
    """Запустить проверки, примеры и измерения."""
    tail = PList.from_iterable([2, 3])
    a, b = PList.cons(1, tail), PList.cons(9, tail)
    assert a.tail is b.tail
    assert a.take(2).to_list() == [1, 2] and a.drop(1) is tail
    assert a.nth(2) == 3 and a.length() == 3
    assert a.map(lambda x: x * 2).to_list() == [2, 4, 6]
    assert a.filter(lambda x: x > 1) == tail
    assert a.reverse().to_list() == [3, 2, 1]
    assert a.fold_left(operator.sub, 0) == -6
    assert a.fold_right(operator.sub, 0) == 2
    assert a.append(tail).drop(3) is tail
    print("1. PList:", a.to_list(), b.to_list(), "общий хвост:", a.tail is b.tail)

    print("2. FIFO и сохранность версий, проверка с deque")
    for size in (10_000, 25_000, 50_000, 100_000):
        print(f"  {size:>6} операций: {queue_check(size):.4f} с")

    initial = dict.fromkeys(range(10_000), 0)
    print("3. 10 000 записей, 1000 обновлений: метод | секунды | МиБ")
    for name, factory, fn in (
        ("deepcopy", lambda: initial, deep_set),
        ("{**d, k: v}", lambda: initial, lambda d, k: {**d, k: -k - 1}),
        ("pmap.set", lambda: pmap(initial), lambda d, k: d.set(k, -k - 1)),
    ):
        seconds, mib = measure(factory, fn, 1000)
        print(f"  {name:12} | {seconds:.4f} | {mib:.3f}")

    config = freeze({"server": {"port": 80, "hosts": ["a", "b"]}})
    changed = config.transform(("server", "port"), 443).transform(
        ("server", "hosts", 0), str.upper
    )
    assert thaw(config)["server"]["port"] == 80
    print("4. Конфигурация:", thaw(changed))
    vector = pvector([0] * 1000)
    start = perf_counter()
    direct = vector
    for i in range(1000):
        direct = direct.set(i, i + 1)
    direct_time = perf_counter() - start
    start = perf_counter()
    builder = vector.evolver()
    for i in range(1000):
        builder[i] = i + 1
    batched = builder.persistent()
    assert direct == batched and vector[-1] == 0
    print(f"  pvector.set: {direct_time:.6f} с, evolver: {perf_counter() - start:.6f} с")
    student = Student(name="Виктория", score=92)
    try:
        student.set(score=101)
    except InvariantException:
        print("  PRecord отклонил 101, сохранён балл", student.score)
    else:
        raise AssertionError("Инвариант не сработал")
    graph = add_edge(pmap(), "A", "B")
    assert bfs(graph, "A") == ("A", "B")
    print("  BFS:", bfs(add_edge(graph, "B", "C"), "A"))

    print("5. Проверка законов:")
    funcs = (
        (lambda x: Maybe.unit(x + 2), lambda x: Maybe(None)),
        (lambda x: ListM((x, x + 1)), lambda x: ListM(())),
        (lambda x: Writer(x + 1, ("+1",)), lambda x: Writer(x * 2, ("×2",))),
    )
    for cls, pair in zip((Maybe, ListM, Writer), funcs):
        print(f"  {cls.__name__}: {check_laws(cls.unit, range(5), pair)} проверок")
    print("  Тройки:", triples(20))
    print("  5!:", factorial(5))

    first = Version().add(8).add(4).add(12)
    second = Version().add(4).add(9)
    branch = first.add(6)
    assert branch.tree.right is first.tree.right
    assert tuple(inorder(branch.parent.tree)) == (4, 8, 12)
    joined = first.combine(second, union)
    common = first.combine(second, intersection)
    assert tuple(inorder(joined.tree)) == (4, 8, 9, 12)
    assert tuple(inorder(common.tree)) == (4,)
    print("6. BST: исходное", tuple(inorder(first.tree)), "ветка", tuple(inorder(branch.tree)))
    print(
        "  Объединение:", tuple(inorder(joined.tree)), "пересечение:", tuple(inorder(common.tree))
    )
    order = list(range(3000))
    random.Random(310).shuffle(order)
    base = None
    for k in order:
        base = insert(base, k)
    for name, factory, fn in (
        ("копирование пути", lambda: base, lambda t, k: insert(t, 3000 + k)),
        ("полная копия set", lambda: set(order), lambda s, k: s | {3000 + k}),
    ):
        order_updates = list(range(1000))
        random.Random(312).shuffle(order_updates)
        seconds, mib = measure(factory, lambda x, i: fn(x, order_updates[i]), 1000)
        print(f"  {name}: {seconds:.4f} с, {mib:.3f} МиБ")

    zipper = Zipper(first.tree)
    edited = zipper.down_left().replace(BST(5)).root()
    assert zipper.down_right().up().focus == first.tree
    assert edited.right is first.tree.right and first.tree.left.key == 4
    print("Доп. Zipper:", tuple(inorder(edited)), "исходный", tuple(inorder(first.tree)))


if __name__ == "__main__":
    main()
