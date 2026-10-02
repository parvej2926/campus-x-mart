import test from "node:test";
import assert from "node:assert/strict";
import { suggestCategory } from "./categorySuggestion.js";

test("suggests a category from whole words in item text", () => {
  const suggestion = suggestCategory("Used CSE textbook with lecture notes");
  assert.equal(suggestion.category, "Books");
  assert.deepEqual(suggestion.matchedKeywords, ["textbook", "notes"]);
  assert.equal(suggestion.source, "rule-based");
});

test("does not match keyword fragments inside unrelated words", () => {
  assert.equal(suggestCategory("phonecase for campus"), null);
});

test("returns no suggestion when there are no known category terms", () => {
  assert.equal(suggestCategory("A lovely campus-market keepsake"), null);
});

test("resolves category ties in a stable order", () => {
  assert.equal(suggestCategory("Book chair").category, "Books");
});
