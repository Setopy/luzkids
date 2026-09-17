const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");

const script = fs.readFileSync(path.join(__dirname, "../static/js/games.js"), "utf8");
const flush = () => new Promise(resolve => setImmediate(resolve));

function page(fetchImpl) {
  const handlers = {};
  const button = { disabled: false, textContent: "Ask",
    addEventListener: (name, fn) => { handlers[name] = fn; },
    click: () => { if (!button.disabled) handlers.click(); } };
  const input = { value: "Why did Paul write this letter?", addEventListener() {} };
  const answer = { hidden: true, textContent: "" };
  const limit = { style: {}, textContent: "" };
  const elements = { "ai-ask-btn": button, "ai-question": input,
    "ai-answer": answer, "ai-limit": limit };
  const calls = [], timers = new Map();
  let timerId = 0;
  const context = {
    window: { LANG: "en" }, AbortController,
    document: {
      getElementById: id => elements[id] || null,
      querySelectorAll: () => [],
      querySelector: selector => selector === ".lesson"
        ? { dataset: { series: "ephesians", lesson: "lesson01" } }
        : selector === 'meta[name="csrf-token"]' ? { content: "csrf-test" } : null,
    },
    fetch: (url, options) => { calls.push({url, options}); return fetchImpl(url, options); },
    setTimeout: fn => { timers.set(++timerId, fn); return timerId; },
    clearTimeout: id => timers.delete(id),
  };
  vm.runInNewContext(script, context, { filename: "games.js" });
  return { button, input, answer, limit, calls, timers, handlers };
}

const reply = (ok, body) => Promise.resolve({ ok, json: () => Promise.resolve(body) });

test("successful answer sends lesson and CSRF context and consumes one question", async () => {
  const p = page(() => reply(true, {ok: true, answer: "God loves us."}));
  p.button.click();
  await flush();
  assert.equal(p.answer.textContent, "God loves us.");
  assert.match(p.limit.textContent, /^2 question/);
  assert.equal(p.button.disabled, false);
  assert.equal(p.timers.size, 0);
  assert.equal(p.calls[0].url, "/api/ask");
  assert.equal(p.calls[0].options.headers["X-CSRFToken"], "csrf-test");
  assert.deepEqual(JSON.parse(p.calls[0].options.body), {
    question: p.input.value, series_id: "ephesians", lesson_id: "lesson01", lang: "en"
  });
});

for (const [name, ok, body] of [
  ["provider unavailable", false, {ok: false, answer: "Try again."}],
  ["login expired", false, {ok: false, answer: "Please log in."}],
  ["rate limit", false, {ok: false, rate_limited: true, answer: "Take a break."}],
  ["malformed success", true, {ok: true}],
]) {
  test(name + " does not consume a question", async () => {
    const p = page(() => reply(ok, body));
    p.button.click();
    await flush();
    assert.match(p.limit.textContent, /^3 question/);
    assert.equal(p.button.disabled, false);
    assert.equal(p.timers.size, 0);
  });
}

test("network and non-JSON errors leave all questions available", async () => {
  for (const fetchImpl of [
    () => Promise.reject(new Error("offline")),
    () => Promise.resolve({ok: false, json: () => Promise.reject(new SyntaxError("HTML"))}),
  ]) {
    const p = page(fetchImpl);
    p.button.click();
    await flush();
    assert.match(p.limit.textContent, /^3 question/);
    assert.match(p.answer.textContent, /Try again/);
    assert.equal(p.button.disabled, false);
  }
});

test("timeout aborts a stalled request and restores the button", async () => {
  const p = page((url, options) => new Promise((resolve, reject) => {
    options.signal.addEventListener("abort", () => reject(new Error("aborted")));
  }));
  p.button.click();
  assert.equal(p.button.disabled, true);
  [...p.timers.values()][0]();
  await flush();
  assert.equal(p.calls[0].options.signal.aborted, true);
  assert.equal(p.button.disabled, false);
  assert.match(p.limit.textContent, /^3 question/);
  assert.equal(p.timers.size, 0);
});

test("duplicate submissions are ignored while a request is pending", async () => {
  let resolve;
  const p = page(() => new Promise(done => { resolve = done; }));
  p.handlers.click();
  p.handlers.click();
  assert.equal(p.calls.length, 1);
  resolve({ok: true, json: () => Promise.resolve({ok: true, answer: "An answer."})});
  await flush();
  assert.match(p.limit.textContent, /^2 question/);
});

test("three successful answers exhaust the session allowance", async () => {
  const p = page(() => reply(true, {ok: true, answer: "An answer."}));
  for (let i = 0; i < 3; i++) { p.button.click(); await flush(); }
  assert.equal(p.button.disabled, true);
  assert.match(p.limit.textContent, /Question limit reached/);
  p.handlers.click();
  assert.equal(p.calls.length, 3);
});

