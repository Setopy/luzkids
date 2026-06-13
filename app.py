"""
LuzKids — bilingual interactive Bible studies for children.
"Let your light shine before others" — Matthew 5:16
"Que brille la luz de ustedes delante de todos" — Mateo 5:16

Flask MVP. Deliberately boring technology: the value is the content.
Deploy target: Railway (same stack as ElisaVoz).
"""
import os
from datetime import datetime
from functools import wraps

from flask import (Flask, render_template, redirect, url_for, request,
                   session, flash, jsonify, abort)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from werkzeug.security import generate_password_hash, check_password_hash

from content_loader import load_all_series, load_series, load_lesson

# ---------------------------------------------------------------- app setup
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///luzkids.db").replace("postgres://", "postgresql://")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# Verified languages are human-reviewed; AI languages are machine-translated
# (translate_series.py) and badged as such in the UI.
VERIFIED_LANGS = {"en": "English", "es": "Español"}
AI_LANGS = {"fr": "Français", "pt": "Português"}   # shown with a "beta" tag + feedback banner
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
    "first_lamp":    {"name": "First Lamp",         "emoji": "🕯️",  "desc": {"en": "Complete your first lesson",           "es": "Completa tu primera lección",            "fr": "Complète ta première leçon"}},
    "word_seeker":   {"name": "Word Seeker",         "emoji": "📖",  "desc": {"en": "Complete 5 lessons",                   "es": "Completa 5 lecciones",                   "fr": "Complète 5 leçons"}},
    "explorer":      {"name": "Scripture Explorer",  "emoji": "🗺️",  "desc": {"en": "Complete 10 lessons",                  "es": "Completa 10 lecciones",                  "fr": "Complète 10 leçons"}},
    "on_fire":       {"name": "On Fire!",            "emoji": "🔥",  "desc": {"en": "Keep a 3-day streak",                  "es": "Mantén un racha de 3 días",              "fr": "Garde une série de 3 jours"}},
    "ablaze":        {"name": "Ablaze",              "emoji": "🔥🔥","desc": {"en": "Keep a 7-day streak",                  "es": "Mantén una racha de 7 días",             "fr": "Garde une série de 7 jours"}},
    "quiz_hero":     {"name": "Quiz Hero",           "emoji": "⭐",  "desc": {"en": "Score 100% on a quiz",                 "es": "Obtén 100% en un quiz",                  "fr": "Obtiens 100% à un quiz"}},
    "word_perfect":  {"name": "Word Perfect",        "emoji": "⌨️",  "desc": {"en": "Type a memory verse perfectly",        "es": "Escribe un versículo de memoria perfecto","fr": "Tape un verset de mémoire parfaitement"}},
    "soul_winner":   {"name": "Soul Winner",         "emoji": "🌍",  "desc": {"en": "Add your first prayer target",         "es": "Agrega tu primer objetivo de oración",   "fr": "Ajoute ta première cible de prière"}},
    "graduate":      {"name": "Graduate",            "emoji": "🎓",  "desc": {"en": "Complete an entire series",            "es": "Completa una serie completa",            "fr": "Complète une série entière"}},
    "jesus_arrow":   {"name": "Jesus\' Arrow",       "emoji": "🏹",  "desc": {"en": "Reach Jesus\' Arrow rank",            "es": "Alcanza el rango Flecha de Jesús",       "fr": "Atteins le rang Flèche de Jésus"}},
    "trilingual":    {"name": "Trilingual",          "emoji": "🌐",  "desc": {"en": "Study in 2+ languages",               "es": "Estudia en 2+ idiomas",                  "fr": "Étudie dans 2+ langues"}},
    "certified":     {"name": "Certified!",          "emoji": "📜",  "desc": {"en": "Earn your first certificate",          "es": "Gana tu primer certificado",             "fr": "Gagne ton premier certificat"}},
}
app.jinja_env.globals["BADGES"] = BADGES


def award_badge(child, badge_id):
    """Award a badge if not already earned. Returns True if new."""
    if Badge.query.filter_by(child_id=child.id, badge_id=badge_id).first():
        return False
    db.session.add(Badge(child_id=child.id, badge_id=badge_id))
    return True


def check_badges(child, series_id=None, quiz_score=None, total_q=None):
    """Check and award all applicable badges. Returns list of new badge_ids."""
    new_badges = []
    done_count = Progress.query.filter_by(child_id=child.id, completed=True).count()
    if done_count >= 1  and award_badge(child, "first_lamp"):   new_badges.append("first_lamp")
    if done_count >= 5  and award_badge(child, "word_seeker"):  new_badges.append("word_seeker")
    if done_count >= 10 and award_badge(child, "explorer"):     new_badges.append("explorer")
    if (child.streak or 0) >= 3 and award_badge(child, "on_fire"):  new_badges.append("on_fire")
    if (child.streak or 0) >= 7 and award_badge(child, "ablaze"):   new_badges.append("ablaze")
    if quiz_score is not None and total_q and quiz_score == total_q and award_badge(child, "quiz_hero"):
        new_badges.append("quiz_hero")
    if series_id:
        series = load_series(series_id)
        if series:
            total = len(series["lessons"])
            done  = Progress.query.filter_by(child_id=child.id, series_id=series_id, completed=True).count()
            if done >= total and award_badge(child, "graduate"): new_badges.append("graduate")
    _, rank_name, _ = get_rank(child.xp or 0)
    if rank_name == "Jesus' Arrow" and award_badge(child, "jesus_arrow"): new_badges.append("jesus_arrow")
    # certified badge triggered from cert route
    return new_badges



# ---------------------------------------------------------------- models
class User(UserMixin, db.Model):
    """A parent / teacher account. Children are profiles, not accounts."""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(80), nullable=False)
    plan = db.Column(db.String(20), default="free")   # free | family | church
    lang = db.Column(db.String(5), default="en")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    children = db.relationship("ChildProfile", backref="owner", lazy=True,
                               cascade="all, delete-orphan")

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    @property
    def max_children(self):
        return 10   # everything is free — generous fixed limit


class ChildProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.String(60), nullable=False)
    avatar = db.Column(db.String(10), default="🌟")  # emoji avatar, kid-pickable
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    xp = db.Column(db.Integer, default=0)
    streak = db.Column(db.Integer, default=0)
    longest_streak = db.Column(db.Integer, default=0)
    last_active = db.Column(db.Date)
    progress = db.relationship("Progress", backref="child", lazy=True,
                               cascade="all, delete-orphan")


class Badge(db.Model):
    """One-time achievement badges earned by a child."""
    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey("child_profile.id"), nullable=False)
    badge_id = db.Column(db.String(40), nullable=False)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint("child_id", "badge_id"),)

class MissionTarget(db.Model):
    """Soul winner tracker — personal evangelism log per child."""
    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey("child_profile.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    prayed_today = db.Column(db.Boolean, default=False)
    shared_gospel = db.Column(db.Boolean, default=False)
    responded = db.Column(db.Boolean, default=False)
    notes = db.Column(db.String(300))

class Progress(db.Model):
    """One row per (child, series, lesson). Completed lessons light a lamp."""
    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey("child_profile.id"),
                         nullable=False)
    series_id = db.Column(db.String(60), nullable=False)
    lesson_id = db.Column(db.String(60), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    quiz_score = db.Column(db.Integer)          # out of quiz length
    completed_at = db.Column(db.DateTime)
    __table_args__ = (db.UniqueConstraint("child_id", "series_id", "lesson_id"),)


class Feedback(db.Model):
    """Visitor reports — the QA system for unreviewed languages (and everything else)."""
    id = db.Column(db.Integer, primary_key=True)
    page = db.Column(db.String(200))
    lang = db.Column(db.String(5))
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ---------------------------------------------------------------- helpers
def get_lang():
    """Language priority: session toggle > account setting > browser > en."""
    if "lang" in session:
        return session["lang"]
    if current_user.is_authenticated and current_user.lang in SUPPORTED_LANGS:
        return current_user.lang
    return request.accept_languages.best_match(SUPPORTED_LANGS) or "en"


def t(field):
    """Pick the right language from a bilingual {'en':..,'es':..} dict."""
    if isinstance(field, dict):
        lang = get_lang()
        return field.get(lang) or field.get("en") or next(iter(field.values()), "")
    return field


def active_child():
    """The child profile currently 'signed in' on this device."""
    cid = session.get("active_child_id")
    if cid and current_user.is_authenticated:
        child = db.session.get(ChildProfile, cid)
        if child and child.user_id == current_user.id:
            return child
    return None


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

app.jinja_env.globals.update(t=t, get_lang=get_lang, active_child=active_child,
                             series_access_allowed=series_access_allowed,
                             LANGUAGES=LANGUAGES, AI_LANGS=AI_LANGS)

UI = {  # small UI string table — content strings live in the JSON, not here
    "tagline": {"en": "Interactive Bible studies that light up Scripture for kids",
                "es": "Estudios bíblicos interactivos que iluminan la Escritura para niños"},
    "library": {"en": "Study library", "es": "Biblioteca de estudios"},
    "start": {"en": "Start lesson", "es": "Comenzar lección"},
    "locked": {"en": "Family plan", "es": "Plan familiar"},
    "free": {"en": "Free", "es": "Gratis"},
    "who_learning": {"en": "Who is learning today?", "es": "¿Quién aprende hoy?"},
    "parent_guide": {"en": "Parent & teacher guide", "es": "Guía para padres y maestros"},
    "memory_verse": {"en": "Memory verse", "es": "Versículo para memorizar"},
    "quiz": {"en": "Quiz time!", "es": "¡Hora del quiz!"},
    "song": {"en": "Sing along", "es": "Canta conmigo"},
    "complete": {"en": "I finished this lesson!", "es": "¡Terminé esta lección!"},
    "printables": {"en": "Printables", "es": "Imprimibles"},
}
app.jinja_env.globals["UI"] = UI


# ---------------------------------------------------------------- routes
@app.route("/lang/<lang>")
def set_lang(lang):
    if lang in SUPPORTED_LANGS:
        session["lang"] = lang
        if current_user.is_authenticated:
            current_user.lang = lang
            db.session.commit()
    return redirect(request.referrer or url_for("index"))


@app.route("/")
def index():
    series_list = load_all_series()
    stats = {
        "languages": len(LANGUAGES),
        "free_lessons": sum(len(s["lessons"]) for s in series_list if s.get("free")),
    }
    return render_template("index.html", series_list=series_list, stats=stats)


@app.route("/library")
def library():
    return render_template("library.html", series_list=load_all_series())


@app.route("/series/<series_id>")
def series_page(series_id):
    series = load_series(series_id) or abort(404)
    done = set()
    child = active_child()
    if child:
        done = {p.lesson_id for p in Progress.query.filter_by(
            child_id=child.id, series_id=series_id, completed=True)}
    return render_template("series.html", series=series, done=done)


@app.route("/series/<series_id>/<lesson_id>")
def lesson_page(series_id, lesson_id):
    series = load_series(series_id) or abort(404)
    lesson = load_lesson(series_id, lesson_id) or abort(404)
    return render_template("lesson.html", series=series, lesson=lesson)


@app.route("/api/complete", methods=["POST"])
@login_required
def api_complete():
    from datetime import date as _date
    child = active_child()
    if not child:
        return jsonify(error="no_active_child"), 400
    data = request.get_json(force=True)
    row = Progress.query.filter_by(child_id=child.id,
                                   series_id=data["series_id"],
                                   lesson_id=data["lesson_id"]).first()
    already_done = row and row.completed
    total_q = 0  # defined here so always in scope
    if not row:
        row = Progress(child_id=child.id, series_id=data["series_id"],
                       lesson_id=data["lesson_id"])
        db.session.add(row)
    row.completed = True
    row.quiz_score = data.get("quiz_score")
    row.completed_at = datetime.utcnow()

    rank_up = False
    xp_earned = 0
    if not already_done:
        # XP
        series = load_series(data["series_id"])
        total_q = 0
        for l in (series or {}).get("lessons", []):
            if l["id"] == data["lesson_id"]:
                from content_loader import load_lesson
                les = load_lesson(data["series_id"], data["lesson_id"])
                for b in (les or {}).get("blocks", []):
                    if b["type"] == "quiz":
                        total_q = len(b["questions"])
        xp_earned = xp_for_lesson(data.get("quiz_score"), total_q)
        old_rank = get_rank(child.xp)
        child.xp = (child.xp or 0) + xp_earned
        new_rank = get_rank(child.xp)
        rank_up = new_rank[1] != old_rank[1]

        # Streak
        today = _date.today()
        if child.last_active is None or child.last_active < today:
            from datetime import timedelta
            if child.last_active == today - timedelta(days=1):
                child.streak = (child.streak or 0) + 1
            elif child.last_active != today:
                child.streak = 1
            child.last_active = today
            if (child.streak or 0) > (child.longest_streak or 0):
                child.longest_streak = child.streak

    db.session.commit()

    # check series complete
    series = load_series(data["series_id"])
    series_complete = False
    if series:
        total = len(series["lessons"])
        done = Progress.query.filter_by(child_id=child.id,
                                        series_id=data["series_id"],
                                        completed=True).count()
        series_complete = done >= total

    new_badges = check_badges(child, series_id=data["series_id"],
                              quiz_score=data.get("quiz_score"), total_q=total_q)
    if new_badges:
        db.session.commit()
    _, rank_name, rank_emoji = get_rank(child.xp)
    badge_details = [{"id": b, "name": BADGES[b]["name"], "emoji": BADGES[b]["emoji"]}
                     for b in new_badges if b in BADGES]
    return jsonify(ok=True, xp_earned=xp_earned, total_xp=child.xp,
                   rank=rank_name, rank_emoji=rank_emoji, rank_up=rank_up,
                   streak=child.streak or 0, series_complete=series_complete,
                   new_badges=badge_details)


# ----------------------------------------------------- auth & profiles
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        if User.query.filter_by(email=email).first():
            flash(t({"en": "That email is already registered.",
                     "es": "Ese correo ya está registrado."}))
            return redirect(url_for("register"))
        user = User(email=email, display_name=request.form["name"].strip(),
                    lang=get_lang())
        user.set_password(request.form["password"])
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for("profiles"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(
            email=request.form["email"].strip().lower()).first()
        if user and user.check_password(request.form["password"]):
            login_user(user)
            return redirect(url_for("profiles"))
        flash(t({"en": "Email or password didn't match.",
                 "es": "El correo o la contraseña no coinciden."}))
    return render_template("login.html")


@app.route("/logout")
def logout():
    logout_user()
    session.pop("active_child_id", None)
    return redirect(url_for("index"))


@app.route("/profiles", methods=["GET", "POST"])
@login_required
def profiles():
    if request.method == "POST":
        if len(current_user.children) >= current_user.max_children:
            flash(t({"en": "Your plan's profile limit is reached.",
                     "es": "Has llegado al límite de perfiles de tu plan."}))
        else:
            db.session.add(ChildProfile(user_id=current_user.id,
                                        name=request.form["name"].strip(),
                                        avatar=request.form.get("avatar", "🌟")))
            db.session.commit()
    return render_template("profiles.html")


@app.route("/profiles/<int:child_id>/select")
@login_required
def select_child(child_id):
    child = db.session.get(ChildProfile, child_id)
    if child and child.user_id == current_user.id:
        session["active_child_id"] = child.id
    return redirect(url_for("library"))


@app.route("/dashboard")
@login_required
def dashboard():
    """Parent view: every child's lamps across every series."""
    all_series = load_all_series()
    report = []
    for child in current_user.children:
        rows = Progress.query.filter_by(child_id=child.id, completed=True).all()
        done_map = {}
        for r in rows:
            done_map.setdefault(r.series_id, set()).add(r.lesson_id)
        badges = Badge.query.filter_by(child_id=child.id).all()
        report.append({"child": child, "done": done_map, "badges": badges})
    return render_template("dashboard.html", report=report, all_series=all_series)


# ----------------------------------------------------- feedback
@app.route("/feedback/submit", methods=["POST"])
def feedback_submit():
    msg = request.form.get("message", "").strip()
    if msg:
        db.session.add(Feedback(page=request.form.get("page", "")[:200],
                                lang=get_lang(), message=msg[:2000]))
        db.session.commit()
        flash(t({"en": "Thank you! Your report helps us improve every language.",
                 "es": "¡Gracias! Tu reporte nos ayuda a mejorar cada idioma.",
                 "fr": "Merci ! Votre signalement nous aide à améliorer chaque langue."}))
    return redirect(request.form.get("page") or url_for("index"))


@app.route("/feedback")
@login_required
def feedback_list():
    if current_user.id != 1:        # owner only (first registered account)
        abort(403)
    rows = Feedback.query.order_by(Feedback.created_at.desc()).all()
    return render_template("feedback.html", rows=rows)




# ----------------------------------------------------- AI companion (Groq free tier)
@app.route("/api/ask", methods=["POST"])
@login_required
def api_ask():
    import urllib.request, json as _json, os
    data = request.get_json(force=True)
    question = data.get("question", "").strip()[:300]
    lesson_id = data.get("lesson_id", "")
    series_id = data.get("series_id", "")
    lang = data.get("lang", "en")
    if not question:
        return jsonify(error="No question provided"), 400

    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return jsonify(answer=t({
            "en": "The AI companion needs a GROQ_API_KEY to work. Ask your parent to set it up!",
            "es": "El compañero IA necesita una clave GROQ_API_KEY. ¡Pídele a tu padre que la configure!",
            "fr": "Le compagnon IA a besoin d'une clé GROQ_API_KEY. Demande à ton parent de la configurer !"
        }))

    lesson = load_lesson(series_id, lesson_id)
    lesson_text = ""
    if lesson:
        for b in lesson.get("blocks", []):
            if b["type"] == "story":
                lesson_text = b.get("body", {}).get("en", "")[:800]
                break

    lang_name = {"en": "English", "es": "Spanish", "fr": "French"}.get(lang, "English")
    system = f"""You are a warm, wise Bible teacher answering questions from a child aged 6-12 about a Bible lesson.
Lesson topic: {lesson_id} from Ephesians.
Lesson content summary: {lesson_text[:400]}
Doctrinal framework: Wesleyan-Holiness biblical Christianity, consistent with the Deeper Life Bible Church doctrinal tradition — (1) Scripture as final authority, (2) Total depravity of man, (3) Repentance: complete turning from all sin, required before saving faith, (4) Restitution: making amends for wrongs done, (5) Justification by grace through faith in the atoning blood of Christ, (6) Entire Sanctification: a definite second work of grace, instantaneous, by which the heart is purified — NOT progressive but received by faith, (7) Holy Ghost Baptism: enduement of power upon the sanctified believer, (8) Holy living and separation from the world, (9) Personal evangelism as every believer's calling, (10) Salvation CAN be lost through wilful persistent sin — no unconditional eternal security. Always answer within these convictions. Never contradict them.
Rules: Answer in {lang_name}. Keep answers to 3-4 sentences maximum. Use simple, joyful, age-appropriate language.
Never speculate beyond scripture. Never contradict the doctrinal framework. If a question is off-topic, gently bring it back to the lesson.
Do not mention AI, Groq, or any technology. You are simply a Bible teacher."""

    body = _json.dumps({
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": question}],
        "max_tokens": 180, "temperature": 0.5
    }).encode()
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            result = _json.load(r)
        answer = result["choices"][0]["message"]["content"].strip()
        return jsonify(answer=answer)
    except Exception as e:
        return jsonify(answer=t({
            "en": "I couldn't answer right now — try again in a moment!",
            "es": "No pude responder ahora — ¡inténtalo de nuevo en un momento!",
            "fr": "Je n'ai pas pu répondre maintenant — réessaie dans un moment !"
        }))


# ----------------------------------------------------- soul winner tracker
@app.route("/mission")
@login_required
def mission():
    child = active_child()
    targets = MissionTarget.query.filter_by(child_id=child.id).order_by(
        MissionTarget.created_at.desc()).all() if child else []
    return render_template("mission.html", targets=targets, child=child)


@app.route("/mission/add", methods=["POST"])
@login_required
def mission_add():
    child = active_child()
    if not child:
        flash(t({"en": "Select a child profile first.", "es": "Selecciona un perfil de niño primero.",
                 "fr": "Sélectionne un profil d'enfant d'abord."}))
        return redirect(url_for("profiles"))
    name = request.form.get("name", "").strip()
    if name:
        db.session.add(MissionTarget(child_id=child.id, name=name,
                                     notes=request.form.get("notes","").strip()[:300]))
        db.session.commit()
        if award_badge(child, "soul_winner"): db.session.commit()
    return redirect(url_for("mission"))


@app.route("/mission/<int:target_id>/toggle/<field>", methods=["POST"])
@login_required
def mission_toggle(target_id, field):
    child = active_child()
    t_obj = db.session.get(MissionTarget, target_id)
    if t_obj and child and t_obj.child_id == child.id and field in ("prayed_today","shared_gospel","responded"):
        setattr(t_obj, field, not getattr(t_obj, field))
        db.session.commit()
    return redirect(url_for("mission"))


@app.route("/mission/<int:target_id>/delete", methods=["POST"])
@login_required
def mission_delete(target_id):
    child = active_child()
    t_obj = db.session.get(MissionTarget, target_id)
    if t_obj and child and t_obj.child_id == child.id:
        db.session.delete(t_obj); db.session.commit()
    return redirect(url_for("mission"))


# ----------------------------------------------------- certificates
from flask import send_file
import io

@app.route("/certificate/lesson/<series_id>/<lesson_id>/<int:child_id>")
@login_required
def cert_lesson(series_id, lesson_id, child_id):
    child = db.session.get(ChildProfile, child_id)
    if not child or child.user_id != current_user.id:
        abort(403)
    progress = Progress.query.filter_by(child_id=child_id, series_id=series_id,
                                        lesson_id=lesson_id, completed=True).first()
    if not progress:
        abort(404)
    series = load_series(series_id)
    lesson = load_lesson(series_id, lesson_id)
    if not series or not lesson:
        abort(404)
    lesson_num = next((i+1 for i, l in enumerate(series["lessons"])
                       if l["id"] == lesson_id), 1)
    _, rank_name, _ = get_rank(child.xp or 0)
    lang = get_lang()
    from certificate import lesson_certificate
    pdf = lesson_certificate(
        child_name=child.name,
        lesson_title=t(lesson["title"]),
        series_title=t(series["title"]),
        lesson_ref=lesson.get("ref",""),
        rank_name=rank_name,
        lesson_number=lesson_num,
        total_lessons=len(series["lessons"]),
        lang=lang
    )
    if award_badge(child, "certified"): db.session.commit()
    fname = f"LuzKids_{child.name}_{lesson_id}.pdf".replace(" ","_")
    return send_file(io.BytesIO(pdf), mimetype="application/pdf",
                     as_attachment=False, download_name=fname)


@app.route("/certificate/series/<series_id>/<int:child_id>")
@login_required
def cert_series(series_id, child_id):
    child = db.session.get(ChildProfile, child_id)
    if not child or child.user_id != current_user.id:
        abort(403)
    series = load_series(series_id)
    if not series:
        abort(404)
    done = Progress.query.filter_by(child_id=child_id, series_id=series_id,
                                    completed=True).count()
    if done < len(series["lessons"]):
        abort(403)  # not complete yet
    _, rank_name, _ = get_rank(child.xp or 0)
    lang = get_lang()
    from certificate import series_certificate
    pdf = series_certificate(
        child_name=child.name,
        series_title=t(series["title"]),
        total_lessons=len(series["lessons"]),
        rank_name=rank_name,
        total_xp=child.xp or 0,
        lang=lang
    )
    fname = f"LuzKids_{child.name}_{series_id}_Complete.pdf".replace(" ","_")
    return send_file(io.BytesIO(pdf), mimetype="application/pdf",
                     as_attachment=False, download_name=fname)



# ----------------------------------------------------- PWA
@app.route("/manifest.json")
def pwa_manifest():
    from flask import jsonify
    return jsonify({
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
    })

@app.route("/sw.js")
def service_worker():
    from flask import send_from_directory
    return send_from_directory("static", "sw.js",
                               mimetype="application/javascript")


# ---------------------------------------------------------------- main
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
