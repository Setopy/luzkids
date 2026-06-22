"""
Content pipeline. A study series is a folder under content/:

    content/
      ephesians/
        series.json      <- metadata + ordered lesson list
        lesson01.json    <- one lesson, fully bilingual
        lesson02.json
        ...

Adding a new series = drop in a folder. No code changes, no redeploy logic.
Every human-visible string is a {"en": "...", "es": "..."} dict.
See CONTENT_GUIDE.md for the lesson template.
"""
import json
from functools import lru_cache
from pathlib import Path

CONTENT_DIR = Path(__file__).parent / "content"


@lru_cache(maxsize=None)
def _load_series_cached(series_id: str):
    f = CONTENT_DIR / series_id / "series.json"
    if not f.exists():
        return None
    series = json.loads(f.read_text(encoding="utf-8"))
    series["id"] = series_id
    return series


def load_series(series_id: str):
    # Return a copy so callers mutating the dict (e.g. setting series["id"])
    # can't corrupt the cached object shared across requests.
    series = _load_series_cached(series_id)
    return dict(series) if series is not None else None


@lru_cache(maxsize=1)
def _all_series_ids():
    out = []
    if CONTENT_DIR.exists():
        for d in sorted(CONTENT_DIR.iterdir()):
            if d.is_dir() and (d / "series.json").exists():
                out.append(d.name)
    return tuple(out)


def load_all_series():
    out = [load_series(sid) for sid in _all_series_ids()]
    out = [s for s in out if s is not None]
    # free series first, then by 'order' if provided
    out.sort(key=lambda s: (not s.get("free", False), s.get("order", 99)))
    return out


@lru_cache(maxsize=None)
def _load_lesson_cached(series_id: str, lesson_id: str):
    f = CONTENT_DIR / series_id / f"{lesson_id}.json"
    if not f.exists():
        return None
    lesson = json.loads(f.read_text(encoding="utf-8"))
    lesson["id"] = lesson_id
    return lesson


def load_lesson(series_id: str, lesson_id: str):
    lesson = _load_lesson_cached(series_id, lesson_id)
    return dict(lesson) if lesson is not None else None
