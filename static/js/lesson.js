/* LuzKids lesson player — scramble game, quiz, completion. No frameworks. */
(function () {
  "use strict";
  const lessonEl = document.querySelector(".lesson");
  if (!lessonEl) return;
  const seriesId = lessonEl.dataset.series;
  const lessonId = lessonEl.dataset.lesson;
  let quizScore = null;

  /* star-burst celebration — sprays stars from an element */
  function celebrate(el, count) {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const rect = el.getBoundingClientRect();
    const cx = rect.left + rect.width / 2, cy = rect.top + rect.height / 2;
    const glyphs = ["⭐", "✨", "🌟", "💛", "🕯️"];
    for (let i = 0; i < (count || 14); i++) {
      const s = document.createElement("span");
      s.className = "burst-star";
      s.textContent = glyphs[i % glyphs.length];
      const angle = (Math.PI * 2 * i) / (count || 14) + Math.random() * .5;
      const dist = 70 + Math.random() * 110;
      s.style.left = cx + "px"; s.style.top = cy + "px";
      s.style.setProperty("--dx", Math.cos(angle) * dist + "px");
      s.style.setProperty("--dy", Math.sin(angle) * dist - 40 + "px");
      document.body.appendChild(s);
      setTimeout(() => s.remove(), 1200);
    }
  }

  /* ---------------- badge notifications */
  function showBadges(badges, parent) {
    if (!badges || !badges.length) return;
    var wrap = document.createElement("div");
    wrap.className = "badge-earned-wrap";
    badges.forEach(function(b) {
      var el = document.createElement("div");
      el.className = "badge-earned pop-in";
      el.innerHTML = "<span class='badge-emoji'>" + b.emoji + "</span><span class='badge-label'>New badge: <strong>" + b.name + "</strong></span>";
      wrap.appendChild(el);
    });
    parent.appendChild(wrap);
    if (window.celebrate) celebrate(wrap, badges.length * 6);
  }

  /* ---------------- memory verse scramble ---------------- */
  document.querySelectorAll(".scramble").forEach(function (root) {
    const words = JSON.parse(root.dataset.words);
    const pool = root.querySelector(".scramble-pool");
    const answer = root.querySelector(".scramble-answer");
    const result = root.querySelector(".scramble-result");
    let placed = 0;

    function build() {
      pool.innerHTML = ""; answer.innerHTML = "";
      result.hidden = true; placed = 0;
      shuffled(words).forEach(function (w, i) {
        const b = document.createElement("button");
        b.className = "word-chip"; b.textContent = w; b.type = "button";
        b.addEventListener("click", function () {
          if (w === words[placed]) {           // correct next word
            placed += 1;
            const done = document.createElement("span");
            done.className = "word-chip"; done.textContent = w;
            answer.appendChild(done);
            b.remove();
            if (placed === words.length) { result.hidden = false; celebrate(answer, 16); }
          } else {                              // wrong — gentle shake
            b.classList.add("wrong");
            setTimeout(() => b.classList.remove("wrong"), 350);
          }
        });
        pool.appendChild(b);
      });
    }
    function shuffled(arr) {
      const a = arr.slice();
      for (let i = a.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [a[i], a[j]] = [a[j], a[i]];
      }
      // avoid accidentally presenting the solved order
      return a.join() === arr.join() && a.length > 2 ? shuffled(arr) : a;
    }
    root.querySelector(".scramble-reset").addEventListener("click", build);
    build();
  });

  /* ---------------- quiz ---------------- */
  document.querySelectorAll(".quiz").forEach(function (root) {
    const questions = JSON.parse(root.dataset.quiz);
    const area = root.querySelector(".quiz-area");
    const scoreEl = root.querySelector(".quiz-score");
    let correct = 0, answered = 0;

    questions.forEach(function (q) {
      const qEl = document.createElement("p");
      qEl.className = "quiz-q";
      qEl.textContent = pick(q.q);
      area.appendChild(qEl);
      let locked = false;
      pick(q.options).forEach(function (opt, idx) {
        const b = document.createElement("button");
        b.className = "quiz-opt"; b.type = "button"; b.textContent = opt;
        b.addEventListener("click", function () {
          if (locked) return;
          locked = true; answered += 1;
          if (idx === q.answer) { b.classList.add("correct"); correct += 1; }
          else { b.classList.add("incorrect"); }
          markCorrect(qEl, q.answer);   // always reveal the right answer
          if (answered === questions.length) {
            quizScore = correct;
            scoreEl.hidden = false;
            if (correct === questions.length) celebrate(scoreEl, 18);
            scoreEl.textContent = (window.LANG === "es")
              ? "Tu puntuación: " + correct + " de " + questions.length + " ⭐"
              : "Your score: " + correct + " of " + questions.length + " ⭐";
          }
        });
        b.dataset.q = qEl.textContent; b.dataset.idx = idx;
        area.appendChild(b);
      });
    });

    function markCorrect(qEl, answerIdx) {
      let n = qEl.nextElementSibling;
      while (n && n.classList.contains("quiz-opt")) {
        if (parseInt(n.dataset.idx, 10) === answerIdx) n.classList.add("correct");
        n = n.nextElementSibling;
      }
    }
  });

  function pick(field) {
    if (field && typeof field === "object" && !Array.isArray(field)) {
      return field[window.LANG] || field.en;
    }
    return field;
  }

  /* ---------------- completion ---------------- */
  const btn = document.getElementById("complete-btn");
  if (btn) {
    btn.addEventListener("click", function () {
      fetch("/api/complete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ series_id: seriesId, lesson_id: lessonId,
                               quiz_score: quizScore })
      }).then(r => r.json()).then(function (d) {
        if (d.ok) {
          btn.hidden = true;
          var panel = document.getElementById("complete-panel");
          panel.hidden = false;

          // XP award display
          var xpEl = document.getElementById("xp-award");
          if (xpEl && d.xp_earned > 0) {
            xpEl.textContent = "+" + d.xp_earned + " XP  ·  Total: " + d.total_xp + " XP";
            xpEl.className = "xp-award pop-in";
          }

          // rank up
          var rankEl = document.getElementById("rank-award");
          if (rankEl && d.rank_up) {
            rankEl.textContent = "🎉 New rank: " + d.rank_emoji + " " + d.rank;
            rankEl.className = "rank-award rank-up pop-in";
          }

          // streak
          if (d.streak > 1) {
            var chip = document.querySelector(".streak-chip");
            if (chip) chip.textContent = "🔥 " + d.streak + " day streak";
          }

          // series complete certificate link
          if (d.series_complete) {
            var sl = document.getElementById("series-cert-link");
            if (sl) sl.hidden = false;
            celebrate(panel, 40);
          if (d.new_badges && d.new_badges.length) {
            showBadges(d.new_badges, panel);
          }
          } else {
            celebrate(panel, 24);
          if (d.new_badges && d.new_badges.length) {
            showBadges(d.new_badges, panel);
          }
          }
        }
      });
    });
  }
})();
