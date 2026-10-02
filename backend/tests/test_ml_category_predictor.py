from ml.category_predictor import predict_category


def test_predicts_books_from_whole_word_keywords():
    assert predict_category("Used CSE textbook with lecture notes") == "Books"


def test_does_not_match_keyword_fragments_inside_unrelated_words():
    assert predict_category("phonecase for campus") == "Others"
    assert predict_category("chairlift for hills") == "Others"


def test_returns_unrecognized_text_as_others():
    assert predict_category("A lovely campus-market keepsake") == "Others"
