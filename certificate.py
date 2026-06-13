"""
certificate.py — LuzKids / Jesus' Arrows certificate generator.
Produces beautifully designed printable PDFs using ReportLab.
Two certificate types:
  • Lesson certificate  — one per lesson completed
  • Series certificate  — for completing an entire series
"""
import io
from datetime import date
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.units import cm, mm

# ── brand colours (match CSS vars) ──────────────────────────────────────────
NAVY   = HexColor("#1e2547")
NAVY_D = HexColor("#12172e")
GOLD   = HexColor("#f6ab3a")
GOLD_S = HexColor("#ffd98a")
MEADOW = HexColor("#4f9d69")
PAPER  = HexColor("#fdf7ec")

# ── rank table (matches RANKS in app.py) ─────────────────────────────────────
RANKS = [
    (0,    "Seeker"),
    (100,  "Believer"),
    (300,  "Growing"),
    (600,  "Sanctified"),
    (1000, "Spirit-Filled"),
    (1500, "Arrow in Training"),
    (2200, "Jesus' Arrow"),
    (3000, "Arrow of Light"),
    (4000, "Sent Arrow"),
]

def get_rank_name(xp):
    name = RANKS[0][1]
    for threshold, label in RANKS:
        if xp >= threshold:
            name = label
    return name

# ── helpers ──────────────────────────────────────────────────────────────────
def _draw_border(c, W, H, margin=18):
    m = margin
    # outer gold frame
    c.setStrokeColor(GOLD)
    c.setLineWidth(4)
    c.rect(m, m, W - 2*m, H - 2*m)
    # inner thin frame
    c.setLineWidth(1.2)
    c.rect(m+7, m+7, W - 2*(m+7), H - 2*(m+7))

def _draw_corner_ornaments(c, W, H, margin=18):
    """Simple corner diamond ornaments."""
    m, s = margin + 18, 10
    c.setFillColor(GOLD)
    for x, y in [(m, m), (W-m, m), (m, H-m), (W-m, H-m)]:
        p = c.beginPath()
        p.moveTo(x, y-s); p.lineTo(x+s, y); p.lineTo(x, y+s); p.lineTo(x-s, y)
        p.close()
        c.drawPath(p, fill=1, stroke=0)

def _draw_lamp(c, cx, cy, size=28):
    """A tiny candle flame glyph drawn with bezier."""
    c.setFillColor(GOLD)
    c.setStrokeColor(GOLD_S)
    c.setLineWidth(1)
    p = c.beginPath()
    p.moveTo(cx, cy + size)
    p.curveTo(cx + size*0.6, cy + size*0.6, cx + size*0.4, cy, cx, cy - size*0.1)
    p.curveTo(cx - size*0.4, cy, cx - size*0.6, cy + size*0.6, cx, cy + size)
    p.close()
    c.drawPath(p, fill=1, stroke=0)
    # wick
    c.setStrokeColor(GOLD_S); c.setLineWidth(2)
    c.line(cx, cy - size*0.1, cx, cy - size*0.5)

# ── lesson certificate ────────────────────────────────────────────────────────
def lesson_certificate(child_name, lesson_title, series_title,
                       lesson_ref, rank_name, lesson_number,
                       total_lessons, lang="en"):
    """
    Returns a bytes PDF for a single completed lesson.
    A4 landscape, navy background, gold frame, frameable quality.
    """
    W, H = landscape(A4)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(W, H))

    # background
    c.setFillColor(NAVY_D)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # inner warm cream panel
    panel_m = 30
    c.setFillColor(HexColor("#0f1428"))
    c.roundRect(panel_m, panel_m, W - 2*panel_m, H - 2*panel_m, 16, fill=1, stroke=0)

    _draw_border(c, W, H, margin=panel_m)
    _draw_corner_ornaments(c, W, H, margin=panel_m)

    # top lamp ornaments
    for lx in [W*0.28, W*0.72]:
        _draw_lamp(c, lx, H - 62, size=20)

    # ── HEADER ────────────────────────────────────────────────────────────────
    # Organisation name
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(W/2, H - 68, "JESUS' ARROWS  ·  LUZKIDS BIBLE PROGRAMME")

    # thin gold rule
    c.setStrokeColor(GOLD); c.setLineWidth(1.5)
    c.line(W*0.2, H - 80, W*0.8, H - 80)

    # preamble text
    preamble = {
        "en": "This certificate is proudly awarded to",
        "es": "Este certificado se otorga con orgullo a",
        "fr": "Ce certificat est fièrement décerné à",
    }.get(lang, "This certificate is proudly awarded to")
    c.setFillColor(HexColor("#c8d4f0"))
    c.setFont("Helvetica", 12)
    c.drawCentredString(W/2, H - 108, preamble)

    # ── CHILD NAME ────────────────────────────────────────────────────────────
    c.setFillColor(white)
    name_size = max(28, min(44, int(540 / max(len(child_name), 1))))
    c.setFont("Helvetica-Bold", name_size)
    c.drawCentredString(W/2, H - 148, child_name)

    # name underline
    name_w = c.stringWidth(child_name, "Helvetica-Bold", name_size)
    c.setStrokeColor(GOLD_S); c.setLineWidth(1)
    c.line(W/2 - name_w/2 - 10, H - 155, W/2 + name_w/2 + 10, H - 155)

    # ── ACHIEVEMENT TEXT ──────────────────────────────────────────────────────
    action = {
        "en": "has successfully completed",
        "es": "ha completado exitosamente",
        "fr": "a complété avec succès",
    }.get(lang, "has successfully completed")
    c.setFillColor(HexColor("#c8d4f0")); c.setFont("Helvetica", 13)
    c.drawCentredString(W/2, H - 182, action)

    # Lesson title (gold, big)
    c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(W/2, H - 216, f"Lesson {lesson_number}: {lesson_title}")

    # Series and ref
    c.setFillColor(HexColor("#a8b8e0")); c.setFont("Helvetica", 12)
    c.drawCentredString(W/2, H - 238, f"{series_title}  ·  {lesson_ref}")

    # ── PROGRESS INDICATOR ────────────────────────────────────────────────────
    prog_y = H - 272
    bar_w, bar_h = 340, 10
    bar_x = W/2 - bar_w/2
    # track
    c.setFillColor(HexColor("#2a3560")); c.roundRect(bar_x, prog_y, bar_w, bar_h, 5, fill=1, stroke=0)
    # fill
    fill_w = bar_w * lesson_number / total_lessons
    c.setFillColor(GOLD); c.roundRect(bar_x, prog_y, fill_w, bar_h, 5, fill=1, stroke=0)
    # label
    c.setFillColor(HexColor("#a8b8e0")); c.setFont("Helvetica", 10)
    prog_label = {
        "en": f"Series progress: {lesson_number} of {total_lessons} lessons",
        "es": f"Progreso de la serie: {lesson_number} de {total_lessons} lecciones",
        "fr": f"Progrès de la série: {lesson_number} de {total_lessons} leçons",
    }.get(lang)
    c.drawCentredString(W/2, prog_y - 14, prog_label)

    # ── RANK BADGE ────────────────────────────────────────────────────────────
    badge_x, badge_y = W - 130, 90
    c.setFillColor(HexColor("#1e2e60")); c.roundRect(badge_x - 50, badge_y - 20, 140, 52, 12, fill=1, stroke=0)
    c.setStrokeColor(GOLD); c.setLineWidth(1.5); c.roundRect(badge_x - 50, badge_y - 20, 140, 52, 12, fill=0, stroke=1)
    rank_label = {"en": "Rank", "es": "Rango", "fr": "Rang"}.get(lang, "Rank")
    c.setFillColor(GOLD_S); c.setFont("Helvetica-Bold", 8); c.drawCentredString(badge_x + 20, badge_y + 22, rank_label.upper())
    c.setFillColor(white); c.setFont("Helvetica-Bold", 11); c.drawCentredString(badge_x + 20, badge_y + 4, rank_name)

    # ── SCRIPTURE ─────────────────────────────────────────────────────────────
    verse = {
        "en": '"Like arrows in the hands of a warrior are children born in one\'s youth."  — Psalm 127:4',
        "es": '"Como flechas en las manos del guerrero son los hijos de la juventud."  — Salmo 127:4',
        "fr": '"Comme les flèches dans la main d\'un guerrier, ainsi sont les fils de la jeunesse."  — Psaume 127:4',
    }.get(lang)
    c.setFillColor(HexColor("#7888b8")); c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(W/2, 72, verse)

    # thin rule above verse
    c.setStrokeColor(HexColor("#2a3560")); c.setLineWidth(1)
    c.line(W*0.2, 86, W*0.8, 86)

    # ── DATE ─────────────────────────────────────────────────────────────────
    today = date.today()
    date_str = {
        "en": today.strftime("%B %d, %Y"),
        "es": today.strftime("%d de %B de %Y"),
        "fr": today.strftime("%d %B %Y"),
    }.get(lang, today.strftime("%B %d, %Y"))
    date_label = {"en": "Awarded on", "es": "Otorgado el", "fr": "Décerné le"}.get(lang)
    c.setFillColor(HexColor("#6070a0")); c.setFont("Helvetica", 10)
    c.drawString(60, 72, f"{date_label}: {date_str}")

    # luzkids.org bottom right
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(HexColor("#4050a0"))
    c.drawRightString(W - 60, 56, "LuzKids · Jesus' Arrows")
    c.drawRightString(W - 60, 44, "luzkids.org")

    c.save()
    buf.seek(0)
    return buf.read()


# ── series (full module) certificate ─────────────────────────────────────────
def series_certificate(child_name, series_title, total_lessons,
                       rank_name, total_xp, lang="en"):
    """
    Returns a bytes PDF for completing an entire series.
    More elaborate design with gold seal and all lessons acknowledged.
    """
    W, H = landscape(A4)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(W, H))

    # rich dark background with subtle gradient effect (two rects)
    c.setFillColor(HexColor("#0a0f24"))
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(HexColor("#141a38"))
    c.rect(0, H*0.4, W, H*0.6, fill=1, stroke=0)

    # gold border — double frame
    for margin, lw in [(20, 5), (30, 1.5)]:
        c.setStrokeColor(GOLD); c.setLineWidth(lw)
        c.rect(margin, margin, W - 2*margin, H - 2*margin)
    _draw_corner_ornaments(c, W, H, margin=20)

    # lamp row across top
    for i, lx in enumerate([W*0.18, W*0.32, W*0.46, W*0.54, W*0.68, W*0.82]):
        _draw_lamp(c, lx, H - 55, size=16)

    # ── SERIES CERTIFICATE HEADER ─────────────────────────────────────────────
    c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(W/2, H - 75, "JESUS' ARROWS  ·  LUZKIDS BIBLE PROGRAMME")
    c.setStrokeColor(GOLD); c.setLineWidth(1.5)
    c.line(W*0.15, H - 87, W*0.85, H - 87)

    # gold star seal (simulated)
    seal_x, seal_y = W/2, H - 130
    c.setFillColor(HexColor("#c9821f")); c.circle(seal_x, seal_y, 38, fill=1, stroke=0)
    c.setFillColor(GOLD); c.circle(seal_x, seal_y, 34, fill=1, stroke=0)
    c.setFillColor(NAVY_D); c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(seal_x, seal_y + 8, "SERIES")
    c.drawCentredString(seal_x, seal_y - 4, "COMPLETE")
    c.setFont("Helvetica", 7)
    c.drawCentredString(seal_x, seal_y - 15, "🕯️" * 5)

    # preamble
    preamble = {"en": "With great joy, this certifies that",
                "es": "Con gran alegría, este certificado declara que",
                "fr": "Avec grande joie, ce certificat atteste que"}.get(lang)
    c.setFillColor(HexColor("#c8d4f0")); c.setFont("Helvetica", 12)
    c.drawCentredString(W/2, H - 180, preamble)

    # child name
    c.setFillColor(white)
    name_size = max(32, min(50, int(580 / max(len(child_name), 1))))
    c.setFont("Helvetica-Bold", name_size)
    c.drawCentredString(W/2, H - 222, child_name)
    name_w = c.stringWidth(child_name, "Helvetica-Bold", name_size)
    c.setStrokeColor(GOLD_S); c.setLineWidth(1)
    c.line(W/2 - name_w/2 - 15, H - 230, W/2 + name_w/2 + 15, H - 230)

    # achievement
    action = {"en": "has completed the entire",
              "es": "ha completado la serie completa",
              "fr": "a complété entièrement la série"}.get(lang)
    c.setFillColor(HexColor("#c8d4f0")); c.setFont("Helvetica", 13)
    c.drawCentredString(W/2, H - 258, action)

    # series title (gold, large)
    c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(W/2, H - 292, series_title)

    # all N lessons
    all_lessons = {"en": f"All {total_lessons} lessons — every chapter, every verse",
                   "es": f"Las {total_lessons} lecciones — cada capítulo, cada versículo",
                   "fr": f"Les {total_lessons} leçons — chaque chapitre, chaque verset"}.get(lang)
    c.setFillColor(HexColor("#a8b8e0")); c.setFont("Helvetica", 12)
    c.drawCentredString(W/2, H - 314, all_lessons)

    # lamp row for completion (one per lesson, tiny)
    lamp_y = H - 342
    lamps_per_row = total_lessons
    spacing = min(28, (W - 200) / lamps_per_row)
    start_x = W/2 - (spacing * (lamps_per_row - 1)) / 2
    c.setFillColor(GOLD)
    for i in range(lamps_per_row):
        _draw_lamp(c, start_x + i * spacing, lamp_y, size=9)

    # rank + XP
    badge_y = 95
    c.setFillColor(HexColor("#1e2e60"))
    c.roundRect(W/2 - 110, badge_y - 20, 220, 56, 14, fill=1, stroke=0)
    c.setStrokeColor(GOLD); c.setLineWidth(2)
    c.roundRect(W/2 - 110, badge_y - 20, 220, 56, 14, fill=0, stroke=1)
    rank_label = {"en": "Rank Achieved", "es": "Rango Logrado", "fr": "Rang Atteint"}.get(lang)
    c.setFillColor(GOLD_S); c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(W/2, badge_y + 26, rank_label.upper())
    c.setFillColor(white); c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(W/2, badge_y + 8, rank_name)
    xp_label = {"en": f"{total_xp} XP earned", "es": f"{total_xp} XP ganados", "fr": f"{total_xp} XP gagnés"}.get(lang)
    c.setFillColor(GOLD); c.setFont("Helvetica", 10)
    c.drawCentredString(W/2, badge_y - 8, xp_label)

    # scripture
    verse = {"en": '"Like arrows in the hands of a warrior are children born in one\'s youth."  — Psalm 127:4',
             "es": '"Como flechas en las manos del guerrero son los hijos de la juventud."  — Salmo 127:4',
             "fr": '"Comme les flèches dans la main d\'un guerrier, ainsi sont les fils de la jeunesse."  — Psaume 127:4'}.get(lang)
    c.setStrokeColor(HexColor("#2a3560")); c.setLineWidth(1); c.line(W*0.15, 75, W*0.85, 75)
    c.setFillColor(HexColor("#7888b8")); c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(W/2, 60, verse)

    today = date.today()
    date_str = today.strftime("%B %d, %Y")
    date_label = {"en": "Awarded on", "es": "Otorgado el", "fr": "Décerné le"}.get(lang)
    c.setFillColor(HexColor("#6070a0")); c.setFont("Helvetica", 10)
    c.drawString(55, 60, f"{date_label}: {date_str}")
    c.setFont("Helvetica-Bold", 10); c.setFillColor(HexColor("#4050a0"))
    c.drawRightString(W - 55, 48, "LuzKids · Jesus' Arrows")

    c.save()
    buf.seek(0)
    return buf.read()
