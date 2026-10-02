from typing import Optional

class SimpleCategoryModel:
    def __init__(self):
        self.labels = ["Books", "Electronics", "Furniture", "Bikes", "Clothes", "Others"]
        self.keyword_map = {
            "Books": ["book", "textbook", "notebook", "notes", "study"],
            "Electronics": ["laptop", "phone", "charger", "keyboard", "mouse", "headset", "tablet"],
            "Furniture": ["chair", "desk", "table", "lamp", "shelf", "cabinet"],
            "Bikes": ["bike", "cycle", "helmet", "bicycle"],
            "Clothes": ["shirt", "hoodie", "jeans", "shoes", "jacket", "dress"],
            "Others": ["misc", "general", "other", "tool", "accessory"],
        }

    def predict(self, text: str):
        normalized = (text or "").strip().lower()
        if not normalized:
            return "Others"

        best_label = "Others"
        best_score = 0
        for label, keywords in self.keyword_map.items():
            score = sum(1 for keyword in keywords if keyword in normalized)
            if score > best_score:
                best_score = score
                best_label = label
        return best_label

def load_model(path: Optional[str] = None):
    return SimpleCategoryModel()
