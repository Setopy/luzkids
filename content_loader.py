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
from pathlib import Path

CONTENT_DIR = Path(__file__).parent / "content"


def load_series(series_id: str):
    f = CONTENT_DIR / series_id / "series.json"
    if not f.exists():
        return None
    series = json.loads(f.read_text(encoding="utf-8"))
    series["id"] = series_id
    return series


def load_all_series():
    out = []
    if CONTENT_DIR.exists():
        for d in sorted(CONTENT_DIR.iterdir()):
            if d.is_dir() and (d / "series.json").exists():
                out.append(load_series(d.name))
    # free series first, then by 'order' if provided
    out.sort(key=lambda s: (not s.get("free", False), s.get("order", 99)))
    return out


def load_lesson(series_id: str, lesson_id: str):
    f = CONTENT_DIR / series_id / f"{lesson_id}.json"
    if not f.exists():
        return None
    lesson = json.loads(f.read_text(encoding="utf-8"))
    lesson["id"] = lesson_id
    return lesson
