#!/usr/bin/env python3
"""
translate_series.py — LuzKids worldwide translation machine.

Usage:
    export GROQ_API_KEY=gsk_...          # same free key as ElisaVoz
    python tools/translate_series.py --lang fr
    python tools/translate_series.py --lang pt --series ephesians
    python tools/translate_series.py --lang fr --dry-run    # test without API calls

Design rules (do not break these):
  1. NEVER machine-translate Bible verses. Verse text comes from a real
     translation via the free getBible API; if unavailable, the verse is
     flagged [VERSE NEEDED] for manual paste from a licensed Bible.
  2. Build-time, not runtime: results are written into the lesson JSON.
  3. Free-tier friendly: throttled, retries on 429, saves after EVERY
     lesson — if you hit the daily token cap, rerun tomorrow; it resumes,
     skipping anything already translated.
  4. QA: a second model call judges each translation 0-10 against the
     English; low scores are retried once, then logged to review_flags.txt.
"""
import argparse, json, os, sys, time, urllib.request
from pathlib import Path

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"   # free tier compatible        # strong free-tier model on Groq
THROTTLE_SECONDS = 2.5                    # stay politely under free-tier RPM
JUDGE_THRESHOLD = 7                       # 0-10; below this -> retry/flag

# getBible (free, no key) translation codes per language for verse text.
# https://getbible.net — add languages here as you expand.
BIBLE_SOURCES = {
    "fr": "ls1910",       # Louis Segond 1910 (public domain)
    "pt": "almeida",      # Almeida Revista e Corrigida (public domain)
    "de": "luther1912",
    "it": "riveduta",
    "id": "tb",           # Terjemahan Baru
}

# Theological glossary: approved renderings the model MUST use.
GLOSSARY = {
    "fr": {"grace": "la grâce", "redemption": "la rédemption", "Holy Spirit": "le Saint-Esprit",
           "gospel": "l'Évangile", "salvation": "le salut", "faith": "la foi",
           "armour of God": "l'armure de Dieu", "church": "l'Église",
           "Lord": "le Seigneur", "memory verse": "verset à mémoriser"},
    "pt": {"grace": "a graça", "redemption": "a redenção", "Holy Spirit": "o Espírito Santo",
           "gospel": "o evangelho", "salvation": "a salvação", "faith": "a fé",
           "armour of God": "a armadura de Deus", "church": "a igreja",
           "Lord": "o Senhor", "memory verse": "versículo para memorizar"},
}
LANG_NAMES = {"fr": "French", "pt": "Portuguese", "de": "German", "it": "Italian", "id": "Indonesian"}

# --------------------------------------------------------------- Groq client
def groq_chat(messages, max_tokens=1200, retries=5):
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        sys.exit("Set GROQ_API_KEY first (same key as your ElisaVoz project).")
    from groq import Groq
    client = Groq(api_key=key)
    for attempt in range(retries):
        try:
            r = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.3,
                max_completion_tokens=max_tokens,
            )
            time.sleep(THROTTLE_SECONDS)
            return r.choices[0].message.content.strip()
        except Exception as e:
            err = str(e)
            if "429" in err or "rate" in err.lower():
                wait = min(60 * (attempt + 1), 300)
                print(f"   rate-limited; sleeping {wait}s "
                      f"(free tier — progress is saved, safe to Ctrl-C and resume)")
                time.sleep(wait)
            else:
                raise
    sys.exit("Repeated rate limits — daily free-tier cap likely reached. "
             "Progress is saved; rerun tomorrow to resume.")

def translate(text, lang, context):
    gloss = "\n".join(f'  "{k}" -> "{v}"' for k, v in GLOSSARY.get(lang, {}).items())
    sys_prompt = (
        f"You translate children's Bible study content from English to {LANG_NAMES[lang]}. "
        f"Audience: children aged 6-12 and their Christian parents. "
        f"Tone: warm, simple, joyful, read-aloud friendly. "
        f"Use these exact approved theological terms:\n{gloss}\n"
        f"Return ONLY the translation, no quotes, no commentary.")
    return groq_chat([{"role": "system", "content": sys_prompt},
                      {"role": "user", "content": f"Context: {context}\n\nTranslate:\n{text}"}])

def judge(english, translated, lang):
    prompt = (f"You are a strict bilingual theological editor. Score 0-10 how faithfully this "
              f"{LANG_NAMES[lang]} translation conveys the English for a children's Bible lesson "
              f"(meaning, doctrine, tone). Reply with ONLY the integer.\n\n"
              f"ENGLISH:\n{english}\n\n{LANG_NAMES[lang].upper()}:\n{translated}")
    reply = groq_chat([{"role": "user", "content": prompt}], max_tokens=5)
    digits = "".join(ch for ch in reply if ch.isdigit())
    return int(digits[:2]) if digits else 0

# --------------------------------------------------------------- verse fetch
BOOK_NUM = {"Ephesians": 49}   # getBible book numbers; extend per series

def fetch_verse(ref_en, lang):
    """ref like 'Ephesians 2:8' or 'Ephesians 1:3-6' -> real translated text or None."""
    src = BIBLE_SOURCES.get(lang)
    if not src:
        return None
    try:
        book, rest = ref_en.rsplit(" ", 1)
        chapter, verses = rest.split(":")
        v1 = verses.split("-")[0]; v2 = verses.split("-")[-1]
        url = (f"https://api.getbible.net/v2/{src}/{BOOK_NUM[book.strip()]}/"
               f"{chapter}.json")
        with urllib.request.urlopen(url, timeout=20) as r:
            data = json.load(r)
        wanted = range(int(v1), int(v2) + 1)
        text = " ".join(v["text"].strip() for v in data["verses"]
                        if v["verse"] in wanted)
        return text or None
    except Exception:
        return None

# --------------------------------------------------------------- main pass
def process_lesson(path, lang, dry):
    lesson = json.loads(path.read_text(encoding="utf-8"))
    changed, flags = False, []

    def need(d):                       # translate only missing strings (resume-safe)
        return isinstance(d, dict) and "en" in d and lang not in d

    def do(d, context):
        nonlocal changed
        if not need(d):
            return
        if dry:
            d[lang] = f"[{lang} pending]"; changed = True; return
        out = translate(d["en"], lang, context)
        score = judge(d["en"], out, lang)
        if score < JUDGE_THRESHOLD:
            out = translate(d["en"], lang, context + " (previous attempt scored low; be precise)")
            score = judge(d["en"], out, lang)
            if score < JUDGE_THRESHOLD:
                flags.append(f"{path.name} :: {context} :: score {score}")
        d[lang] = out; changed = True
        print(f"   ✓ {context} (QA {score}/10)")

    do(lesson["title"], "lesson title")
    for b in lesson["blocks"]:
        t = b["type"]
        if t == "story":
            do(b["heading"], "story heading"); do(b["body"], "story body (read-aloud narrative)")
        elif t == "memory_verse":
            if need(b["verse"]):
                ref = b["ref"]["en"].split("(")[0].strip()
                real = None if dry else fetch_verse(ref, lang)
                b["verse"][lang] = real or f"[VERSE NEEDED: {ref} — paste from a licensed {LANG_NAMES.get(lang, lang)} Bible]"
                b["ref"][lang] = ref + (" (LSG)" if lang == "fr" else " (ARC)" if lang == "pt" else "")
                if not real and not dry:
                    flags.append(f"{path.name} :: verse {ref} needs manual paste")
                changed = True
                print(f"   ✓ verse from real Bible translation" if real else f"   ⚠ verse flagged for manual paste")
            if need(b["scramble_words"]):
                # scramble derives from the real verse: first 6-8 words
                words = b["verse"].get(lang, "").replace("[VERSE NEEDED", "").split()
                b["scramble_words"][lang] = words[:7] if len(words) >= 5 else words
                changed = True
        elif t == "song":
            do(b["title"], "song title")
        elif t == "quiz":
            for i, q in enumerate(b["questions"]):
                do(q["q"], f"quiz question {i+1}")
                if isinstance(q["options"], dict) and lang not in q["options"]:
                    if dry:
                        q["options"][lang] = [f"[{lang}]"] * 4
                    else:
                        joined = " ||| ".join(q["options"]["en"])
                        out = translate(joined, lang, f"quiz options {i+1}, keep ||| separators, keep order")
                        opts = [o.strip() for o in out.split("|||")]
                        q["options"][lang] = opts if len(opts) == 4 else q["options"]["en"]
                        if len(opts) != 4:
                            flags.append(f"{path.name} :: quiz {i+1} options malformed")
                    changed = True
        elif t == "printable":
            for it in b["items"]: do(it["label"], "printable label")
        elif t == "parent_guide":
            do(b["body"], "parent/teacher guide (adult register)")

    if changed:
        path.write_text(json.dumps(lesson, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f" saved {path.name}")
    return flags

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", required=True, help="target language code, e.g. fr, pt")
    ap.add_argument("--series", default="ephesians")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.lang not in LANG_NAMES:
        sys.exit(f"Add '{args.lang}' to LANG_NAMES, GLOSSARY and BIBLE_SOURCES first.")
    root = Path(__file__).resolve().parent.parent / "content" / args.series
    lessons = sorted(root.glob("lesson*.json"))
    print(f"Translating {len(lessons)} lessons -> {LANG_NAMES[args.lang]} "
          f"({'DRY RUN' if args.dry_run else 'Groq free tier, throttled'})")

    all_flags = []
    for p in lessons:
        print(f"\n{p.name}")
        all_flags += process_lesson(p, args.lang, args.dry_run)

    # series metadata too
    sp = root / "series.json"
    series = json.loads(sp.read_text(encoding="utf-8"))
    for field in ("title", "subtitle", "description"):
        d = series[field]
        if args.lang not in d:
            d[args.lang] = (f"[{args.lang} pending]" if args.dry_run
                            else translate(d["en"], args.lang, f"series {field}"))
    for l in series["lessons"]:
        if args.lang not in l["title"]:
            l["title"][args.lang] = (f"[{args.lang} pending]" if args.dry_run
                                     else translate(l["title"]["en"], args.lang, "lesson title"))
    sp.write_text(json.dumps(series, ensure_ascii=False, indent=2), encoding="utf-8")

    if all_flags:
        Path("review_flags.txt").write_text("\n".join(all_flags))
        print(f"\n⚠ {len(all_flags)} items flagged -> review_flags.txt")
    print("\nDone. Remember to add the language to AI_LANGS in app.py to switch it on.")

if __name__ == "__main__":
    main()
