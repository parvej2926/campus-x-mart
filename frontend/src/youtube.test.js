import test from "node:test";
import assert from "node:assert/strict";
import { youtubeEmbedUrl } from "./youtube.js";

test("normalizes supported YouTube URL formats to privacy-enhanced embeds", () => {
  assert.equal(youtubeEmbedUrl("https://youtu.be/dQw4w9WgXcQ"), "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ?rel=0");
  assert.equal(youtubeEmbedUrl("https://www.youtube.com/watch?v=dQw4w9WgXcQ"), "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ?rel=0");
  assert.equal(youtubeEmbedUrl("https://youtube.com/shorts/dQw4w9WgXcQ"), "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ?rel=0");
});

test("rejects unsupported hosts and malformed video IDs", () => {
  assert.equal(youtubeEmbedUrl("https://youtube.com.evil.example/watch?v=dQw4w9WgXcQ"), null);
  assert.equal(youtubeEmbedUrl("https://example.com/dQw4w9WgXcQ"), null);
  assert.equal(youtubeEmbedUrl("https://youtube.com/watch?v=short"), null);
});
