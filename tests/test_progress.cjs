// On-device progress logic (static/js/progress.js). Run: node --test tests/
const test = require("node:test");
const assert = require("node:assert/strict");
const P = require("../static/js/progress.js");

const RANKS = [[0, "Seeker", "🔍"], [100, "Believer", "✝️"], [300, "Growing", "🌱"],
  [2200, "Jesus' Arrow", "⚡"]];
const LESSONS = ["lesson01", "lesson02"];
const day = (s) => new Date(s + "T12:00:00");

function done(profile, lessonId, opts = {}) {
  return P.completeLesson(profile, Object.assign({ seriesId: "ephesians", lessonId,
    seriesLessons: LESSONS, totalQ: 3, score: 3 }, opts), RANKS, opts.now || day("2026-11-01"));
}

test("completing a lesson awards XP, perfect-quiz bonus and first badges", () => {
  const p = P.newProfile("Ada", "🦁");
  const r = done(p, "lesson01");
  assert.equal(r.xp_earned, 75);
  assert.equal(p.xp, 75);
  assert.equal(r.streak, 1);
  assert.deepEqual(r.new_badges.sort(), ["first_lamp", "quiz_hero"]);
  assert.equal(r.series_complete, false);
});

test("repeating a lesson gives no extra XP", () => {
  const p = P.newProfile("Ada");
  done(p, "lesson01");
  const r = done(p, "lesson01");
  assert.equal(r.xp_earned, 0);
  assert.equal(p.xp, 75);
});

test("lessons that are not in the series are rejected", () => {
  const p = P.newProfile("Ada");
  assert.equal(done(p, "made-up"), null);
  assert.equal(p.xp, 0);
});

test("quiz scores are capped at the real number of questions", () => {
  const p = P.newProfile("Ada");
  const r = done(p, "lesson01", { score: 99 });
  assert.equal(p.done["ephesians/lesson01"].score, 3);
  assert.equal(r.xp_earned, 75);
});

test("finishing every lesson completes the series and earns graduate", () => {
  const p = P.newProfile("Ada");
  done(p, "lesson01");
  const r = done(p, "lesson02", { score: 1 });
  assert.equal(r.series_complete, true);
  assert.ok(r.new_badges.includes("graduate"));
  assert.equal(r.xp_earned, 50);
});

test("streak grows on consecutive days and resets after a gap", () => {
  const p = P.newProfile("Ada");
  const L = ["a", "b", "c", "d"];
  const go = (id, d) => P.completeLesson(p, { seriesId: "s", lessonId: id, seriesLessons: L, totalQ: 0 }, RANKS, day(d));
  go("a", "2026-11-01"); go("b", "2026-11-02");
  assert.equal(go("c", "2026-11-03").streak, 3);
  assert.ok(p.badges.on_fire);
  assert.equal(go("d", "2026-11-06").streak, 1);
  assert.equal(p.longest, 3);
});

test("rank-up is reported", () => {
  const p = P.newProfile("Ada");
  p.xp = 90;
  const r = done(p, "lesson01");
  assert.equal(r.rank_up, true);
  assert.equal(r.rank, "Believer");
});

test("loading a progress file keeps only known, clean fields", () => {
  const raw = { active: "pabc", evil: "<script>", profiles: [
    { id: "pabc", name: "  Ben\u0000  ", avatar: "💣", xp: "5000", streak: 2, longest: 1,
      badges: { first_lamp: "2026-10-01", "bad key!": "x" },
      done: { "ephesians/lesson01": { score: 3, at: "2026-10-01" }, "../../x": {} },
      mission: [{ name: "J", notes: "n", prayed: 1, extra: "dropped" }], password: "nope" },
    { name: "" }] };
  const st = P.sanitizeState(raw);
  assert.equal(st.profiles.length, 1);
  const p = st.profiles[0];
  assert.equal(p.name, "Ben");
  assert.equal(p.avatar, "🌟");
  assert.equal(p.xp, 5000);
  assert.equal(p.longest, 2);
  assert.deepEqual(Object.keys(p.badges), ["first_lamp"]);
  assert.deepEqual(Object.keys(p.done), ["ephesians/lesson01"]);
  assert.equal(p.mission[0].prayed, true);
  assert.equal("extra" in p.mission[0], false);
  assert.equal("password" in p, false);
  assert.equal("evil" in st, false);
  assert.equal(st.active, "pabc");
});

test("files that are not progress files are refused", () => {
  assert.equal(P.sanitizeState(null), null);
  assert.equal(P.sanitizeState({ profiles: "x" }), null);
  assert.equal(P.sanitizeState([1, 2]), null);
});

test("names are trimmed to 40 characters", () => {
  assert.equal(P.newProfile("x".repeat(100)).name.length, 40);
});
