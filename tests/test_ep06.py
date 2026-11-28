"""Episode 6: scoring replies and classifying index entries, without databases or a model."""
from sync import score
from sync.kb import Fact, render
from sync.record import chunk_texts


def q(kind, right, stale, fact_kind, fact="x.y", qkind="changed"):
    return {"kind": qkind, "fact": fact, "right": right, "stale": stale, "fact_kind": fact_kind}


def test_amounts_need_their_currency_and_whole_number():
    x = q("changed", "$44", ["$49"], "usd")
    assert score.score(x, "The Pro plan costs $44 per month.") == "current"
    assert score.score(x, "It costs $49 per month.") == "stale"
    assert score.score(x, "It used to be $49 and is now $44.") == "both"
    assert score.score(x, "It costs 44 USD.") == "current"
    assert score.score(x, "It costs $449.") == "other"
    assert score.score(x, "I don't know.") == "declined"
    e = q("changed", "€40", ["€45"], "eur")
    assert score.score(e, "€40 per month") == "current"
    assert score.score(e, "45 euros") == "stale"


def test_numbers_match_with_or_without_thousands_separator():
    x = q("changed", "1,800 requests per minute", ["1,200 requests per minute"], "rate")
    assert score.score(x, "The limit is 1800 requests per minute.") == "current"
    assert score.score(x, "1,200 requests/min") == "stale"
    assert score.score(x, "11,200") == "other"
    p = q("changed", "99.95%", ["99.9%"], "percent")
    assert score.score(p, "It guarantees 99.95% uptime.") == "current"
    assert score.score(p, "It guarantees 99.9% uptime.") == "stale"


def test_menu_paths_match_labels_in_order():
    x = q("changed", "Account → Billing and plans", ["Settings → Billing"], "path")
    assert score.score(x, "Go to Account > Billing and plans.") == "current"
    assert score.score(x, "Open Settings → Billing in Acme Console.") == "stale"
    assert score.score(x, "Billing is under Settings.") == "other"
    assert score.score(x, "Go to Account / Billing and plans.") == "current"
    m = q("changed", "Settings → Members", ["Team → Members"], "path")
    assert score.score(m, "To invite team members, go to Settings → Members.") == "current"
    assert score.score(m, "Open Team → Members.") == "stale"


def test_plan_and_status_count_the_first_mentioned():
    x = q("changed", "Business", ["Pro"], "name", fact="feature.tracing.plan")
    assert score.score(x, "Tracing is available on the Business plan and above (Business, Enterprise).") == "current"
    assert score.score(x, "The Pro plan, and also Business and Enterprise.") == "stale"
    s = q("changed", "generally available", ["in beta"], "status")
    assert score.score(s, "It is generally available, no longer in beta.") == "current"
    assert score.score(s, "The integration is in beta.") == "stale"


def test_deleted_and_new():
    d = q("deleted", "", ["https://hooks.acme.cloud/in/box-abc123"], "url", qkind="deleted")
    assert score.score(d, "It sends events to https://hooks.acme.cloud/in/box-abc123.") == "stale"
    assert score.score(d, "I don't know.") == "current"
    assert score.score(d, "The Box integration was retired.") == "current"
    n = q("new", "https://hooks.acme.cloud/in/vercel-xyz789", [], "url", qkind="new")
    assert score.score(n, "https://hooks.acme.cloud/in/vercel-xyz789") == "current"
    assert score.score(n, "The context doesn't say.") == "missing"


def test_render_matches_its_own_pattern():
    for f in [Fact("a", "usd", 49), Fact("a", "count", 250, "seats"), Fact("a", "gb", 1000), Fact("a", "days", 14),
              Fact("a", "rate", 1200), Fact("a", "path", "Data → Audit log"), Fact("a", "percent", "99.9"),
              Fact("a", "name", "Monday to Friday, 08:00 to 18:00 UTC"), Fact("a", "minutes", 15)]:
        assert score.pattern(f.kind, render(f)).search("x " + render(f) + " y"), f


def test_classify_index_entries():
    row = {"id": 1, "slug": "a", "title": "T", "body": "Body one."}
    live = {1: row}
    cur = chunk_texts(row)[0]
    entries = [{"article_id": 1, "text": cur}, {"article_id": 1, "text": cur}, {"article_id": 1, "text": "T\n\nOld."},
               {"article_id": 2, "text": "gone"}]
    assert score.classify(entries, live) == ["current", "duplicate", "outdated", "deleted"]
    a = score.audit(entries, live)
    assert a["missing"] == 0 and a["entries"] == 4
    assert score.in_sync([{"text": cur}], row) == (True, True)
    assert score.in_sync([{"text": cur}, {"text": "old"}], row) == (True, False)
    assert score.in_sync([], None) == (True, True)


def test_query_time_check_keeps_only_text_the_record_still_has():
    from sync.designs import Design
    row = {"id": 1, "slug": "a", "title": "T", "body": "Now."}
    cur = chunk_texts(row)[0]

    class Rec:
        def rows(self, where, params):
            return [row] if 1 in params[0] else []

    class D(Design):
        check = True

        def near(self, vec, k):
            return [{"article_id": 1, "text": "T\n\nBefore."}, {"article_id": 2, "text": "gone"},
                    {"article_id": 1, "text": cur}]

    keep, dropped = D(Rec(), None, None).retrieve(None)
    assert [k["text"] for k in keep] == [cur]
    assert [d["article_id"] for d in dropped] == [1, 2]
