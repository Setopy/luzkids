from content_loader import load_all_series, load_series, load_lesson


def test_load_all_series_returns_known_series():
    series_list = load_all_series()
    ids = {s["id"] for s in series_list}
    assert "ephesians" in ids


def test_load_series_unknown_returns_none():
    assert load_series("not-a-real-series") is None


def test_load_series_returned_dict_is_a_copy():
    a = load_series("ephesians")
    b = load_series("ephesians")
    a["title"] = "mutated"
    assert b["title"] != "mutated"


def test_load_lesson_unknown_returns_none():
    assert load_lesson("ephesians", "not-a-real-lesson") is None


def test_load_lesson_known():
    series = load_series("ephesians")
    first_lesson_id = series["lessons"][0]["id"]
    lesson = load_lesson("ephesians", first_lesson_id)
    assert lesson is not None
    assert lesson["id"] == first_lesson_id
