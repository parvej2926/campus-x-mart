const CATEGORY_RULES = [
  ["Books", ["book", "textbook", "notes", "novel", "study", "exam", "course"]],
  ["Electronics", ["laptop", "phone", "charger", "keyboard", "mouse", "headphone", "tablet"]],
  ["Furniture", ["chair", "desk", "table", "bed", "lamp", "shelf", "cabinet"]],
  ["Bikes", ["bike", "cycle", "helmet", "bicycle", "mountain bike"]],
  ["Clothes", ["shirt", "jacket", "jeans", "shoe", "dress", "hoodie", "sneaker"]],
  ["Others", ["misc", "general", "other", "accessory", "tool"]],
];

function matchesKeyword(text, keyword) {
  const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`\\b${escaped}(?:s|es)?\\b`).test(text);
}

export function suggestCategory(itemText) {
  const text = ` ${String(itemText || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim()} `;
  if (!text.trim()) return null;

  let bestSuggestion = null;
  for (const [category, keywords] of CATEGORY_RULES) {
    const matchedKeywords = keywords.filter((keyword) => matchesKeyword(text, keyword));
    if (matchedKeywords.length > (bestSuggestion?.matchedKeywords.length || 0)) {
      bestSuggestion = { category, matchedKeywords, source: "rule-based" };
    }
  }

  return bestSuggestion;
}
