/* LuzKids games.js — armour builder, typing challenge, AI companion.
   No external dependencies. AI uses Groq free tier (zero cost). */
(function () {
"use strict";

var LANG = window.LANG || "en";
var SERIES_ID = document.querySelector(".lesson") ? document.querySelector(".lesson").dataset.series : "";
var LESSON_ID  = document.querySelector(".lesson") ? document.querySelector(".lesson").dataset.lesson : "";

/* ================================================================
   1. ARMOUR BUILDER GAME
   Click a piece → it gets selected → click the right soldier zone → it snaps in
   ================================================================ */
var armourEl = document.getElementById("armour-game");
if (armourEl) {
  var pieces   = JSON.parse(armourEl.dataset.pieces || "[]");
  var pool     = document.getElementById("armour-pool");
  var complete = document.getElementById("armour-complete");
  var meaningBox = document.getElementById("armour-meaning");
  var meaningTitle = document.getElementById("armour-meaning-title");
  var meaningText  = document.getElementById("armour-meaning-text");
  var selected = null;
  var placed   = {};

  function pick(p, lang) { return (p[lang] || p["en"]); }

  // Build piece cards
  pieces.forEach(function(piece) {
    var card = document.createElement("div");
    card.className = "armour-piece";
    card.dataset.id = piece.id;
    card.dataset.zone = piece.zone;
    card.innerHTML = "<span class='armour-icon'>" + piece.icon + "</span><span>" + pick(piece, LANG) + "</span>";
    card.addEventListener("click", function() {
      if (placed[piece.id]) return;
      if (selected === card) { selected = null; card.classList.remove("selected"); return; }
      if (selected) selected.classList.remove("selected");
      selected = card;
      card.classList.add("selected");
    });
    pool.appendChild(card);
  });

  // Zone click handlers
  document.querySelectorAll(".soldier-zone").forEach(function(zone) {
    zone.addEventListener("click", function() {
      if (!selected) return;
      var targetZone = zone.dataset.zone;
      var piece = pieces.find(function(p) { return p.id === selected.dataset.id; });
      if (targetZone === selected.dataset.zone) {
        // Correct!
        zone.innerHTML = "<span class='armour-placed'>" + piece.icon + "<br><small>" + pick(piece, LANG) + "</small></span>";
        zone.classList.add("filled");
        placed[piece.id] = true;
        selected.classList.add("done");
        selected.classList.remove("selected");
        selected = null;

        // Show meaning
        meaningBox.hidden = false;
        meaningTitle.textContent = piece.icon + " " + pick(piece, LANG);
        meaningText.textContent = pick(piece.meaning, LANG);

        // Check all placed
        if (Object.keys(placed).length === pieces.length) {
          complete.hidden = false;
          complete.classList.add("armour-win");
          // star burst
          if (window.celebrate) celebrate(complete, 28);
        }
      } else {
        // Wrong zone — shake the zone
        zone.classList.add("sz-wrong");
        setTimeout(function() { zone.classList.remove("sz-wrong"); }, 400);
        selected.classList.add("wrong-flash");
        setTimeout(function() { selected && selected.classList.remove("wrong-flash"); }, 400);
      }
    });
  });
}

/* ================================================================
   2. MEMORY VERSE TYPING CHALLENGE
   Toggle button reveals a textarea; check button grades accuracy.
   ================================================================ */
document.querySelectorAll(".typing-toggle").forEach(function(btn) {
  btn.addEventListener("click", function() {
    var targetId = btn.dataset.target;
    var box = document.getElementById(targetId);
    if (!box) return;
    box.hidden = !box.hidden;
    if (!box.hidden) box.querySelector(".typing-input").focus();
  });
});

document.querySelectorAll(".typing-check").forEach(function(btn) {
  btn.addEventListener("click", function() {
    var box = btn.closest(".typing-challenge");
    var input = box.querySelector(".typing-input");
    var result = box.querySelector(".typing-result");
    // Get the correct verse text from the blockquote in the same verse-block section
    var verseBlock = btn.closest(".verse-block");
    var quote = verseBlock ? verseBlock.querySelector("blockquote") : null;
    if (!quote) return;
    var correct = quote.textContent.replace(/["""]/g,"").split("\n")[0].trim().toLowerCase();
    var typed = input.value.trim().toLowerCase();

    // Simple word-match scoring
    var correctWords = correct.split(/\s+/).filter(Boolean);
    var typedWords   = typed.split(/\s+/).filter(Boolean);
    var hits = 0;
    correctWords.forEach(function(w, i) {
      if (typedWords[i] && typedWords[i].replace(/[^a-záéíóúàâêîôûäëïöü]/gi,"") === w.replace(/[^a-záéíóúàâêîôûäëïöü]/gi,"")) hits++;
    });
    var pct = correctWords.length > 0 ? Math.round(hits * 100 / correctWords.length) : 0;

    result.hidden = false;
    if (pct === 100) {
      result.className = "typing-result result-perfect";
      result.textContent = {"en":"🎉 Perfect! You know it by heart!","es":"🎉 ¡Perfecto! ¡Lo sabes de memoria!","fr":"🎉 Parfait ! Tu le sais par cœur !"}[LANG] || "🎉 Perfect!";
      if (window.celebrate) celebrate(result, 18);
    } else if (pct >= 70) {
      result.className = "typing-result result-good";
      result.textContent = ({"en":"✅ Great — " + pct + "% correct. Keep practising!","es":"✅ ¡Genial — " + pct + "% correcto. ¡Sigue practicando!","fr":"✅ Super — " + pct + "% correct. Continue !"}[LANG] || "✅ " + pct + "%");
    } else {
      result.className = "typing-result result-try";
      result.textContent = ({"en":"Keep going — " + pct + "% correct. Read it again and try!","es":"Sigue intentando — " + pct + "% correcto. ¡Léelo de nuevo!","fr":"Continue — " + pct + "% correct. Relis et essaie !"}[LANG] || pct + "%");
    }
  });
});

/* ================================================================
   3. AI BIBLE COMPANION  (Groq free tier — zero cost)
   The endpoint /api/ask proxies to Groq on the server side.
   Rate-limited to 3 questions per lesson session.
   ================================================================ */
var askBtn  = document.getElementById("ai-ask-btn");
var askInput = document.getElementById("ai-question");
var answerBox = document.getElementById("ai-answer");
var limitMsg  = document.getElementById("ai-limit");
var questionsLeft = 3;

function updateLimit() {
  if (limitMsg) {
    limitMsg.style.display = "block";
    limitMsg.textContent = questionsLeft > 0
      ? ({"en": questionsLeft + " question(s) remaining this session",
          "es": questionsLeft + " pregunta(s) restante(s) esta sesión",
          "fr": questionsLeft + " question(s) restante(s) cette session"}[LANG] || "")
      : ({"en": "Question limit reached — come back next time!",
          "es": "Límite de preguntas alcanzado — ¡vuelve la próxima vez!",
          "fr": "Limite atteinte — reviens la prochaine fois !"}[LANG] || "");
  }
}
updateLimit();

if (askBtn) {
  askBtn.addEventListener("click", function() {
    var q = (askInput ? askInput.value.trim() : "");
    if (!q || questionsLeft <= 0) return;
    questionsLeft--;
    updateLimit();
    askBtn.disabled = true;
    askBtn.textContent = {"en":"Thinking...","es":"Pensando...","fr":"Je réfléchis..."}[LANG] || "...";
    if (answerBox) { answerBox.hidden = false; answerBox.textContent = "⏳ ..."; }

    fetch("/api/ask", {
      method: "POST",
      headers: {"Content-Type": "application/json",
                "X-CSRFToken": document.querySelector('meta[name="csrf-token"]').content},
      body: JSON.stringify({question: q, series_id: SERIES_ID, lesson_id: LESSON_ID, lang: LANG})
    }).then(function(r) { return r.json(); }).then(function(d) {
      if (d.rate_limited) {
        questionsLeft++;
        updateLimit();
      }
      if (answerBox) {
        answerBox.hidden = false;
        answerBox.textContent = d.answer || d.error || "Sorry, I couldn't answer that right now.";
      }
    }).catch(function() {
      if (answerBox) { answerBox.textContent = "Sorry — something went wrong. Try again!"; }
    }).finally(function() {
      if (askBtn) {
        askBtn.disabled = questionsLeft <= 0;
        askBtn.textContent = {"en":"Ask","es":"Preguntar","fr":"Demander"}[LANG] || "Ask";
      }
    });
  });

  // Enter key submits
  if (askInput) {
    askInput.addEventListener("keydown", function(e) { if (e.key === "Enter") askBtn.click(); });
  }
}

})();

/* ================================================================
   4. WALL DEMOLISHER GAME (Lesson 6)
   ================================================================ */
var wallEl = document.querySelector(".wall-game");
if (wallEl) {
  var bricks = JSON.parse(wallEl.dataset.bricks || "[]");
  var reveal = JSON.parse(wallEl.dataset.reveal || "{}");
  var wlang = wallEl.dataset.lang || "en";
  var pool = document.getElementById("wall-bricks");
  var revEl = document.getElementById("wall-reveal");
  var tapped = 0;

  bricks.forEach(function(brick) {
    var b = document.createElement("div");
    b.className = "wall-brick";
    b.textContent = brick[wlang] || brick["en"];
    b.addEventListener("click", function() {
      if (b.classList.contains("broken")) return;
      b.classList.add("broken");
      tapped++;
      setTimeout(function() { b.style.display = "none"; }, 400);
      if (tapped === bricks.length) {
        setTimeout(function() {
          revEl.hidden = false;
          revEl.textContent = reveal[wlang] || reveal["en"];
          revEl.classList.add("wall-reveal-show");
          if (window.celebrate) celebrate(revEl, 22);
        }, 600);
      }
    });
    pool.appendChild(b);
  });
}

/* ================================================================
   5. LIGHT SORTER GAME (Lesson 12)
   ================================================================ */
var sorterEl = document.querySelector(".light-sorter");
if (sorterEl) {
  var sitems = JSON.parse(sorterEl.dataset.items || "[]");
  var slang = sorterEl.dataset.lang || "en";
  var spool = document.getElementById("sorter-pool");
  var lcount = document.getElementById("light-count");
  var dcount = document.getElementById("dark-count");
  var sresult = document.getElementById("sorter-result");
  var sorted = 0;
  var correct = 0;

  // shuffle
  for (var i = sitems.length - 1; i > 0; i--) {
    var j = Math.floor(Math.random() * (i + 1));
    var tmp = sitems[i]; sitems[i] = sitems[j]; sitems[j] = tmp;
  }

  sitems.forEach(function(item) {
    var card = document.createElement("div");
    card.className = "sorter-card";
    card.textContent = item[slang] || item["en"];
    card.dataset.light = item.light ? "1" : "0";

    card.addEventListener("click", function() {
      if (card.classList.contains("sorted")) return;
      // Show light/dark choice buttons
      var btns = document.createElement("div");
      btns.className = "sorter-choice";
      ["light", "dark"].forEach(function(choice) {
        var btn = document.createElement("button");
        btn.textContent = choice === "light" ? "☀️" : "🌑";
        btn.className = "sorter-btn";
        btn.addEventListener("click", function(e) {
          e.stopPropagation();
          var isLight = (choice === "light");
          var wasCorrect = (isLight === (card.dataset.light === "1"));
          card.classList.add("sorted");
          card.classList.add(wasCorrect ? "sort-correct" : "sort-wrong");
          card.querySelector(".sorter-choice") && card.querySelector(".sorter-choice").remove();
          if (wasCorrect) {
            correct++;
            if (isLight) { lcount.textContent = parseInt(lcount.textContent)+1; }
            else { dcount.textContent = parseInt(dcount.textContent)+1; }
          } else {
            card.classList.add("shake");
          }
          sorted++;
          if (sorted === sitems.length) {
            sresult.hidden = false;
            if (correct === sitems.length && window.celebrate) celebrate(sresult, 16);
          }
        });
        btns.appendChild(btn);
      });
      card.appendChild(btns);
    });
    spool.appendChild(card);
  });
}
