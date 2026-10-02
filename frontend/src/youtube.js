const YOUTUBE_HOSTS = new Set([
  "youtu.be",
  "www.youtu.be",
  "youtube.com",
  "www.youtube.com",
  "m.youtube.com",
  "youtube-nocookie.com",
  "www.youtube-nocookie.com",
]);
const VIDEO_ID_PATTERN = /^[A-Za-z0-9_-]{11}$/;

export function youtubeEmbedUrl(value) {
  try {
    const url = new URL(value);
    const hostname = url.hostname.toLowerCase().replace(/\.$/, "");
    if (!YOUTUBE_HOSTS.has(hostname) || !["http:", "https:"].includes(url.protocol) || url.username || url.password) return null;

    const segments = url.pathname.split("/").filter(Boolean);
    let videoId = null;
    if (hostname === "youtu.be" || hostname === "www.youtu.be") {
      videoId = segments[0];
    } else if (url.pathname === "/watch") {
      videoId = url.searchParams.get("v");
    } else if (segments.length >= 2 && ["embed", "shorts", "live"].includes(segments[0])) {
      videoId = segments[1];
    }

    if (!VIDEO_ID_PATTERN.test(videoId || "")) return null;
    return `https://www.youtube-nocookie.com/embed/${videoId}?rel=0`;
  } catch {
    return null;
  }
}
