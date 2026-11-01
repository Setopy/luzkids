/* LuzKids on-device progress.
 *
 * Privacy by design: everything about a child (nickname, avatar, lessons
 * done, XP, streaks, badges, certificates and the Mission log) is kept ONLY
 * in this browser's localStorage. Nothing here is ever sent to the server.
 * Families can move progress between devices with a file they download
 * and load themselves.
 *
 * The pure functions at the top are also exported for Node tests.
 */
(function (root) {
  "use strict";

  var KEY = "luzkids.v1";
  var MAX_PROFILES = 10;
  var AVATARS = ["🌟", "🦁", "🐑", "🕊️", "🌈", "🛡️", "🎺", "🌻"];

  /* ------------------------------------------------------------ pure logic */
  function emptyState() { return { version: 1, active: null, profiles: [] }; }

  function cleanText(v, max) {
    return String(v == null ? "" : v).replace(/[\u0000-\u001f]/g, " ").trim().slice(0, max);
  }

  function isoDay(d) {
    d = d || new Date();
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  }

  function daysBetween(a, b) { // whole days from day string a to day string b
    var pa = a.split("-").map(Number), pb = b.split("-").map(Number);
    return Math.round((Date.UTC(pb[0], pb[1] - 1, pb[2]) - Date.UTC(pa[0], pa[1] - 1, pa[2])) / 86400000);
  }

  function rankFor(xp, ranks) {
    var r = ranks[0];
    ranks.forEach(function (x) { if (xp >= x[0]) r = x; });
    return r;
  }

  function xpForLesson(score, totalQ) {
    return 50 + (score != null && totalQ > 0 && score === totalQ ? 25 : 0);
  }

  function newProfile(name, avatar, now) {
    return {
      id: "p" + Math.random().toString(36).slice(2, 10),
      name: cleanText(name, 40), avatar: AVATARS.indexOf(avatar) >= 0 ? avatar : AVATARS[0],
      xp: 0, streak: 0, longest: 0, last: null, badges: {}, done: {}, mission: [],
      created: isoDay(now)
    };
  }

  function award(profile, id, now) {
    if (profile.badges[id]) return false;
    profile.badges[id] = isoDay(now);
    return true;
  }

  function doneCount(profile, seriesId) {
    return Object.keys(profile.done).filter(function (k) {
      return !seriesId || k.indexOf(seriesId + "/") === 0;
    }).length;
  }

  /* Mark a lesson complete. `seriesLessons` is the list of real lesson ids in
     the series and `totalQ` the lesson's real number of quiz questions, both
     provided by the page, so made-up lessons or scores can't add points. */
  function completeLesson(profile, opts, ranks, now) {
    var seriesLessons = opts.seriesLessons || [];
    if (seriesLessons.indexOf(opts.lessonId) < 0) return null;
    var totalQ = Math.max(0, opts.totalQ | 0);
    var score = opts.score == null ? null : Math.max(0, Math.min(totalQ, opts.score | 0));
    var key = opts.seriesId + "/" + opts.lessonId;
    var already = !!profile.done[key];
    var today = isoDay(now);
    var res = { xp_earned: 0, rank_up: false, new_badges: [] };

    if (!already) {
      profile.done[key] = { score: score, at: today };
      var oldRank = rankFor(profile.xp, ranks);
      res.xp_earned = xpForLesson(score, totalQ);
      profile.xp += res.xp_earned;
      res.rank_up = rankFor(profile.xp, ranks)[1] !== oldRank[1];
      if (!profile.last || profile.last < today) {
        profile.streak = profile.last && daysBetween(profile.last, today) === 1 ? profile.streak + 1 : 1;
        profile.last = today;
        profile.longest = Math.max(profile.longest, profile.streak);
      }
    } else if (score != null) {
      var prev = profile.done[key].score;
      if (prev == null || score > prev) profile.done[key].score = score;
    }

    var total = doneCount(profile);
    var seriesDone = seriesLessons.every(function (l) { return profile.done[opts.seriesId + "/" + l]; });
    var checks = [
      ["first_lamp", total >= 1], ["word_seeker", total >= 5], ["explorer", total >= 10],
      ["on_fire", profile.streak >= 3], ["ablaze", profile.streak >= 7],
      ["quiz_hero", score != null && totalQ > 0 && score === totalQ],
      ["graduate", seriesDone],
      ["jesus_arrow", rankFor(profile.xp, ranks)[1] === "Jesus' Arrow"]
    ];
    checks.forEach(function (c) { if (c[1] && award(profile, c[0], now)) res.new_badges.push(c[0]); });

    var r = rankFor(profile.xp, ranks);
    res.total_xp = profile.xp; res.rank = r[1]; res.rank_emoji = r[2];
    res.streak = profile.streak; res.series_complete = seriesDone;
    return res;
  }

  /* Accept only a well-formed progress file, keeping known fields. */
  function sanitizeState(raw) {
    if (!raw || typeof raw !== "object" || !Array.isArray(raw.profiles)) return null;
    var out = emptyState();
    raw.profiles.slice(0, MAX_PROFILES).forEach(function (p) {
      if (!p || typeof p !== "object") return;
      var q = newProfile(p.name, p.avatar);
      if (typeof p.id === "string" && /^p[a-z0-9]{1,16}$/.test(p.id)) q.id = p.id;
      q.xp = Math.max(0, Math.min(1e6, p.xp | 0));
      q.streak = Math.max(0, p.streak | 0); q.longest = Math.max(q.streak, p.longest | 0);
      q.last = /^\d{4}-\d{2}-\d{2}$/.test(p.last || "") ? p.last : null;
      q.created = /^\d{4}-\d{2}-\d{2}$/.test(p.created || "") ? p.created : q.created;
      if (p.badges && typeof p.badges === "object") Object.keys(p.badges).slice(0, 50).forEach(function (b) {
        if (/^[a-z_]{1,30}$/.test(b)) q.badges[b] = cleanText(p.badges[b], 10);
      });
      if (p.done && typeof p.done === "object") Object.keys(p.done).slice(0, 2000).forEach(function (k) {
        if (/^[a-z0-9_-]{1,60}\/[a-z0-9_-]{1,60}$/i.test(k)) {
          var d = p.done[k] || {};
          q.done[k] = { score: d.score == null ? null : Math.max(0, d.score | 0), at: cleanText(d.at, 10) };
        }
      });
      if (Array.isArray(p.mission)) p.mission.slice(0, 200).forEach(function (m) {
        if (!m || typeof m !== "object") return;
        q.mission.push({ id: cleanText(m.id, 20) || ("m" + Math.random().toString(36).slice(2, 10)),
          name: cleanText(m.name, 40), notes: cleanText(m.notes, 200),
          prayed: !!m.prayed, shared: !!m.shared, responded: !!m.responded });
      });
      if (q.name) out.profiles.push(q);
    });
    var ids = out.profiles.map(function (p) { return p.id; });
    out.active = ids.indexOf(raw.active) >= 0 ? raw.active : (ids[0] || null);
    return out;
  }

  var api = { emptyState: emptyState, newProfile: newProfile, completeLesson: completeLesson,
              rankFor: rankFor, xpForLesson: xpForLesson, sanitizeState: sanitizeState,
              award: award, doneCount: doneCount, isoDay: isoDay, daysBetween: daysBetween,
              AVATARS: AVATARS, MAX_PROFILES: MAX_PROFILES };
  if (typeof module !== "undefined" && module.exports) { module.exports = api; return; }

  /* ------------------------------------------------------------ browser */
  var doc = root.document;
  var dataEl = doc.getElementById("luz-data");
  var LUZ = dataEl ? JSON.parse(dataEl.textContent) : { ranks: [[0, "Seeker", "🔍"]], badges: {}, s: {} };
  var S = LUZ.s || {};
  var BASE = LUZ.base || "/en";   // language prefix, e.g. "/es"

  function load() {
    try { return sanitizeState(JSON.parse(root.localStorage.getItem(KEY) || "null")) || emptyState(); }
    catch (e) { return emptyState(); }
  }
  function save(st) { try { root.localStorage.setItem(KEY, JSON.stringify(st)); } catch (e) { /* storage full or blocked */ } }
  function activeProfile(st) {
    for (var i = 0; i < st.profiles.length; i++) if (st.profiles[i].id === st.active) return st.profiles[i];
    return null;
  }
  function el(tag, cls, text) {
    var e = doc.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function pageData(id) {
    var n = doc.getElementById(id);
    return n ? JSON.parse(n.textContent) : null;
  }
  function badgeLine(id) {
    var b = LUZ.badges[id] || { emoji: "🏅", name: id };
    return b.emoji + " " + b.name;
  }
  function certUrl(profileId, seriesId, lessonId) {
    return BASE + "/certificate/?p=" + encodeURIComponent(profileId) + "&s=" + encodeURIComponent(seriesId) +
      (lessonId ? "&l=" + encodeURIComponent(lessonId) : "");
  }

  /* Award a badge to whoever is learning on this device (used by games). */
  api.awardActive = function (id) {
    var st = load(), p = activeProfile(st);
    if (p && LUZ.badges[id] && award(p, id)) { save(st); return true; }
    return false;
  };
  root.LuzProgress = api;

  /* ---- nav chip */
  function updateChip() {
    var chip = doc.getElementById("child-chip");
    if (!chip) return;
    var ap = activeProfile(load());
    chip.textContent = ap ? ap.avatar + " " + ap.name : "👤 " + (S.choose_child || "Choose child");
  }
  updateChip();

  /* ---- series page: light lamps for lessons done on this device */
  var list = doc.querySelector(".lesson-list[data-series]");
  if (list) {
    var sp = activeProfile(load());
    if (sp) list.querySelectorAll(".lesson-row[data-lesson]").forEach(function (row) {
      if (sp.done[list.dataset.series + "/" + row.dataset.lesson]) {
        row.classList.add("done");
        var mark = row.querySelector(".lamp-mark");
        if (mark) mark.textContent = "🕯️";
      }
    });
  }

  /* ---- lesson page footer */
  var foot = doc.getElementById("lesson-progress");
  if (foot) {
    var lp = activeProfile(load());
    var info = pageData("lesson-data");
    if (!lp) {
      foot.appendChild(el("p", "meta", S.pick_child_first));
      var go = el("a", "btn ghost", S.who_learning); go.href = BASE + "/profiles/"; foot.appendChild(go);
    } else {
      var r0 = rankFor(lp.xp, LUZ.ranks);
      var bar = el("div", "pre-complete-bar");
      var streakChip = el("span", "streak-chip", "🔥 " + lp.streak + " " + S.day_streak);
      bar.appendChild(streakChip);
      bar.appendChild(el("span", "rank-chip", r0[2] + " " + r0[1]));
      var xpChip = el("span", "xp-chip", "⭐ " + lp.xp + " XP");
      bar.appendChild(xpChip);
      foot.appendChild(bar);
      var btn = el("button", "btn big", "🕯️ " + S.complete); btn.type = "button"; foot.appendChild(btn);
      var panel = el("div"); panel.hidden = true; foot.appendChild(panel);
      btn.addEventListener("click", function () {
        var st = load(), p = activeProfile(st);
        if (!p) return;
        var res = completeLesson(p, { seriesId: info.series, lessonId: info.lesson, seriesLessons: info.lessons,
          totalQ: info.total_q, score: root.LuzQuizScore == null ? null : root.LuzQuizScore }, LUZ.ranks);
        if (!res) return;
        save(st);
        btn.hidden = true; panel.hidden = false;
        var hello = el("p", "complete-name", S.lamp_lit + " ");
        hello.appendChild(el("strong", null, p.name)); hello.appendChild(doc.createTextNode(" 🌟"));
        panel.appendChild(hello);
        if (res.xp_earned > 0) panel.appendChild(el("div", "xp-award pop-in", "+" + res.xp_earned + " XP  ·  " + S.total + ": " + res.total_xp + " XP"));
        if (res.rank_up) panel.appendChild(el("div", "rank-award rank-up pop-in", "🎉 " + S.new_rank + " " + res.rank_emoji + " " + res.rank));
        streakChip.textContent = "🔥 " + res.streak + " " + S.day_streak;
        xpChip.textContent = "⭐ " + res.total_xp + " XP";
        if (res.new_badges.length) {
          var bw = el("div", "badge-earned-wrap");
          res.new_badges.forEach(function (b) { bw.appendChild(el("div", "badge-earned pop-in", S.new_badge + " " + badgeLine(b))); });
          panel.appendChild(bw);
        }
        var links = el("div", "cert-links");
        var a1 = el("a", "btn small", "📜 " + S.lesson_cert); a1.href = certUrl(p.id, info.series, info.lesson); links.appendChild(a1);
        if (res.series_complete) {
          var a2 = el("a", "btn small gold", "🏆 " + S.series_cert); a2.href = certUrl(p.id, info.series); links.appendChild(a2);
        }
        panel.appendChild(links);
        if (root.LuzCelebrate) root.LuzCelebrate(panel, res.series_complete ? 40 : 24);
      });
    }
  }

  /* ---- profiles page */
  var profApp = doc.getElementById("profiles-app");
  if (profApp) {
    var renderProfiles = function () {
      var st = load();
      var grid = doc.getElementById("profile-cards");
      grid.textContent = "";
      if (!st.profiles.length) grid.appendChild(el("p", "meta", S.no_profiles));
      st.profiles.forEach(function (p) {
        var card = el("div", "card profile" + (p.id === st.active ? " selected" : ""));
        card.appendChild(el("div", "card-emoji big", p.avatar));
        card.appendChild(el("h3", null, p.name));
        var r = rankFor(p.xp, LUZ.ranks);
        card.appendChild(el("p", "meta", r[2] + " " + r[1] + " · ⭐ " + p.xp + " XP"));
        if (p.id === st.active) card.appendChild(el("p", "meta", "✔ " + S.learning_now));
        else {
          var sel = el("button", "btn small", S.select); sel.type = "button";
          sel.addEventListener("click", function () { var s2 = load(); s2.active = p.id; save(s2); location.href = BASE + "/library/"; });
          card.appendChild(sel);
        }
        var rm = el("button", "btn small ghost", S.remove); rm.type = "button";
        rm.addEventListener("click", function () {
          if (!root.confirm(S.confirm_remove)) return;
          var s2 = load();
          s2.profiles = s2.profiles.filter(function (x) { return x.id !== p.id; });
          if (s2.active === p.id) s2.active = s2.profiles.length ? s2.profiles[0].id : null;
          save(s2); renderProfiles();
        });
        card.appendChild(rm);
        grid.appendChild(card);
      });
      doc.getElementById("add-profile").hidden = st.profiles.length >= MAX_PROFILES;
      updateChip();
    };
    var avatarSel = doc.getElementById("new-avatar");
    AVATARS.forEach(function (a) { var o = el("option", null, a); o.value = a; avatarSel.appendChild(o); });
    doc.getElementById("add-profile").addEventListener("submit", function (e) {
      e.preventDefault();
      var nameIn = doc.getElementById("new-name");
      var st = load();
      if (!cleanText(nameIn.value, 40) || st.profiles.length >= MAX_PROFILES) return;
      var p = newProfile(nameIn.value, avatarSel.value);
      st.profiles.push(p); st.active = p.id; save(st);
      nameIn.value = ""; renderProfiles();
    });
    doc.getElementById("export-btn").addEventListener("click", function () {
      var blob = new Blob([JSON.stringify(load(), null, 1)], { type: "application/json" });
      var a = doc.createElement("a");
      a.href = URL.createObjectURL(blob); a.download = "luzkids-progress-" + isoDay() + ".json";
      doc.body.appendChild(a); a.click();
      setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
      doc.getElementById("file-msg").textContent = S.saved_file;
    });
    doc.getElementById("import-file").addEventListener("change", function (e) {
      var f = e.target.files && e.target.files[0];
      var msg = doc.getElementById("file-msg");
      if (!f) return;
      var reader = new FileReader();
      reader.onload = function () {
        var st = null;
        try { st = sanitizeState(JSON.parse(reader.result)); } catch (err) { st = null; }
        if (!st) { msg.textContent = S.bad_file; return; }
        if (!root.confirm(S.confirm_load)) return;
        save(st); renderProfiles(); msg.textContent = S.loaded_file;
      };
      reader.readAsText(f.slice(0, 2000000));
      e.target.value = "";
    });
    renderProfiles();
  }

  /* ---- progress (parent view of this device) */
  var progApp = doc.getElementById("progress-app");
  if (progApp) {
    var catalog = pageData("catalog-data") || [];
    var st0 = load();
    if (!st0.profiles.length) {
      progApp.appendChild(el("p", "meta", S.no_profiles));
      var addA = el("a", "btn", S.add_child); addA.href = BASE + "/profiles/"; progApp.appendChild(addA);
    }
    st0.profiles.forEach(function (p) {
      var box = el("div", "dash-child");
      var r = rankFor(p.xp, LUZ.ranks), next = null, prev = 0;
      LUZ.ranks.forEach(function (x) { if (x[0] <= p.xp) prev = x[0]; else if (!next) next = x; });
      var card = el("div", "rank-card");
      card.appendChild(el("span", "rank-emoji", r[2]));
      var inf = el("div", "rank-info");
      inf.appendChild(el("div", "rank-name", p.avatar + " " + p.name + " — " + r[1]));
      inf.appendChild(el("div", "rank-xp", "⭐ " + p.xp + " XP" + (next ? " · " + (next[0] - p.xp) + " " + S.xp_to + " " + next[1] : "") +
        "   🔥 " + p.streak + " " + S.day_streak));
      var wrap = el("div", "xp-bar-wrap"), fill = el("div", "xp-bar-fill");
      fill.style.width = (next ? Math.min(100, Math.floor((p.xp - prev) * 100 / (next[0] - prev))) : 100) + "%";
      wrap.appendChild(fill); inf.appendChild(wrap); card.appendChild(inf); box.appendChild(card);
      var wall = el("div", "badge-wall");
      Object.keys(LUZ.badges).forEach(function (bid) {
        var b = LUZ.badges[bid], chipB = el("span", "badge-chip" + (p.badges[bid] ? " earned" : ""), b.emoji + " " + b.name);
        chipB.title = b.desc; wall.appendChild(chipB);
      });
      box.appendChild(wall);
      catalog.forEach(function (s) {
        var done = s.lessons.filter(function (l) { return p.done[s.id + "/" + l.id]; });
        var pct = s.lessons.length ? Math.floor(done.length * 100 / s.lessons.length) : 0;
        var row = el("div", "dash-series" + (pct === 100 ? " complete" : ""));
        var head = el("div", "dash-series-head");
        head.appendChild(el("span", null, s.emoji + " " + s.title));
        var meta = el("span", "meta");
        if (pct === 100) {
          meta.appendChild(doc.createTextNode("🎉 " + S.complete_word + " "));
          var ca = el("a", "btn small gold", "🏆 " + S.certificate); ca.href = certUrl(p.id, s.id); meta.appendChild(ca);
        } else meta.textContent = done.length + "/" + s.lessons.length + " · " + pct + "%";
        head.appendChild(meta); row.appendChild(head);
        var track = el("div", "progress-track"), pf = el("div", "progress-fill");
        pf.style.width = pct + "%"; track.appendChild(pf); row.appendChild(track);
        var lamps = el("div", "lamps");
        s.lessons.forEach(function (l) {
          if (p.done[s.id + "/" + l.id]) { var la = el("a", null, "🕯️"); la.href = certUrl(p.id, s.id, l.id); la.title = l.title; lamps.appendChild(la); }
          else lamps.appendChild(doc.createTextNode("·"));
        });
        row.appendChild(lamps); box.appendChild(row);
      });
      progApp.appendChild(box);
    });
  }

  /* ---- mission field (names stay on this device) */
  var misApp = doc.getElementById("mission-app");
  if (misApp) {
    var renderMission = function () {
      var st = load(), p = activeProfile(st);
      doc.getElementById("mission-nochild").hidden = !!p;
      doc.getElementById("mission-main").hidden = !p;
      if (!p) return;
      var grid = doc.getElementById("mission-grid");
      grid.textContent = "";
      doc.getElementById("mission-empty").hidden = p.mission.length > 0;
      p.mission.forEach(function (m) {
        var card = el("div", "mission-card" + (m.responded ? " responded" : ""));
        var nm = el("div", "mission-name", m.name);
        if (m.responded) nm.appendChild(el("span", "mission-badge won", " 🎉 " + S.responded));
        card.appendChild(nm);
        if (m.notes) card.appendChild(el("p", "meta", m.notes));
        [["prayed", "🙏 " + S.prayed], ["shared", "📣 " + S.shared], ["responded", "✝️ " + S.responded]].forEach(function (f) {
          var b = el("button", "btn small" + (m[f[0]] ? " gold" : " ghost"), f[1]); b.type = "button";
          b.addEventListener("click", function () {
            var s2 = load(), p2 = activeProfile(s2);
            p2.mission.forEach(function (x) { if (x.id === m.id) x[f[0]] = !x[f[0]]; });
            save(s2); renderMission();
          });
          card.appendChild(b);
        });
        var del = el("button", "btn small ghost", "✕ " + S.remove); del.type = "button";
        del.addEventListener("click", function () {
          var s2 = load(), p2 = activeProfile(s2);
          p2.mission = p2.mission.filter(function (x) { return x.id !== m.id; });
          save(s2); renderMission();
        });
        card.appendChild(del);
        grid.appendChild(card);
      });
      doc.getElementById("ms-count").textContent = p.mission.length;
      doc.getElementById("ms-shared").textContent = p.mission.filter(function (x) { return x.shared; }).length;
      doc.getElementById("ms-resp").textContent = p.mission.filter(function (x) { return x.responded; }).length;
    };
    doc.getElementById("mission-form").addEventListener("submit", function (e) {
      e.preventDefault();
      var st = load(), p = activeProfile(st);
      var nm = cleanText(doc.getElementById("ms-name").value, 40);
      if (!p || !nm || p.mission.length >= 200) return;
      p.mission.unshift({ id: "m" + Math.random().toString(36).slice(2, 10), name: nm,
        notes: cleanText(doc.getElementById("ms-notes").value, 200), prayed: false, shared: false, responded: false });
      award(p, "soul_winner");
      save(st);
      doc.getElementById("ms-name").value = ""; doc.getElementById("ms-notes").value = "";
      renderMission();
    });
    renderMission();
  }

  /* ---- printable certificate, built from on-device data only */
  var certApp = doc.getElementById("certificate-app");
  if (certApp) {
    var cat = pageData("catalog-data") || [];
    var q = new URLSearchParams(root.location.search);
    var st = load(), p = null;
    st.profiles.forEach(function (x) { if (x.id === q.get("p")) p = x; });
    var series = null; cat.forEach(function (s) { if (s.id === q.get("s")) series = s; });
    var lessonId = q.get("l"), lesson = null;
    if (series && lessonId) series.lessons.forEach(function (l) { if (l.id === lessonId) lesson = l; });
    var ok = p && series && (lessonId ? lesson && p.done[series.id + "/" + lessonId]
      : series.lessons.every(function (l) { return p.done[series.id + "/" + l.id]; }));
    if (!ok) certApp.appendChild(el("p", "card", S.cert_not_done));
    else renderCertificate(p, series, lesson, st);
  }

  function renderCertificate(p, series, lesson, st) {
    if (award(p, "certified")) save(st);
    var r = rankFor(p.xp, LUZ.ranks);
    var c = el("div", "cert-sheet");
    c.appendChild(el("div", "cert-lamp", "🕯️"));
    c.appendChild(el("h1", "cert-title", S.cert_title));
    c.appendChild(el("p", "cert-sub", S.cert_awarded));
    c.appendChild(el("p", "cert-name", p.avatar + " " + p.name));
    c.appendChild(el("p", "cert-sub", lesson ? S.cert_for_lesson : S.cert_for_series));
    c.appendChild(el("p", "cert-what", lesson ? lesson.title + " — " + series.emoji + " " + series.title : series.emoji + " " + series.title));
    c.appendChild(el("p", "cert-meta", r[2] + " " + r[1] + " · ⭐ " + p.xp + " XP · " + isoDay()));
    c.appendChild(el("p", "cert-verse", "“Let your light shine before others” — Matthew 5:16"));
    certApp.appendChild(c);
    var pr = el("button", "btn big no-print", "🖨️ " + S.print); pr.type = "button";
    pr.addEventListener("click", function () { root.print(); });
    certApp.appendChild(pr);
  }
})(typeof window !== "undefined" ? window : this);
