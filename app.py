"""
LuzKids — interactive Bible studies for children.
"Let your light shine before others" — Matthew 5:16
"Que brille la luz de ustedes delante de todos" — Mateo 5:16

A static site. Flask is used only to render the pages: `python build.py`
writes every page, in every language, to dist/ for Cloudflare Pages, and
`python app.py` runs the same pages locally for development. There is no
database and nothing about children is stored anywhere but the family's
own device (static/js/progress.js).
"""
import os

from flask import Flask, render_template, redirect, url_for, request, abort, g, jsonify

from content_loader import load_all_series, load_series, load_lesson, load_songs

# ---------------------------------------------------------------- app setup
app = Flask(__name__)

FEEDBACK_EMAIL = "aielitazit@gmail.com"

# Verified languages are human-reviewed; AI languages are machine-translated
# (translate_series.py) and badged as such in the UI.
VERIFIED_LANGS = {"en": "English", "es": "Español"}
AI_LANGS = {"fr": "Français", "pt": "Português", "th": "ไทย"}   # shown with a "beta" tag + feedback banner
LANGUAGES = {**VERIFIED_LANGS, **AI_LANGS}
SUPPORTED_LANGS = tuple(LANGUAGES.keys())

RANKS = [
    (0,    "Seeker",           "🔍"),
    (100,  "Believer",         "✝️"),
    (300,  "Growing",          "🌱"),
    (600,  "Sanctified",       "✨"),
    (1000, "Spirit-Filled",    "🔥"),
    (1500, "Arrow in Training","🏹"),
    (2200, "Jesus\' Arrow",     "⚡"),
    (3000, "Arrow of Light",   "🕯️"),
    (4000, "Sent Arrow",       "🌍"),
]

def get_rank(xp):
    r = RANKS[0]
    for threshold, name, emoji in RANKS:
        if xp >= threshold:
            r = (threshold, name, emoji)
    return r

def xp_for_lesson(quiz_score, total_q):
    base = 50
    if quiz_score is not None and total_q > 0 and quiz_score == total_q:
        base += 25   # perfect quiz bonus
    return base

app.jinja_env.globals.update(get_rank=get_rank, RANKS=RANKS)
BADGES = {
    "first_lamp":    {"name": "First Lamp",         "emoji": "🕯️",  "desc": {"en": "Complete your first lesson", "th": "จบบทเรียนแรกของคุณ",           "es": "Completa tu primera lección",            "fr": "Complète ta première leçon"}},
    "word_seeker":   {"name": "Word Seeker",         "emoji": "📖",  "desc": {"en": "Complete 5 lessons", "th": "จบบทเรียน 5 บท",                   "es": "Completa 5 lecciones",                   "fr": "Complète 5 leçons"}},
    "explorer":      {"name": "Scripture Explorer",  "emoji": "🗺️",  "desc": {"en": "Complete 10 lessons", "th": "จบบทเรียน 10 บท",                  "es": "Completa 10 lecciones",                  "fr": "Complète 10 leçons"}},
    "on_fire":       {"name": "On Fire!",            "emoji": "🔥",  "desc": {"en": "Keep a 3-day streak", "th": "รักษาสถิติต่อเนื่อง 3 วัน",                  "es": "Mantén un racha de 3 días",              "fr": "Garde une série de 3 jours"}},
    "ablaze":        {"name": "Ablaze",              "emoji": "🔥🔥","desc": {"en": "Keep a 7-day streak", "th": "รักษาสถิติต่อเนื่อง 7 วัน",                  "es": "Mantén una racha de 7 días",             "fr": "Garde une série de 7 jours"}},
    "quiz_hero":     {"name": "Quiz Hero",           "emoji": "⭐",  "desc": {"en": "Score 100% on a quiz", "th": "ทำแบบทดสอบได้ 100%",                 "es": "Obtén 100% en un quiz",                  "fr": "Obtiens 100% à un quiz"}},
    "word_perfect":  {"name": "Word Perfect",        "emoji": "⌨️",  "desc": {"en": "Type a memory verse perfectly", "th": "พิมพ์ข้อพระคัมภีร์ท่องจำได้ถูกต้องครบถ้วน",        "es": "Escribe un versículo de memoria perfecto","fr": "Tape un verset de mémoire parfaitement"}},
    "soul_winner":   {"name": "Soul Winner",         "emoji": "🌍",  "desc": {"en": "Add your first prayer target", "th": "เพิ่มคนแรกที่คุณจะอธิษฐานเผื่อ",         "es": "Agrega tu primer objetivo de oración",   "fr": "Ajoute ta première cible de prière"}},
    "graduate":      {"name": "Graduate",            "emoji": "🎓",  "desc": {"en": "Complete an entire series", "th": "จบชุดเรียนทั้งชุด",            "es": "Completa una serie completa",            "fr": "Complète une série entière"}},
    "jesus_arrow":   {"name": "Jesus\' Arrow",       "emoji": "🏹",  "desc": {"en": "Reach Jesus\' Arrow rank", "th": "ไปถึงระดับลูกศรของพระเยซู",            "es": "Alcanza el rango Flecha de Jesús",       "fr": "Atteins le rang Flèche de Jésus"}},
    "trilingual":    {"name": "Trilingual",          "emoji": "🌐",  "desc": {"en": "Study in 2+ languages", "th": "เรียนได้มากกว่า 2 ภาษา",               "es": "Estudia en 2+ idiomas",                  "fr": "Étudie dans 2+ langues"}},
    "certified":     {"name": "Certified!",          "emoji": "📜",  "desc": {"en": "Earn your first certificate", "th": "รับประกาศนียบัตรแรกของคุณ",          "es": "Gana tu primer certificado",             "fr": "Gagne ton premier certificat"}},
}
app.jinja_env.globals["BADGES"] = BADGES


# ---------------------------------------------------------------- helpers
def get_lang():
    """The language comes from the address: /en/..., /es/..., and so on."""
    lang = g.get("lang")
    if lang in SUPPORTED_LANGS:
        return lang
    return request.accept_languages.best_match(SUPPORTED_LANGS) or "en"


def lang_url(code):
    """The current page's address in another language."""
    path = request.path
    prefix = "/" + g.get("lang", "")
    rest = path[len(prefix):] if g.get("lang") and path.startswith(prefix) else "/"
    return "/" + code + (rest or "/")


@app.url_value_preprocessor
def pull_lang(endpoint, values):
    if values and "lang" in values:
        g.lang = values.pop("lang")
        if g.lang not in SUPPORTED_LANGS:
            abort(404)


@app.url_defaults
def add_lang(endpoint, values):
    if "lang" not in values and app.url_map.is_endpoint_expecting(endpoint, "lang"):
        values["lang"] = get_lang()


def t(field):
    """Pick the right language from a bilingual {'en':..,'es':..} dict."""
    if isinstance(field, dict):
        lang = get_lang()
        return field.get(lang) or field.get("en") or next(iter(field.values()), "")
    return field


def series_access_allowed(series):
    """Everything on LuzKids is free."""
    return True


import markupsafe

@app.template_filter('paragraphs')
def paragraphs_filter(text):
    """Render \n\n-separated text as proper <p> blocks."""
    if not text:
        return markupsafe.Markup("")
    paras = [p.strip() for p in str(text).split("\n\n") if p.strip()]
    return markupsafe.Markup("".join(
        f'<p class="content-p">{markupsafe.escape(p)}</p>' for p in paras
    ))

app.jinja_env.globals.update(t=t, get_lang=get_lang, lang_url=lang_url, FEEDBACK_EMAIL=FEEDBACK_EMAIL,
                             series_access_allowed=series_access_allowed,
                             LANGUAGES=LANGUAGES, AI_LANGS=AI_LANGS)

UI = {  # small UI string table — content strings live in the JSON, not here
    "tagline": {"en": "Interactive Bible studies that light up Scripture for kids", "th": "พระคัมภีร์ศึกษาแบบอินเทอร์แอกทีฟที่ทำให้พระวจนะสว่างไสวสำหรับเด็ก",
                "es": "Estudios bíblicos interactivos que iluminan la Escritura para niños"},
    "library": {"en": "Study library", "th": "คลังบทเรียน", "es": "Biblioteca de estudios"},
    "start": {"en": "Start lesson", "th": "เริ่มบทเรียน", "es": "Comenzar lección"},
    "locked": {"en": "Family plan", "th": "แพ็กเกจครอบครัว", "es": "Plan familiar"},
    "free": {"en": "Free", "th": "ฟรี", "es": "Gratis"},
    "who_learning": {"en": "Who is learning today?", "th": "ใครจะเรียนวันนี้?", "es": "¿Quién aprende hoy?"},
    "parent_guide": {"en": "Parent & teacher guide", "th": "คู่มือสำหรับผู้ปกครองและครู", "es": "Guía para padres y maestros"},
    "memory_verse": {"en": "Memory verse", "th": "ข้อพระคัมภีร์ท่องจำ", "es": "Versículo para memorizar"},
    "quiz": {"en": "Quiz time!", "th": "ถึงเวลาทำแบบทดสอบ!", "es": "¡Hora del quiz!"},
    "song": {"en": "Sing along", "th": "ร้องตาม", "es": "Canta conmigo"},
    "complete": {"en": "I finished this lesson!", "th": "ฉันเรียนบทนี้จบแล้ว!", "es": "¡Terminé esta lección!"},
    "printables": {"en": "Printables", "th": "ใบงานพิมพ์", "es": "Imprimibles"},
}
app.jinja_env.globals["UI"] = UI

# Strings used by the on-device progress code (static/js/progress.js).
CLIENT_STRINGS = {
    "choose_child": {"en": "Choose child", "es": "Elegir niño", "fr": "Choisir l'enfant", "th": "เลือกเด็ก"},
    "who_learning": UI["who_learning"],
    "complete": UI["complete"],
    "lamp_lit": {"en": "Lamp lit! Well done,", "es": "¡Lámpara encendida! Bien hecho,", "fr": "Lampe allumée ! Bravo,", "th": "จุดตะเกียงแล้ว! เยี่ยมมาก"},
    "day_streak": {"en": "day streak", "es": "días seguidos", "fr": "jours de suite", "th": "วันต่อเนื่อง"},
    "new_rank": {"en": "New rank:", "es": "Nuevo rango:", "fr": "Nouveau rang :", "th": "ระดับใหม่:"},
    "new_badge": {"en": "New badge:", "es": "Nueva insignia:", "fr": "Nouveau badge :", "th": "เหรียญใหม่:"},
    "total": {"en": "Total", "es": "Total", "fr": "Total", "th": "รวม"},
    "lesson_cert": {"en": "Lesson certificate", "es": "Certificado de lección", "fr": "Certificat de leçon", "th": "ประกาศนียบัตรบทเรียน"},
    "series_cert": {"en": "SERIES certificate!", "es": "¡Certificado de SERIE!", "fr": "Certificat de SÉRIE !", "th": "ประกาศนียบัตรชุดเรียน!"},
    "pick_child_first": {"en": "Choose who is learning to light lamps and earn stars.", "es": "Elige quién aprende para encender lámparas y ganar estrellas.", "fr": "Choisis qui apprend pour allumer des lampes et gagner des étoiles.", "th": "เลือกว่าใครกำลังเรียนเพื่อจุดตะเกียงและสะสมดาว"},
    "name_ph": {"en": "Nickname (no full names)", "es": "Apodo (sin nombre completo)", "fr": "Surnom (pas de nom complet)", "th": "ชื่อเล่น (ไม่ใช้ชื่อจริงเต็ม)"},
    "add_child": {"en": "Add child", "es": "Agregar niño", "fr": "Ajouter un enfant", "th": "เพิ่มเด็ก"},
    "remove": {"en": "Remove", "es": "Quitar", "fr": "Retirer", "th": "ลบ"},
    "confirm_remove": {"en": "Remove this profile and all its progress from this device?", "es": "¿Quitar este perfil y todo su progreso de este dispositivo?", "fr": "Retirer ce profil et toute sa progression de cet appareil ?", "th": "ลบโปรไฟล์นี้และความคืบหน้าทั้งหมดออกจากอุปกรณ์นี้หรือไม่?"},
    "learning_now": {"en": "Learning now", "es": "Aprendiendo ahora", "fr": "Apprend maintenant", "th": "กำลังเรียนอยู่"},
    "select": {"en": "Choose", "es": "Elegir", "fr": "Choisir", "th": "เลือก"},
    "saved_file": {"en": "Progress file saved.", "es": "Archivo de progreso guardado.", "fr": "Fichier de progression enregistré.", "th": "บันทึกไฟล์ความคืบหน้าแล้ว"},
    "loaded_file": {"en": "Progress loaded onto this device.", "es": "Progreso cargado en este dispositivo.", "fr": "Progression chargée sur cet appareil.", "th": "โหลดความคืบหน้าลงอุปกรณ์นี้แล้ว"},
    "bad_file": {"en": "That file isn't a LuzKids progress file.", "es": "Ese archivo no es un archivo de progreso de LuzKids.", "fr": "Ce fichier n'est pas un fichier de progression LuzKids.", "th": "ไฟล์นี้ไม่ใช่ไฟล์ความคืบหน้าของ LuzKids"},
    "confirm_load": {"en": "Replace the progress on this device with the file?", "es": "¿Reemplazar el progreso de este dispositivo con el archivo?", "fr": "Remplacer la progression de cet appareil par le fichier ?", "th": "แทนที่ความคืบหน้าบนอุปกรณ์นี้ด้วยไฟล์หรือไม่?"},
    "no_profiles": {"en": "No profiles on this device yet.", "es": "Aún no hay perfiles en este dispositivo.", "fr": "Aucun profil sur cet appareil pour l'instant.", "th": "ยังไม่มีโปรไฟล์บนอุปกรณ์นี้"},
    "complete_word": {"en": "Complete!", "es": "¡Completa!", "fr": "Terminée !", "th": "เสร็จสมบูรณ์!"},
    "certificate": {"en": "Certificate", "es": "Certificado", "fr": "Certificat", "th": "ประกาศนียบัตร"},
    "xp_to": {"en": "XP to", "es": "XP para", "fr": "XP pour", "th": "XP ถึง"},
    "prayed": {"en": "Prayed today", "es": "Oré hoy", "fr": "Prié aujourd'hui", "th": "อธิษฐานวันนี้แล้ว"},
    "shared": {"en": "Shared the gospel", "es": "Compartí el evangelio", "fr": "Partagé l'évangile", "th": "แบ่งปันข่าวประเสริฐแล้ว"},
    "responded": {"en": "Responded!", "es": "¡Respondió!", "fr": "A répondu !", "th": "ตอบรับแล้ว!"},
    "cert_title": {"en": "Certificate of Completion", "es": "Certificado de Finalización", "fr": "Certificat de Réussite", "th": "ประกาศนียบัตรแห่งความสำเร็จ"},
    "cert_awarded": {"en": "This certificate is proudly awarded to", "es": "Este certificado se otorga con orgullo a", "fr": "Ce certificat est fièrement décerné à", "th": "ประกาศนียบัตรนี้มอบให้แก่"},
    "cert_for_lesson": {"en": "for completing the lesson", "es": "por completar la lección", "fr": "pour avoir terminé la leçon", "th": "สำหรับการเรียนจบบทเรียน"},
    "cert_for_series": {"en": "for completing every lesson in the series", "es": "por completar todas las lecciones de la serie", "fr": "pour avoir terminé toutes les leçons de la série", "th": "สำหรับการเรียนจบทุกบทเรียนในชุด"},
    "cert_not_done": {"en": "This certificate unlocks when the lesson or series is finished on this device.", "es": "Este certificado se desbloquea al terminar la lección o la serie en este dispositivo.", "fr": "Ce certificat se débloque une fois la leçon ou la série terminée sur cet appareil.", "th": "ประกาศนียบัตรนี้จะปลดล็อกเมื่อเรียนจบบทเรียนหรือชุดเรียนบนอุปกรณ์นี้"},
    "print": {"en": "Print or save as PDF", "es": "Imprimir o guardar como PDF", "fr": "Imprimer ou enregistrer en PDF", "th": "พิมพ์หรือบันทึกเป็น PDF"},
}


def client_data():
    """Everything progress.js needs, already in the visitor's language.
    Contains no personal data: only ranks, badges and interface text."""
    return {
        "lang": get_lang(),
        "base": "/" + get_lang(),
        "ranks": [[th, name, emoji] for th, name, emoji in RANKS],
        "badges": {bid: {"name": b["name"], "emoji": b["emoji"], "desc": t(b["desc"])}
                   for bid, b in BADGES.items()},
        "s": {k: t(v) for k, v in CLIENT_STRINGS.items()},
    }


app.jinja_env.globals["client_data"] = client_data


# ---------------------------------------------------------------- routes
# Every page lives under a language prefix (/en/, /es/, ...) so it can be
# pre-built as a plain file. Addresses end in "/" to match the built files.
@app.route("/")
def root():
    """Local development only; on the static site, dist/index.html picks
    the language in the browser."""
    return redirect(url_for("index", lang=get_lang()))


@app.route("/<lang>/")
def index():
    series_list = load_all_series()
    stats = {
        "languages": len(LANGUAGES),
        "free_lessons": sum(len(s["lessons"]) for s in series_list if s.get("free")),
    }
    return render_template("index.html", series_list=series_list, stats=stats)


@app.route("/<lang>/library/")
def library():
    return render_template("library.html", series_list=load_all_series())


@app.route("/<lang>/songs/")
def songs():
    return render_template("songs.html", songs=load_songs())


@app.route("/<lang>/series/<series_id>/")
def series_page(series_id):
    series = load_series(series_id) or abort(404)
    # Which lessons are done is marked in the browser from on-device data.
    return render_template("series.html", series=series)


@app.route("/<lang>/series/<series_id>/<lesson_id>/")
def lesson_page(series_id, lesson_id):
    series = load_series(series_id) or abort(404)
    lesson = load_lesson(series_id, lesson_id) or abort(404)
    total_q = 0
    for b in lesson.get("blocks", []):
        if b.get("type") == "quiz":
            total_q = len(b.get("questions", []))
    return render_template("lesson.html", series=series, lesson=lesson, total_q=total_q)


# ----------------------------------------------------- on-device pages
# These pages are shells: everything about a child is read from and
# written to the browser's own storage by static/js/progress.js. The
# server never receives a child's name, progress or Mission log.
def series_catalog():
    """Public lesson catalogue (titles and ids only) for on-device pages."""
    return [{"id": s["id"], "emoji": s.get("emoji", ""), "title": t(s["title"]),
             "lessons": [{"id": l["id"], "title": t(l["title"])} for l in s["lessons"]]}
            for s in load_all_series()]


@app.route("/<lang>/profiles/")
def profiles():
    return render_template("profiles.html")


@app.route("/<lang>/progress/")
def progress_page():
    return render_template("progress.html", catalog=series_catalog())


@app.route("/<lang>/mission/")
def mission():
    return render_template("mission.html")


@app.route("/<lang>/certificate/")
def certificate():
    return render_template("certificate.html", catalog=series_catalog())


@app.route("/<lang>/privacy/")
def privacy():
    return render_template("privacy.html")


# ----------------------------------------------------- PWA
def manifest_data():
    return {
        "name": "LuzKids — Jesus' Arrows",
        "short_name": "LuzKids",
        "description": "Interactive Bible studies for children, in every language",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#1e2547",
        "theme_color": "#f6ab3a",
        "orientation": "portrait-primary",
        "categories": ["education", "lifestyle"],
        "icons": [
            {"src": f"/static/icons/icon-{s}x{s}.png",
             "sizes": f"{s}x{s}", "type": "image/png",
             "purpose": "any maskable"}
            for s in [72, 96, 128, 144, 152, 192, 384, 512]
        ]
    }


@app.route("/manifest.json")
def pwa_manifest():
    return jsonify(manifest_data())


@app.route("/sw.js")
def service_worker():
    from flask import send_from_directory
    return send_from_directory("static", "sw.js", mimetype="application/javascript")


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=int(os.environ.get("PORT", 5000)))
