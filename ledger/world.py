"""Acme Cloud's billing data: customers, invoices, invoice lines, refunds and support tickets.

Everything is generated from one seed, so every run sees the same company. The same data is kept
in Python (for the ground truth, computed without SQL) and loaded into Postgres with three roles:

- ``acme``: the owner. What a tutorial connects with: it can read and write everything.
- ``analyst_ro``: read-only, statement timeout, for internal questions.
- ``portal``: read-only, and row-level security limits every table to ``app.customer_id``.

    uv run python -m ledger.world --load     # (re)create tables, roles and data
    uv run python -m ledger.world            # print a summary
"""
from __future__ import annotations

import argparse
import os
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

UTC = timezone.utc
NY = ZoneInfo("America/New_York")           # Acme's books: months and quarters in New York time
NOW = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)
START = datetime(2025, 1, 1, 0, 0, tzinfo=UTC)
EUR_USD = 1.10                              # finance's fixed reporting rate
SEED = 7

PRICES = {"USD": {"starter": 2900, "pro": 4900, "business": 19900},
          "EUR": {"starter": 2700, "pro": 4500, "business": 17900}}
SEAT = {"USD": 1000, "EUR": 900}
STORAGE = {"USD": 500, "EUR": 450}
EUR_COUNTRIES = {"DE", "FR", "NL", "IE", "ES"}

DB_URL = os.environ.get("LEDGER_DB_URL", "postgresql://acme:acme@localhost:5436/ledger")
ANALYST_URL = os.environ.get("LEDGER_ANALYST_URL", "postgresql://analyst_ro:analyst@localhost:5436/ledger")
PORTAL_URL = os.environ.get("LEDGER_PORTAL_URL", "postgresql://portal:portal@localhost:5436/ledger")


@dataclass
class Customer:
    id: int
    name: str
    email: str
    country: str
    plan: str
    currency: str
    created_at: datetime
    churned_at: datetime | None = None
    is_test: bool = False


@dataclass
class Line:
    id: int
    invoice_id: int
    kind: str              # plan | seats | storage
    description: str
    quantity: int
    amount_cents: int


@dataclass
class Invoice:
    id: int
    number: str
    customer_id: int
    issued_at: datetime
    status: str            # paid | open | void
    currency: str
    amount_cents: int
    lines: list[Line] = field(default_factory=list)


@dataclass
class Refund:
    id: int
    invoice_id: int
    refunded_at: datetime
    amount_cents: int
    reason: str


@dataclass
class Ticket:
    id: int
    customer_id: int
    created_at: datetime
    subject: str
    body: str
    topic: str             # ground truth only; not in the database


# Named customers the questions talk about: (name, country, plan, created_at)
NAMED = [
    ("Ada Lovelace", "UK", "pro", datetime(2025, 2, 11, 9, 30, tzinfo=UTC)),
    ("Grace Hopper", "US", "business", datetime(2025, 1, 20, 15, 5, tzinfo=UTC)),
    ("Alan Turing", "UK", "starter", datetime(2025, 6, 23, 10, 12, tzinfo=UTC)),
    ("Mallory Kent", "US", "pro", datetime(2025, 9, 4, 18, 40, tzinfo=UTC)),
    ("Eve Adams", "US", "pro", datetime(2025, 11, 14, 13, 0, tzinfo=UTC)),
]

OTHER_NAMES = [
    "Liam Carter", "Olivia Brooks", "Noah Bennett", "Emma Hughes", "Lucas Meyer", "Mia Schneider",
    "Felix Wagner", "Hannah Fischer", "Jonas Becker", "Lea Hoffmann", "Louis Martin", "Chloe Dubois",
    "Hugo Laurent", "Camille Bernard", "Sem de Vries", "Julia Jansen", "Daan Visser", "Saoirse Byrne",
    "Conor Walsh", "Lucia Garcia", "Pablo Romero", "Wing Chan", "Ka Ho Leung", "Mei Ling Wong",
    "Chun Yin Lau", "Hiu Tung Cheung", "Ethan Tremblay", "Sophie Roy", "Ryan Gagnon", "Zoe Clarke",
    "Jack Wilson", "Isla Thompson", "Cooper Smith", "Ruby Taylor", "James Miller", "Ava Davis",
    "Benjamin Moore", "Charlotte Lee", "Henry Walker", "Amelia Hall", "Samuel Young", "Harper King",
    "Daniel Wright", "Evelyn Scott", "Matthew Green", "Abigail Baker", "Owen Evans", "Ella Roberts",
    "Leo Turner", "Grace Phillips", "Oscar Campbell", "Freya Parker", "Theo Edwards", "Poppy Collins",
]
OTHER_COUNTRIES = (["US"] * 16 + ["UK"] * 6 + ["DE"] * 6 + ["FR"] * 4 + ["NL"] * 3 + ["HK"] * 5
                   + ["CA"] * 4 + ["AU"] * 3 + ["IE"] * 2 + ["ES"] * 2 + ["SG"] * 3)

TEST_ACCOUNTS = [
    ("Acme QA Team", "business", datetime(2025, 1, 6, 8, 0, tzinfo=UTC)),
    ("Billing Sandbox", "business", datetime(2025, 3, 3, 8, 0, tzinfo=UTC)),
    ("Load Test Org", "pro", datetime(2026, 6, 1, 8, 0, tzinfo=UTC)),
]

TOPICS = {
    "slow_dashboard": [
        ("Dashboard takes forever to load", "Since this morning the main dashboard needs almost a minute to open. Can you check?"),
        ("Charts are really sluggish", "All the usage charts crawl when I switch between projects. It used to be instant."),
        ("Reports page keeps timing out", "The reports page spins and then times out for most date ranges."),
        ("Analytics view is painfully slow", "Opening analytics takes 30+ seconds every time, my team is complaining."),
        ("Graphs won't load", "Usage graphs show a spinner for ages before anything appears. Is something wrong on your side?"),
    ],
    "data_export": [
        ("CSV export fails", "When I export my projects to CSV the download fails halfway."),
        ("Can't download my data", "I need a copy of all our records but the download button gives an error."),
        ("Export stuck at 0%", "The export to our S3 bucket has been stuck at 0% since yesterday."),
        ("Backup download link broken", "The link in the 'your backup is ready' email returns a 404."),
        ("Export job never finishes", "I started a full account export six hours ago and it is still running."),
        ("Need a copy of our data", "Our auditors want everything we store with you. How do we get it out? The export page errors."),
    ],
    "billing_question": [
        ("Question about my invoice", "Could you explain the extra seats line on my last invoice?"),
        ("VAT number missing", "Our VAT number isn't on the invoice, can you add it?"),
        ("Change billing email", "Please send invoices to finance@ instead of me."),
        ("Charged after downgrade", "I downgraded but was still charged the old price."),
    ],
    "login": [
        ("SSO login loop", "Signing in with SSO sends me back to the login page."),
        ("2FA code not arriving", "The two-factor code never arrives by SMS."),
        ("Locked out", "I reset my password but still can't get in."),
    ],
    "how_to": [
        ("Add a widget to my dashboard?", "How do I add the storage widget to my dashboard?"),
        ("Import from CSV", "Is there a way to import projects from a CSV file?"),
        ("Invite a teammate", "How do I invite a colleague to our workspace?"),
        ("Dashboard sharing", "Can I share a read-only dashboard with a client?"),
    ],
    "feature_request": [
        ("Dark mode please", "Would love a dark mode for the console."),
        ("Slack alerts", "Feature request: send usage alerts to Slack."),
    ],
}

REFUND_REASONS = ["charged twice", "downgraded mid-cycle", "seats added by mistake", "service outage credit",
                  "cancelled within 14 days", "goodwill credit"]


def _add_months(dt: datetime, k: int) -> datetime:
    month = dt.month - 1 + k
    year, month = dt.year + month // 12, month % 12 + 1
    return dt.replace(year=year, month=month, day=min(dt.day, 28))


def _between(rng: random.Random, a: datetime, b: datetime) -> datetime:
    seconds = int((b - a).total_seconds())
    return a + timedelta(seconds=rng.randrange(max(seconds, 1)))


@dataclass
class World:
    customers: list[Customer]
    invoices: list[Invoice]
    refunds: list[Refund]
    tickets: list[Ticket]

    def customer(self, name: str) -> Customer:
        return next(c for c in self.customers if c.name == name)

    def by_id(self, cid: int) -> Customer:
        return self._index[cid]

    def __post_init__(self) -> None:
        self._index = {c.id: c for c in self.customers}


def build(seed: int = SEED) -> World:
    rng = random.Random(seed)
    customers: list[Customer] = []
    for name, country, plan, created in NAMED:
        customers.append(Customer(len(customers) + 1, name, _email(name), country, plan,
                                  "EUR" if country in EUR_COUNTRIES else "USD", created))
    countries = OTHER_COUNTRIES[:]
    rng.shuffle(countries)
    for i, name in enumerate(OTHER_NAMES):
        country = countries[i % len(countries)]
        plan = rng.choices(["free", "starter", "pro", "business"], [15, 35, 35, 15])[0]
        if i % 7 == 0:   # some accounts were opened in the first hours of a month (UTC): the time-zone trap
            created = datetime(rng.choice([2025, 2026]) if i < 30 else 2025, rng.randint(1, 10), 1,
                               rng.randint(0, 3), rng.randint(0, 59), tzinfo=UTC)
        else:
            created = _between(rng, START, datetime(2026, 10, 20, tzinfo=UTC))
        customers.append(Customer(len(customers) + 1, name, _email(name), country, plan,
                                  "EUR" if country in EUR_COUNTRIES else "USD", created))
    for name, plan, created in TEST_ACCOUNTS:
        customers.append(Customer(len(customers) + 1, name, _email(name, "acme.example"), "US", plan, "USD",
                                  created, is_test=True))
    # churn: about a fifth of the unnamed customers left
    for c in customers[len(NAMED):]:
        if not c.is_test and rng.random() < 0.22:
            earliest = c.created_at + timedelta(days=60)
            if earliest < NOW - timedelta(days=5):
                c.churned_at = _between(rng, earliest, NOW - timedelta(days=2))

    invoices: list[Invoice] = []
    line_id = 0
    for c in customers:
        if c.plan == "free":
            continue
        seats = rng.choices([0, 1, 2, 3, 5], [40, 20, 20, 10, 10])[0]
        storage = c.plan in ("pro", "business") and rng.random() < 0.3
        k = 0
        while True:
            issued = _add_months(c.created_at, k)
            k += 1
            if issued > NOW or (c.churned_at and issued >= c.churned_at):
                break
            if rng.random() < 0.05:
                seats += 1
            spec = [("plan", f"{c.plan.capitalize()} plan (monthly)", 1, PRICES[c.currency][c.plan])]
            if seats:
                spec.append(("seats", "Extra seats", seats, seats * SEAT[c.currency]))
            if seats and rng.random() < 0.12:
                q = rng.choice([1, 2])
                spec.append(("seats", "Extra seats added mid-cycle (prorated)", q, q * SEAT[c.currency] // 2))
            if storage:
                spec.append(("storage", "Extra storage 100 GB", 1, STORAGE[c.currency]))
            amount = sum(s[3] for s in spec)
            if issued > NOW - timedelta(days=14):
                status = "open" if rng.random() < 0.6 else "paid"
            else:
                status = "open" if rng.random() < 0.02 else "paid"
            if status == "paid" and issued < NOW - timedelta(days=20) and rng.random() < 0.03:
                # issued with the seats counted twice, voided, and issued again two hours later
                wrong = spec + ([("seats", "Extra seats", seats, seats * SEAT[c.currency])] if seats
                                else [("seats", "Extra seats", 2, 2 * SEAT[c.currency])])
                inv = Invoice(0, "", c.id, issued, "void", c.currency, sum(s[3] for s in wrong))
                for kind, desc, q, amt in wrong:
                    line_id += 1
                    inv.lines.append(Line(line_id, 0, kind, desc, q, amt))
                invoices.append(inv)
                issued = issued + timedelta(hours=2)
            inv = Invoice(0, "", c.id, issued, status, c.currency, amount)
            for kind, desc, q, amt in spec:
                line_id += 1
                inv.lines.append(Line(line_id, 0, kind, desc, q, amt))
            invoices.append(inv)
    invoices.sort(key=lambda i: (i.issued_at, i.customer_id))
    for n, inv in enumerate(invoices, 1):
        inv.id, inv.number = n, f"INV-{n:05d}"
        for line in inv.lines:
            line.invoice_id = n

    refunds: list[Refund] = []
    paid = [i for i in invoices if i.status == "paid"]
    for inv in rng.sample(paid, 55):
        when = inv.issued_at + timedelta(days=rng.randint(1, 45), hours=rng.randint(0, 23))
        if when >= NOW:
            continue
        reason = rng.choice(REFUND_REASONS)
        amount = inv.amount_cents if reason in ("charged twice", "cancelled within 14 days") else (
            inv.amount_cents // 2 if reason == "downgraded mid-cycle" else
            min(inv.amount_cents, rng.choice([500, 1000, 1500, 2000])))
        refunds.append(Refund(0, inv.id, when, amount, reason))
    refunds.sort(key=lambda r: r.refunded_at)
    for n, r in enumerate(refunds, 1):
        r.id = n

    tickets = _tickets(rng, customers)
    return World(customers, invoices, refunds, tickets)


def _tickets(rng: random.Random, customers: list[Customer]) -> list[Ticket]:
    real = [c for c in customers if not c.is_test]
    out: list[tuple[int, datetime, str, str, str]] = []
    oct_start, nov_start = datetime(2026, 10, 1, 4, tzinfo=UTC), datetime(2026, 11, 1, 4, tzinfo=UTC)

    def alive_at(c: Customer, t: datetime) -> bool:
        return c.created_at < t and (c.churned_at is None or c.churned_at > t)

    # Planted: five different customers complain about a slow dashboard in October 2026
    planted = ["Ada Lovelace", "Lucas Meyer", "Wing Chan", "Zoe Clarke", "Owen Evans"]
    for name, (subject, body) in zip(planted, TOPICS["slow_dashboard"]):
        c = next(x for x in real if x.name == name)
        out.append((c.id, _between(rng, oct_start + timedelta(days=1), nov_start - timedelta(days=2)), subject, body,
                    "slow_dashboard"))
    weights = {"data_export": 30, "billing_question": 40, "login": 25, "how_to": 30, "feature_request": 12,
               "slow_dashboard": 10}
    for topic, n in weights.items():
        for _ in range(n):
            while True:
                c = rng.choice(real)
                t = _between(rng, START, NOW - timedelta(hours=6))
                if not alive_at(c, t):
                    continue
                if topic == "slow_dashboard" and oct_start - timedelta(days=1) <= t < nov_start + timedelta(days=1):
                    continue   # October's slow-dashboard complaints are exactly the five planted ones
                break
            subject, body = rng.choice(TOPICS[topic])
            out.append((c.id, t, subject, body, topic))
    out.sort(key=lambda x: x[1])
    return [Ticket(n, cid, t, s, b, topic) for n, (cid, t, s, b, topic) in enumerate(out, 1)]


def _email(name: str, domain: str = "example.com") -> str:
    return name.lower().replace(" ", ".") + "@" + domain


SCHEMA = """
DROP TABLE IF EXISTS tickets, refunds, invoice_lines, invoices, customers CASCADE;
CREATE TABLE customers (
    id          integer PRIMARY KEY,
    name        text NOT NULL,
    email       text NOT NULL UNIQUE,
    country     text NOT NULL,
    plan        text NOT NULL,
    currency    text NOT NULL,
    created_at  timestamptz NOT NULL,
    churned_at  timestamptz,
    is_test     boolean NOT NULL DEFAULT false
);
CREATE TABLE invoices (
    id            integer PRIMARY KEY,
    number        text NOT NULL UNIQUE,
    customer_id   integer NOT NULL REFERENCES customers(id),
    issued_at     timestamptz NOT NULL,
    status        text NOT NULL CHECK (status IN ('paid', 'open', 'void')),
    currency      text NOT NULL,
    amount_cents  integer NOT NULL
);
CREATE TABLE invoice_lines (
    id            integer PRIMARY KEY,
    invoice_id    integer NOT NULL REFERENCES invoices(id),
    kind          text NOT NULL,
    description   text NOT NULL,
    quantity      integer NOT NULL,
    amount_cents  integer NOT NULL
);
CREATE TABLE refunds (
    id            integer PRIMARY KEY,
    invoice_id    integer NOT NULL REFERENCES invoices(id),
    refunded_at   timestamptz NOT NULL,
    amount_cents  integer NOT NULL,
    reason        text NOT NULL
);
CREATE TABLE tickets (
    id           integer PRIMARY KEY,
    customer_id  integer NOT NULL REFERENCES customers(id),
    created_at   timestamptz NOT NULL,
    subject      text NOT NULL,
    body         text NOT NULL
);
"""

ROLES = """
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'analyst_ro') THEN CREATE ROLE analyst_ro LOGIN PASSWORD 'analyst'; END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'portal') THEN CREATE ROLE portal LOGIN PASSWORD 'portal'; END IF;
END $$;
ALTER ROLE analyst_ro SET default_transaction_read_only = on;
ALTER ROLE analyst_ro SET statement_timeout = '5s';
ALTER ROLE portal SET default_transaction_read_only = on;
ALTER ROLE portal SET statement_timeout = '5s';
GRANT SELECT ON customers, invoices, invoice_lines, refunds, tickets TO analyst_ro, portal;

ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoice_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE refunds ENABLE ROW LEVEL SECURITY;
ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;
CREATE POLICY analyst_all ON customers FOR SELECT TO analyst_ro USING (true);
CREATE POLICY analyst_all ON invoices FOR SELECT TO analyst_ro USING (true);
CREATE POLICY analyst_all ON invoice_lines FOR SELECT TO analyst_ro USING (true);
CREATE POLICY analyst_all ON refunds FOR SELECT TO analyst_ro USING (true);
CREATE POLICY analyst_all ON tickets FOR SELECT TO analyst_ro USING (true);
CREATE POLICY own_rows ON customers FOR SELECT TO portal
    USING (id = nullif(current_setting('app.customer_id', true), '')::int);
CREATE POLICY own_rows ON invoices FOR SELECT TO portal
    USING (customer_id = nullif(current_setting('app.customer_id', true), '')::int);
CREATE POLICY own_rows ON invoice_lines FOR SELECT TO portal
    USING (invoice_id IN (SELECT id FROM invoices));
CREATE POLICY own_rows ON refunds FOR SELECT TO portal
    USING (invoice_id IN (SELECT id FROM invoices));
CREATE POLICY own_rows ON tickets FOR SELECT TO portal
    USING (customer_id = nullif(current_setting('app.customer_id', true), '')::int);
"""


def load(world: World, url: str = DB_URL) -> None:
    import psycopg
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(SCHEMA)
        with conn.cursor() as cur:
            cur.executemany("INSERT INTO customers VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                            [(c.id, c.name, c.email, c.country, c.plan, c.currency, c.created_at, c.churned_at,
                              c.is_test) for c in world.customers])
            cur.executemany("INSERT INTO invoices VALUES (%s,%s,%s,%s,%s,%s,%s)",
                            [(i.id, i.number, i.customer_id, i.issued_at, i.status, i.currency, i.amount_cents)
                             for i in world.invoices])
            cur.executemany("INSERT INTO invoice_lines VALUES (%s,%s,%s,%s,%s,%s)",
                            [(l.id, l.invoice_id, l.kind, l.description, l.quantity, l.amount_cents)
                             for i in world.invoices for l in i.lines])
            cur.executemany("INSERT INTO refunds VALUES (%s,%s,%s,%s,%s)",
                            [(r.id, r.invoice_id, r.refunded_at, r.amount_cents, r.reason) for r in world.refunds])
            cur.executemany("INSERT INTO tickets VALUES (%s,%s,%s,%s,%s)",
                            [(t.id, t.customer_id, t.created_at, t.subject, t.body) for t in world.tickets])
        conn.execute(ROLES)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--load", action="store_true")
    args = ap.parse_args()
    w = build()
    lines = sum(len(i.lines) for i in w.invoices)
    print(f"customers {len(w.customers)} (test {sum(c.is_test for c in w.customers)}, "
          f"churned {sum(c.churned_at is not None for c in w.customers)}), invoices {len(w.invoices)} "
          f"(void {sum(i.status == 'void' for i in w.invoices)}, open {sum(i.status == 'open' for i in w.invoices)}), "
          f"lines {lines}, refunds {len(w.refunds)}, tickets {len(w.tickets)}")
    if args.load:
        load(w)
        print("loaded into", DB_URL.rsplit("@", 1)[-1])


if __name__ == "__main__":
    main()
