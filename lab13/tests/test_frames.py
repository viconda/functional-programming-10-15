import pandas as pd

from analytics.frames import add_features, aggregate, clean, filter_valid, parallel, pipeline


def test_frames():
    df = pd.DataFrame(
        {"branch": [" A ", "b", None, "a"], "qty": [2, 3, 1, -1], "price": [10, 20, 1, 5]}
    )
    original = df.copy(deep=True)
    for step in (clean, add_features, filter_valid, aggregate):
        source = add_features(clean(df)) if step == aggregate else df
        before = source.copy(deep=True)
        step(source)
        pd.testing.assert_frame_equal(source, before)
    pd.testing.assert_frame_equal(df, original)
    pd.testing.assert_frame_equal(pipeline(df), parallel(df, 2))
    assert pipeline(df).revenue.sum() == 80
