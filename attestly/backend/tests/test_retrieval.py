from app import retrieval


def _bank():
    return [
        {"id": 1, "question": "Do you enforce multi-factor authentication (MFA) for all employees?",
         "answer": "Yes, MFA everywhere.", "category": "access"},
        {"id": 2, "question": "Is customer data encrypted at rest?",
         "answer": "Yes, AES-256.", "category": "encryption"},
        {"id": 3, "question": "Do you have a SOC 2 Type II report?",
         "answer": "Yes, available under NDA.", "category": "compliance"},
    ]


def test_exact_question_is_reusable():
    matches = retrieval.rank("Is customer data encrypted at rest?", _bank())
    best = retrieval.best_reusable(matches)
    assert best is not None
    assert best.answer_id == 2
    assert best.score >= 99


def test_reworded_question_matches_right_entry_as_top():
    matches = retrieval.rank("Do you require MFA for staff accounts?", _bank())
    assert matches[0].answer_id == 1  # top match is the MFA entry


def test_unrelated_question_is_not_reusable():
    matches = retrieval.rank("What is your company's annual revenue?", _bank())
    assert retrieval.best_reusable(matches) is None


def test_empty_bank_returns_no_matches():
    assert retrieval.rank("anything", []) == []
