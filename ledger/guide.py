"""What the models are told about the data: the bare schema, and the data team's guide."""
from ledger.world import SCHEMA

DDL = SCHEMA.split("CASCADE;", 1)[1].strip()

GUIDE = """\
Acme Cloud data guide (maintained by the data team)

- Money columns are integer cents in the row's currency (customers.currency, invoices.currency: 'USD' or 'EUR').
  Report money in US dollars. Finance converts EUR at a fixed rate: 1 EUR = 1.10 USD.
- customers.is_test = true marks Acme's own test accounts. Leave them out of every number.
- A current customer has no churned_at (or churned_at in the future). A paying customer is a current customer
  whose plan is not 'free'. A customer churned in a period if churned_at falls in that period.
- customers.plan is the customer's current plan: 'free', 'starter', 'pro' or 'business'.
- invoices.status is 'paid', 'open' (not paid yet) or 'void' (cancelled; never counts, and is usually re-issued
  as a new invoice). "Billed" means paid or open.
- An invoice has one 'plan' line and may have several 'seats' lines and a 'storage' line (invoice_lines.kind).
  invoices.amount_cents is the sum of its lines.
- Revenue for a period = paid invoices issued in the period minus refunds made in the period
  (by refunds.refunded_at), in USD, without test accounts.
- Days, months, quarters and years are counted in New York time (America/New_York).
  Timestamps are stored in UTC.
- tickets holds support tickets; subject and body are free text written by customers.

Example: paid invoices per month, in USD, New York time, without test accounts
SELECT date_trunc('month', i.issued_at AT TIME ZONE 'America/New_York') AS month,
       sum(CASE WHEN i.currency = 'EUR' THEN i.amount_cents * 1.10 ELSE i.amount_cents END) / 100.0 AS paid_usd
FROM invoices i JOIN customers c ON c.id = i.customer_id
WHERE i.status = 'paid' AND NOT c.is_test
GROUP BY 1 ORDER BY 1;
"""
