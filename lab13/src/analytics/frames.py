from concurrent.futures import ProcessPoolExecutor

import pandas as pd


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Создать очищенную таблицу."""
    return df.dropna(subset=["branch", "qty", "price"]).assign(
        branch=lambda d: d.branch.str.strip().str.lower()
    )


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Вычислить выручку без изменения входа."""
    return df.assign(revenue=lambda d: d.qty * d.price)


def filter_valid(df: pd.DataFrame) -> pd.DataFrame:
    """Отобрать положительные количества и неотрицательные цены."""
    return df.query("qty > 0 and price >= 0").copy()


def aggregate(df: pd.DataFrame) -> pd.DataFrame:
    """Суммы и число строк по филиалу."""
    return df.groupby("branch", as_index=False).agg(
        revenue=("revenue", "sum"), orders=("qty", "size")
    )


def pipeline(df: pd.DataFrame) -> pd.DataFrame:
    """Четыре независимых шага через pipe."""
    return df.pipe(clean).pipe(add_features).pipe(filter_valid).pipe(aggregate)


def parallel(df: pd.DataFrame, workers: int = 4) -> pd.DataFrame:
    """MapReduce с повторной агрегацией частичных сумм."""
    size = max(1, (len(df) + workers - 1) // workers)
    parts = [df.iloc[i : i + size].copy() for i in range(0, len(df), size)]
    if not parts:
        return pipeline(df)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        partials = list(pool.map(pipeline, parts))
    return pd.concat(partials).groupby("branch", as_index=False)[["revenue", "orders"]].sum()
