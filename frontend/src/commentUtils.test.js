import test from "node:test";
import assert from "node:assert/strict";
import { mergeCommentList } from "./commentUtils.js";

test("mergeCommentList keeps the latest unique comments without duplication", () => {
  const existing = [
    { comment_id: 1, comment_text: "first" },
    { comment_id: 2, comment_text: "second" },
  ];

  const next = [
    { comment_id: 2, comment_text: "second" },
    { comment_id: 3, comment_text: "third" },
  ];

  assert.deepEqual(mergeCommentList(existing, next), [
    { comment_id: 1, comment_text: "first" },
    { comment_id: 2, comment_text: "second" },
    { comment_id: 3, comment_text: "third" },
  ]);
});

test("mergeCommentList ignores incomplete entries", () => {
  assert.deepEqual(mergeCommentList([{ comment_id: 1, comment_text: "ok" }], [null, { comment_id: 2, comment_text: "later" }]), [
    { comment_id: 1, comment_text: "ok" },
    { comment_id: 2, comment_text: "later" },
  ]);
});
