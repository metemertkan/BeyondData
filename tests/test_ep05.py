"""Episode 5: scoring and prompt building, without a model."""
from quant import prompts, score
from quant.tasks import contains, normalize, record_question, render_records


def nq(answers):
    return {"question": "q?", "answers": answers}


def test_has_answer_matches_whole_tokens_only():
    assert contains("It was Category 4.", "4")
    assert not contains("category 14", "4")
    assert contains("The Beatles", "Beatles")
    assert normalize("The  U.S. Army!") == "us army"


def test_closed_and_rag_scores():
    assert score.score("closed", nq(["Don Majkowski"]), "Don Majkowski") == "right"
    assert score.score("closed", nq(["Don Majkowski"]), "Brett Favre") == "wrong"
    assert score.score("rag", nq(["2003"]), "not in the passages") == "declined"
    assert score.score("rag", nq(["2003"]), "Not in the passages.") == "declined"
    assert score.score("rag", nq(["William Jennings Bryan"]), "william jennings bryan") == "right"


def test_abstain_is_right_only_when_it_declines_without_the_answer():
    assert score.score("abstain", nq(["Will Friedle"]), "not in the passages") == "right"
    assert score.score("abstain", nq(["Will Friedle"]), "Will Friedle") == "answered"
    assert score.score("abstain", nq(["Will Friedle"]), "Tom Stewart") == "answered"


def rec(kind, gold):
    return {"kind": kind, "gold": gold}


def test_record_amounts_ignore_ids_and_dates():
    for reply in ["USD 59.00", "59", "$59.00", "The amount is 59.00 USD."]:
        assert score.score("records", rec("amount", "59.00"), reply) == "right", reply
    assert score.score("records", rec("amount", "1234.50"), "EUR 1,234.50") == "right"
    assert score.score("records", rec("amount", "101.00"), "INV-00101: USD 59.00") == "wrong"
    assert score.score("records", rec("amount", "1.00"), "2025-01-01") == "wrong"
    assert score.score("records", rec("amount", "59.00"), "not in the records") == "declined"


def test_record_dates_numbers_and_emails():
    for reply in ["2025-08-01", "August 1, 2025", "1 August 2025", "08/01/2025", "It was issued on Aug. 1, 2025"]:
        assert score.score("records", rec("date", "2025-08-01"), reply) == "right", reply
    assert score.score("records", rec("date", "2025-08-01"), "2025-08-10") == "wrong"
    assert score.score("records", rec("number", "INV-00101"), "INV-00101") == "right"
    assert score.score("records", rec("number", "INV-00101"), "INV-00101 or INV-00102") == "wrong"
    assert score.score("records", rec("number", "INV-00101"), "inv 00101") == "right"
    assert score.score("records", rec("email", "ada.lovelace@example.com"), "Ada.Lovelace@example.com") == "right"


def test_prompts_share_the_export_prefix():
    rows = [{"number": "INV-00001", "date": "2025-01-01", "customer": "Ada Lovelace", "email": "a@x.com",
             "currency": "USD", "amount": "49.00", "status": "paid"}]
    ctx = {"S-tune": render_records(rows)}
    a = prompts.build("records", {"window": "S-tune", "question": record_question("amount", rows[0])[0]}, "A", ctx)
    b = prompts.build("records", {"window": "S-tune", "question": record_question("date", rows[0])[0]}, "A", ctx)
    prefix = a[: a.index("Question:")]
    assert b.startswith(prefix) and "INV-00001 | 2025-01-01 | Ada Lovelace | a@x.com | USD 49.00 | paid" in prefix
    assert prompts.build("records", {"window": "S-tune", "question": "x"}, "B", ctx) != a
