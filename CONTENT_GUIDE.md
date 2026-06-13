# LuzKids Content Guide
### How to add a new study series in an evening — no code changes

This is the heart of the platform. The app is finished; growth comes from
content. Every new series is just a folder of JSON files.

---

## 1. Create the folder

```
content/
  philippians/          <- series id: lowercase, no spaces
    series.json
    lesson01.json
    lesson02.json
    ...
```

Commit, push, Railway redeploys. The series appears in the library
automatically. That's the whole pipeline.

## 2. The golden rule: everything bilingual

Every human-readable string is a dict with both languages:

```json
{"en": "Chosen and Loved", "es": "Escogidos y Amados"}
```

Write the English and Spanish **together**, not as an afterthought. If one
language is missing the app falls back to English, but don't rely on this
in published content.

## 3. series.json template

```json
{
  "title":       {"en": "", "es": ""},
  "subtitle":    {"en": "", "es": ""},
  "description": {"en": "", "es": ""},
  "age_range": "6-12",
  "free": false,
  "order": 2,
  "emoji": "🕊️",
  "color": "#4F9D69",
  "lessons": [
    {"id": "lesson01", "title": {"en": "", "es": ""}, "ref": "Philippians 1:1-11"}
  ]
}
```

- `free: true` puts it in the free tier — keep exactly ONE flagship series free.
- `color` is the card accent; pick from the palette: gold `#F4A938`,
  meadow `#4F9D69`, sky `#5B7BD5`, berry `#B05478`.

## 4. Lesson blocks — mix and match, in any order

A lesson is `{"title": .., "ref": .., "blocks": [..]}`. Available block types:

**story** — the narrative retelling (aim for 120–180 words per language;
read it aloud — if it doesn't sound like you telling it to your own
children, rewrite it):
```json
{"type": "story", "heading": {"en":"","es":""}, "body": {"en":"","es":""}}
```

**memory_verse** — verse + tap-to-order scramble game. Keep
`scramble_words` to 6–9 words (the key phrase, not the whole verse):
```json
{"type": "memory_verse",
 "verse": {"en":"","es":""}, "ref": {"en":"","es":""},
 "scramble_words": {"en": ["..."], "es": ["..."]}}
```

**song** — your Suno tracks. Drop MP3s into `static/audio/<series>/`:
```json
{"type": "song", "title": {"en":"","es":""},
 "audio_en": "/static/audio/philippians/lesson01_en.mp3",
 "audio_es": "/static/audio/philippians/lesson01_es.mp3"}
```

**quiz** — 3–5 questions, 4 options each, `answer` is the 0-based index:
```json
{"type": "quiz", "questions": [
  {"q": {"en":"","es":""},
   "options": {"en": ["","","",""], "es": ["","","",""]},
   "answer": 0}
]}
```

**printable** — colouring/activity PDFs in `static/printables/<series>/`:
```json
{"type": "printable", "items": [
  {"label": {"en":"","es":""}, "file": "/static/printables/..."}]}
```

**parent_guide** — big idea + 3 conversation starters + a prayer prompt.
This block is what churches pay for; never skip it:
```json
{"type": "parent_guide", "body": {"en":"","es":""}}
```

## 5. A repeatable lesson recipe

Every lesson should follow the same rhythm so children know what to expect:

1. `story` — hook + retelling
2. `memory_verse` — with scramble game
3. `song` — Suno track
4. `quiz` — 3 questions
5. `printable` — one sheet
6. `parent_guide` — always last

## 6. Doctrinal review checklist (before publishing any lesson)

- [ ] Verse quoted accurately in both translations (NIV / NVI or your preferred pair)
- [ ] The "big idea" is what the passage teaches, not a moral bolted on
- [ ] Age-appropriate: no fear-based framing for under-12s
- [ ] Spanish reviewed by a native speaker (Adebimpe or church volunteer)
- [ ] Song lyrics checked against the verse text
- [ ] Suno commercial licence confirmed for any track included

## 7. Production order suggestion

1. **Ephesians** (8 lessons, FREE flagship) — mostly written already
2. **Salmos para Pequeños** (Spanish-first, 6 lessons) — signals genuine bilinguality
3. **The Armour of God deep-dive** (6 lessons) — natural upsell from Ephesians L8
4. **Christmas: The Light Has Come** (4 lessons) — ready before December
