import test from "node:test";
import assert from "node:assert/strict";
import { API, api } from "./api.js";

test("API requests target the local backend", () => {
  assert.equal(API, "http://localhost:8000");
});

test("API requests use cookie credentials, attach CSRF tokens, and never send bearer tokens", async (t) => {
  const originalFetch = globalThis.fetch;
  const originalDocument = globalThis.document;
  t.after(() => {
    globalThis.fetch = originalFetch;
    if (originalDocument === undefined) delete globalThis.document;
    else globalThis.document = originalDocument;
  });

  globalThis.document = { cookie: "campus_x_mart_csrf=csrf-value" };
  let captured;
  globalThis.fetch = async (url, options) => {
    captured = { url, options };
    return new Response(JSON.stringify({ ok: true }), { status: 200 });
  };

  assert.deepEqual(await api("/api/example", "POST", { value: 1 }), { ok: true });
  assert.equal(captured.options.credentials, "include");
  assert.equal(captured.options.headers.get("X-CSRF-Token"), "csrf-value");
  assert.equal(captured.options.headers.has("Authorization"), false);
  assert.equal(captured.options.body, JSON.stringify({ value: 1 }));
});

test("API requests refresh an expired cookie session once and retry", async (t) => {
  const originalFetch = globalThis.fetch;
  const originalDocument = globalThis.document;
  t.after(() => {
    globalThis.fetch = originalFetch;
    if (originalDocument === undefined) delete globalThis.document;
    else globalThis.document = originalDocument;
  });

  globalThis.document = { cookie: "campus_x_mart_csrf=csrf-value" };
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    if (calls.length === 1) return new Response("{}", { status: 401 });
    if (url.endsWith("/api/auth/refresh")) return new Response("{}", { status: 200 });
    return new Response(JSON.stringify({ items: [] }), { status: 200 });
  };

  assert.deepEqual(await api("/api/items"), { items: [] });
  assert.equal(calls.length, 3);
  assert.ok(calls[1].url.endsWith("/api/auth/refresh"));
  assert.equal(calls[1].options.headers.get("X-CSRF-Token"), "csrf-value");
  assert.ok(calls[2].url.endsWith("/api/items"));
});
