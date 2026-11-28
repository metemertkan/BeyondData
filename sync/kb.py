"""Episode 6: Acme Cloud's help center, one month of changes to it, and questions asked during that month.

    uv run python -m sync.kb --prepare          # -> data/ep06/{pilot,full}/{articles,events,questions}.json
    uv run python -m sync.kb                    # print a summary

Acme Cloud is Episode 1's company. Its help center is generated from one seed (7) as articles whose text states
facts (prices, limits, menu paths, URLs, statuses) through placeholders, so the generator knows which articles
state which fact. The record is what the generator writes; nothing here is read back by the designs.

A month of changes is then simulated in memory (pilot: 7 days, seed 8; full run: 30 days, seed 7), and each
change is stored as the rows the application saves (or deletes), or as the one SQL statement of the migration.
Questions are asked at chosen moments, with the right value at that moment and the values that came before it.
"""
from __future__ import annotations

import argparse
import json
import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data" / "ep06"
UTC = timezone.utc
BASE_SEED = 7
RUNS = {
    "pilot": {"seed": 8, "start": datetime(2026, 9, 7, tzinfo=UTC), "days": 7, "migration_day": 3,
              "counts": {"fact": 10, "edit": 90, "new_feature": 2, "new_integration": 2, "release_notes": 5,
                         "incident": 3, "retire_integration": 2, "retire_feature": 1, "prune": 3, "rename": 4,
                         "rewrite": 5},
              "questions": {"changed": 60, "unchanged": 20, "deleted": 10, "new": 10}},
    "full": {"seed": 7, "start": datetime(2026, 10, 19, tzinfo=UTC), "days": 30, "migration_day": 17,
             "counts": {"fact": 44, "edit": 400, "new_feature": 8, "new_integration": 6, "release_notes": 22,
                        "incident": 10, "retire_integration": 6, "retire_feature": 4, "prune": 14, "rename": 15,
                        "rewrite": 20},
             "questions": {"changed": 300, "unchanged": 100, "deleted": 50, "new": 50}},
}
DELAYS = [("2 min", 120), ("15 min", 900), ("1 h", 3600), ("4 h", 4 * 3600), ("12 h", 12 * 3600),
          ("1 day", 86400), ("3 days", 3 * 86400), ("7 days", 7 * 86400)]
CONSOLE_OLD, CONSOLE_NEW = "Acme Console", "Acme Studio"
URL = "https://help.acme.cloud/"


# ------------------------------------------------------------------------------------------------ facts
@dataclass
class Fact:
    key: str
    kind: str                 # usd eur count gb rate days percent path url status name hours minutes
    value: object
    unit: str = ""            # for count: what is counted
    question: str = ""
    changeable: bool = True


def render(f: Fact) -> str:
    v = f.value
    if f.kind == "usd":
        return f"${v}"
    if f.kind == "eur":
        return f"€{v}"
    if f.kind == "count":
        return f"{v:,} {f.unit}"
    if f.kind == "gb":
        return f"{v:,} GB"
    if f.kind == "rate":
        return f"{v:,} requests per minute"
    if f.kind == "days":
        return f"{v} days"
    if f.kind == "minutes":
        return f"{v} minutes"
    if f.kind == "hours":
        return f"{v} hours"
    if f.kind == "percent":
        return f"{v}%"
    if f.kind == "status":
        return {"ga": "generally available", "beta": "in beta", "preview": "in preview"}[v]
    return str(v)


PLANS = ["Starter", "Pro", "Business", "Enterprise"]
SECTIONS = ["Settings", "Projects", "Dashboards", "Data", "Security", "Team", "Developer", "Monitoring"]

FEATURES = [  # name, what a limit counts
    ("Usage alerts", "alert rules"), ("Scheduled exports", "scheduled exports"), ("Audit log", "audit log streams"),
    ("Custom domains", "custom domains"), ("Team roles", "custom roles"), ("Read-only dashboards", "shared dashboards"),
    ("Webhooks", "webhook endpoints"), ("IP allowlist", "allowlist entries"), ("SAML single sign-on", "identity providers"),
    ("SCIM provisioning", "provisioned groups"), ("API keys", "active API keys"), ("Service accounts", "service accounts"),
    ("Projects", "projects"), ("Environments", "environments per project"), ("Saved views", "saved views"),
    ("Annotations", "annotations per dashboard"), ("Anomaly detection", "monitored metrics"),
    ("Cost reports", "cost reports"), ("Budget caps", "budget caps"), ("Usage quotas", "quota rules"),
    ("Data retention rules", "retention rules"), ("Backups", "manual backups per day"), ("Snapshots", "snapshots"),
    ("Restore points", "restore points"), ("Object storage buckets", "buckets"), ("Lifecycle policies", "lifecycle policies"),
    ("Log drains", "log drains"), ("Metrics explorer", "saved queries"), ("Tracing", "traced services"),
    ("Status pages", "status pages"), ("Incident timelines", "timeline templates"), ("On-call schedules", "on-call schedules"),
    ("Escalation policies", "escalation policies"), ("Maintenance windows", "maintenance windows"),
    ("Deploy previews", "concurrent previews"), ("Build cache", "cached builds"), ("Secrets manager", "secrets per project"),
    ("Config variables", "variables per environment"), ("Feature flags", "feature flags"), ("Experiments", "running experiments"),
    ("Workflows", "workflows"), ("Scheduled jobs", "scheduled jobs"), ("Queues", "queues"), ("Event streams", "event streams"),
    ("Data import", "imports per day"), ("CSV import", "rows per import"), ("Bulk edit", "rows per bulk edit"),
    ("Comments", "comment threads"), ("Mentions", "mentions per comment"), ("Notifications", "notification rules"),
    ("Email digests", "digests"), ("Mobile app", "registered devices"), ("Two-factor authentication", "backup codes"),
    ("Session management", "active sessions"), ("Access reviews", "access reviews per quarter"),
    ("Data masking", "masking rules"), ("Field-level encryption", "encrypted fields"), ("Customer-managed keys", "managed keys"),
    ("Private networking", "private endpoints"), ("VPC peering", "peering connections"), ("Load balancers", "load balancers"),
    ("Edge cache", "cache rules"), ("Rate limiting rules", "rate limiting rules"), ("Bot protection", "protected routes"),
    ("Uptime checks", "uptime checks"), ("Synthetic tests", "synthetic tests"), ("Error tracking", "tracked projects"),
    ("Release tracking", "tracked releases"), ("Dashboards", "dashboards"), ("Widgets", "widgets per dashboard"),
    ("Reports", "scheduled reports"), ("Embedded analytics", "embedded views"), ("Data catalog", "catalog entries"),
    ("Query editor", "saved queries per user"), ("Sandboxes", "sandboxes"), ("Templates", "templates"),
    ("Tags", "tags per resource"), ("Labels", "labels"), ("Search", "saved searches"), ("Favorites", "favorites"),
]
NEW_FEATURES = [("Session replay", "recorded sessions"), ("Usage forecasts", "forecasts"), ("Approval flows", "approval flows"),
                ("Data lineage", "lineage graphs"), ("Smart alerts", "smart alert rules"), ("Change log export", "export jobs"),
                ("Cost anomaly alerts", "anomaly rules"), ("Team spaces", "team spaces"), ("Runbooks", "runbooks"),
                ("Access requests", "open requests")]
INTEGRATIONS = [
    "Slack", "Microsoft Teams", "GitHub", "GitLab", "Bitbucket", "Jira", "Linear", "Asana", "Trello", "Notion",
    "Confluence", "PagerDuty", "Opsgenie", "Datadog", "Grafana", "Sentry", "New Relic", "Splunk", "Zapier", "Salesforce",
    "HubSpot", "Zendesk", "Intercom", "Freshdesk", "ServiceNow", "Amazon S3", "Google Cloud Storage", "Azure Blob Storage",
    "BigQuery", "Snowflake", "Redshift", "Okta", "Auth0", "Google Workspace", "Microsoft Entra ID", "Discord", "Webex",
    "Zoom", "Dropbox", "Box", "OneDrive", "SharePoint", "Airtable", "Monday.com", "ClickUp", "Stripe", "Twilio",
    "SendGrid", "Mailchimp", "Segment", "Mixpanel", "Amplitude", "Terraform", "Pulumi", "Kubernetes", "Docker Hub",
    "CircleCI", "Jenkins", "Tableau", "Looker",
]
NEW_INTEGRATIONS = ["Power BI", "Rippling", "Workday", "Mattermost", "Rootly", "incident.io", "Buildkite", "Vercel"]
RESOURCES = ["projects", "environments", "deployments", "builds", "invoices", "usage", "members", "roles", "api-keys",
             "webhooks", "alerts", "dashboards", "reports", "exports", "imports", "backups", "snapshots", "buckets",
             "objects", "logs", "metrics", "traces", "incidents", "status-pages", "schedules", "workflows", "jobs",
             "queues", "secrets", "audit-events"]
REGIONS = [("us-east-1", "Virginia, USA"), ("us-west-2", "Oregon, USA"), ("ca-central-1", "Montréal, Canada"),
           ("eu-west-1", "Dublin, Ireland"), ("eu-central-1", "Frankfurt, Germany"), ("uk-south-1", "London, UK"),
           ("ap-southeast-1", "Singapore"), ("ap-northeast-1", "Tokyo, Japan"), ("ap-southeast-2", "Sydney, Australia"),
           ("sa-east-1", "São Paulo, Brazil")]


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def token(rng: random.Random) -> str:
    return "".join(rng.choice("abcdefghjkmnpqrstuvwxyz23456789") for _ in range(6))


def build_facts(rng: random.Random) -> dict[str, Fact]:
    F: dict[str, Fact] = {}

    def add(key, kind, value, question, unit="", changeable=True):
        F[key] = Fact(key, kind, value, unit, question, changeable)

    add("product.console", "name", CONSOLE_OLD, "What is the name of Acme Cloud's web console?", changeable=False)
    prices = {"Starter": (29, 27), "Pro": (49, 45), "Business": (199, 179)}       # Episode 1's prices
    seats = {"Starter": 3, "Pro": 10, "Business": 50}
    storage = {"Starter": 50, "Pro": 250, "Business": 1000}
    rate = {"Starter": 600, "Pro": 1200, "Business": 6000}
    logs = {"Starter": 7, "Pro": 30, "Business": 90}
    for p in ["Starter", "Pro", "Business"]:
        k = p.lower()
        add(f"plan.{k}.usd", "usd", prices[p][0], f"How much does the {p} plan cost per month in US dollars?")
        add(f"plan.{k}.eur", "eur", prices[p][1], f"How much does the {p} plan cost per month in euros?")
        add(f"plan.{k}.seats", "count", seats[p], f"How many seats are included in the {p} plan?", unit="seats")
        add(f"plan.{k}.storage", "gb", storage[p], f"How much storage is included in the {p} plan?")
        add(f"plan.{k}.rate", "rate", rate[p], f"What is the API rate limit on the {p} plan?")
        add(f"plan.{k}.logs", "days", logs[p], f"How long are logs kept on the {p} plan?")
    add("billing.seat_usd", "usd", 10, "How much does an extra seat cost per month in US dollars?")
    add("billing.storage_usd", "usd", 5, "How much does an extra 100 GB of storage cost per month in US dollars?")
    add("policy.trial", "days", 14, "How long is the free trial?")
    add("policy.refund", "days", 14, "How many days do I have to request a refund?")
    add("policy.sla", "percent", "99.9", "What uptime does the Business plan's SLA guarantee?")
    add("policy.sla_credit", "percent", "10", "How much service credit do I get if the monthly uptime SLA is missed?")
    add("policy.backup_every", "hours", 6, "How often are automatic backups taken?")
    add("policy.backup_keep", "days", 30, "How long are automatic backups kept?")
    add("policy.delete_after", "days", 30, "How long after cancellation is my data deleted?")
    add("policy.support_hours", "name", "Monday to Friday, 08:00 to 18:00 UTC", "What are the support hours?")
    add("policy.upload_mb", "count", 500, "What is the maximum file upload size?", unit="MB")
    add("policy.session", "hours", 12, "How long does a console session last before I have to sign in again?")
    add("policy.password", "count", 12, "What is the minimum password length?", unit="characters")
    add("policy.maintenance", "name", "Sundays, 02:00 to 04:00 UTC", "When is the weekly maintenance window?")
    add("menu.billing", "path", "Settings → Billing", "Where in the console do I find billing and invoices?")
    add("menu.integrations", "path", "Settings → Integrations", "Where in the console do I connect integrations?")
    add("menu.api_keys", "path", "Developer → API keys", "Where in the console do I create API keys?")
    add("menu.members", "path", "Team → Members", "Where in the console do I invite team members?")
    for name, unit in FEATURES + NEW_FEATURES:
        k = slugify(name)
        add(f"feature.{k}.plan", "name", rng.choice(["Starter", "Pro", "Pro", "Business"]),
            f"Which is the lowest plan that includes {name}?")
        add(f"feature.{k}.limit", "count", rng.choice([5, 10, 20, 25, 50, 100, 200, 250, 500]),
            f"How many {unit} can a Pro workspace have with {name}?", unit=unit)
        add(f"feature.{k}.menu", "path", f"{rng.choice(SECTIONS)} → {name}", f"Where in the console do I find {name}?")
    for name in INTEGRATIONS + NEW_INTEGRATIONS:
        k = slugify(name)
        add(f"integration.{k}.webhook", "url", f"https://hooks.acme.cloud/in/{k}-{token(rng)}",
            f"What webhook URL does the {name} integration send events to?")
        add(f"integration.{k}.sync", "minutes", rng.choice([5, 10, 15, 30, 60]),
            f"How often does the {name} integration sync?")
        add(f"integration.{k}.status", "status", rng.choice(["ga", "ga", "ga", "beta"]),
            f"Is the {name} integration generally available or in beta?")
    for r in RESOURCES:
        add(f"api.{r}.page", "count", rng.choice([50, 100, 200, 500]),
            f"What is the maximum page size when listing {r.replace('-', ' ')} with the API?", unit="items per page")
    for r in RESOURCES[:20]:
        add(f"cli.{r}.limit", "count", rng.choice([20, 25, 50, 100]),
            f"What is the default --limit for `acme {r} list`?", unit="results")
    for code, city in REGIONS:
        add(f"region.{code}.status", "status", rng.choice(["ga"] * 7 + ["preview"] * 3),
            f"Is the {code} region ({city}) generally available or in preview?")
    return F


# ------------------------------------------------------------------------------------------------ articles
FILLER = {  # wording that states no fact; a wording edit swaps one paragraph for another variant
    "intro": [
        "This article explains how it works, what you need before you start, and where to look if something goes wrong.",
        "Here is what you need to know before you start, how to set it up, and what to check if it doesn't behave as expected.",
        "Read on for an overview, the steps to get started, and answers to the questions we hear most often.",
        "This guide walks through the basics first and then covers the settings most teams change.",
        "Below you'll find a short overview, step-by-step instructions, and tips from our support team.",
    ],
    "before": [
        "Before you begin, make sure you are signed in with an account that has the Admin or Owner role in the workspace.",
        "You need the Admin or Owner role to change these settings. Members can see them but can't edit them.",
        "Only workspace Admins and Owners can make these changes; ask one of them if the buttons are greyed out for you.",
        "To follow these steps you need permission to manage the workspace, which Admins and Owners have by default.",
    ],
    "tip": [
        "Tip: changes take effect immediately for everyone in the workspace, so let your team know before you switch.",
        "Tip: you can undo most of these changes from the same page within 30 seconds of saving.",
        "Tip: if you manage several workspaces, check which one is selected in the top-left corner before you save.",
        "Tip: every change you make here is recorded, so your team can see who changed what and when.",
        "Tip: you can bookmark this page; the URL keeps the workspace you were in.",
    ],
    "help": [
        "Still stuck? Contact support from the help menu in the bottom-left corner and include your workspace name.",
        "If this doesn't solve the problem, open a ticket from the help menu and tell us what you tried.",
        "Need a hand? Our support team can look at your workspace with you; start a conversation from the help menu.",
        "Didn't find what you were looking for? Search the help center or ask our support team from the help menu.",
    ],
    "why": [
        "Teams use it to keep an eye on what matters without checking the console every hour.",
        "It saves time on repetitive work and gives everyone the same view of what is going on.",
        "Most teams turn it on in their first week, once they have more than a handful of projects.",
        "It is one of the first things we recommend setting up when a team grows beyond a few people.",
    ],
    "troubleshoot": [
        "If nothing happens after you save, refresh the page and check that your browser isn't blocking third-party cookies.",
        "If you see a permissions error, check your role under the team settings and ask an Owner to upgrade it.",
        "If the page loads slowly, try again in a private window; extensions sometimes interfere with the console.",
        "If the setting reverts after you save, another Admin may have changed it at the same time; check the audit trail.",
    ],
    "overview": [
        "Under the hood it runs in the same region as the rest of your workspace, so nothing leaves the region you picked when you created it. It works the same way in the console, the API and the command-line tool, and everything you set up in one place shows up in the others straight away.",
        "It is built into every workspace, so there is nothing to install. Settings are stored per workspace, which means each team can tune it without affecting the others, and an Owner can copy a configuration from one workspace to another from the same page.",
        "It works with the rest of Acme Cloud out of the box: projects, dashboards and alerts all understand it, and you can filter by it almost anywhere in the console. If you use the API, the same objects are available with the same names.",
        "Most of the work happens in the background. Once it is configured you rarely need to come back to it, but the page keeps a short history of recent activity so you can see what it did and when.",
        "It is designed for teams of every size. Small teams usually keep the defaults; larger organisations tend to split it by project or environment and give each team its own settings.",
    ],
    "permissions": [
        "Permissions follow your workspace roles. Owners and Admins can create, edit and delete; Members can use what has been set up; Viewers can only see it. Custom roles can be given any of these rights separately.",
        "Who can change what depends on the role: Admins manage the configuration, Members use it day to day, and Viewers have read-only access. If you use custom roles, look for the matching permission in the role editor.",
        "Access is controlled per workspace. Giving someone the Admin role lets them change every setting described here, so for larger teams we recommend a custom role that grants only the rights they need.",
        "Billing contacts without another role can't see or change these settings. Invite them as Members if they need to follow along, or share a read-only link instead.",
    ],
    "steps": [
        "Give it a name your team will recognise, pick the projects it applies to, and choose who should be notified. You can leave the advanced options at their defaults and change them later; nothing you pick here is permanent.",
        "Start with one project to see how it behaves, then extend it to the rest once you are happy. Each change is saved as you go, and the summary at the top of the page shows what is active.",
        "Fill in the short form, check the preview on the right, and save. The new item appears in the list straight away, with a status that tells you whether it is active, paused or waiting for something.",
        "Work through the three steps on the page: what it should apply to, what should happen, and who should hear about it. A green check next to each step shows when it is complete.",
    ],
    "best": [
        "Best practice: keep names short and consistent, for example team-environment-purpose, so that lists stay readable as they grow. Review what you have once a quarter and remove anything nobody uses.",
        "We recommend writing a one-line description for each item, saying who owns it and why it exists. When someone leaves the team, their items are then easy to hand over instead of being left behind.",
        "Teams that get the most out of it set it up the same way in every environment, test changes in a staging workspace first, and use tags to group related items so they can be found and changed together.",
        "A good habit is to start strict and relax later: it is easier to loosen a rule that is too tight than to find out about one that was too loose. Use the history panel to see what changed when something looks wrong.",
    ],
    "notify": [
        "Notifications go to the people you choose by email and in the console. You can also route them to a chat tool or an on-call service through an integration, and mute them for a while during planned work.",
        "When something needs attention you get one notification, not a stream of them: repeats are grouped, and a summary follows once the issue is resolved. Each person can change how they are notified in their profile.",
        "Every notification links straight to the item it is about. If you'd rather not receive a particular kind, open your profile, choose Notifications and switch it off; your teammates keep theirs.",
    ],
    "audit": [
        "Every change is written to the workspace's audit trail with who made it, when, and what it was before. Owners can export the trail as CSV for reviews.",
        "Changes are recorded in the audit trail, so you can always see who created, edited or deleted an item. Records are kept for as long as your plan keeps logs.",
        "Each create, edit and delete is logged with the person and the time. If a change surprises you, the audit trail is the first place to look.",
    ],
    "api": [
        "Everything on this page is also available through the REST API and the command-line tool, with the same names and the same permissions. API calls count towards your plan's rate limit.",
        "You can automate this with the API: list, create, update and delete are all supported, and every response includes the item's current state. Use an API key with the right scope.",
        "If you manage your setup as code, the Terraform provider and the command-line tool cover the same settings, so you can review changes before they go live.",
    ],
    "data": [
        "Data processed by this feature is stored encrypted in your workspace's region and is included in backups. Deleting an item removes it from the console at once and from backups when they expire.",
        "We only keep what is needed to provide the feature. Personal data is handled as described in our data processing agreement, and you can export or delete it at any time.",
        "Nothing is shared with third parties unless you connect an integration that does so. When you disconnect an integration, the data it sent is no longer updated but stays where it was sent.",
    ],
    "related": [
        "Related articles: getting started with your workspace, managing roles and permissions, and setting up notifications.",
        "See also: the audit trail, workspace settings, and how plans and limits work.",
        "Related: inviting your team, creating API keys, and connecting your first integration.",
    ],
    "faq_billing": [
        "Invoices are issued on the same day each month, the day your subscription started.",
        "Plan changes are prorated: you pay the difference for the rest of the billing period.",
        "You can download every invoice as a PDF from the billing page, together with a CSV of the line items.",
        "Taxes are added according to your billing address; enter your VAT number to have it shown on invoices.",
    ],
}


def P(*parts: str) -> str:
    return " ".join(parts)


@dataclass
class Article:
    id: int
    slug: str
    title: str
    category: str
    paras: list = field(default_factory=list)   # items: ["t", template] or ["f", filler kind, variant]
    created_at: str = ""
    optional: list = field(default_factory=list)  # indexes of paragraphs a rewrite may drop

    def facts(self) -> set[str]:
        out = set()
        for p in self.paras:
            if p[0] == "t":
                out |= set(re.findall(r"\{f:([^}]+)\}", p[1]))
        return out


def fill(template: str, F: dict[str, Fact], lists: dict) -> str:
    s = re.sub(r"\{f:([^}]+)\}", lambda m: render(F[m.group(1)]), template)
    s = re.sub(r"\{list:([^}]+)\}", lambda m: lists[m.group(1)](), s)
    return s


def text_of(a: Article, F: dict[str, Fact], lists: dict) -> str:
    out = []
    for p in a.paras:
        out.append(fill(p[1], F, lists) if p[0] == "t" else FILLER[p[1]][p[2]])
    return "\n\n".join(out)


class World:
    def __init__(self, seed: int = BASE_SEED):
        self.rng = random.Random(seed)
        self.F = build_facts(self.rng)
        self.articles: dict[int, Article] = {}
        self.active_features = [n for n, _ in FEATURES]
        self.active_integrations = list(INTEGRATIONS)
        self.lists = {"integrations": lambda: ", ".join(sorted(self.active_integrations)),
                      "features": lambda: ", ".join(sorted(self.active_features))}
        self.next_id = 1
        self._build()

    # --- helpers
    def f(self, kind: str, *opts) -> list:
        return ["f", kind, self.rng.randrange(len(FILLER[kind]))]

    def fs(self, *kinds: str) -> list:
        return [self.f(k) for k in kinds]

    def unique(self, slug: str, own: int | None = None) -> str:
        taken = {a.slug for a in self.articles.values() if a.id != own}
        out, n = slug, 2
        while out in taken:
            out, n = f"{slug}-{n}", n + 1
        return out

    def add(self, slug, title, category, paras, created, optional=()) -> Article:
        optional = [i for i, p in enumerate(paras) if p[0] == "f" and p[1] != "help"]
        a = Article(self.next_id, self.unique(slug), title, category, paras, created.isoformat(), optional)
        self.articles[a.id] = a
        self.next_id += 1
        return a

    def console(self) -> str:
        return "{f:product.console}"

    def _created(self) -> datetime:
        return datetime(2025, 1, 1, tzinfo=UTC) + timedelta(seconds=self.rng.randrange(int(6.5e7)))

    # --- the help center as it is at the start
    def _build(self):
        c = self.console()
        r = self.rng
        for p in PLANS[:3]:
            k = p.lower()
            self.add(f"plans/{k}", f"The {p} plan", "plans", [
                ["t", f"The {p} plan costs {{f:plan.{k}.usd}} per month (or {{f:plan.{k}.eur}} in the eurozone), billed monthly."],
                self.f("why"),
                ["t", P(f"It includes {{f:plan.{k}.seats}} and {{f:plan.{k}.storage}} of storage.",
                        "Extra seats cost {f:billing.seat_usd} per month each, and each extra 100 GB of storage costs {f:billing.storage_usd} per month.")],
                ["t", P(f"API requests on the {p} plan are limited to {{f:plan.{k}.rate}} per workspace.",
                        f"Logs are kept for {{f:plan.{k}.logs}}.")],
                ["t", f"To change plans, open {c} and go to {{f:menu.billing}}. Changes are prorated."],
                self.f("faq_billing"), self.f("help")], self._created())
        self.add("plans/enterprise", "The Enterprise plan", "plans", [
            ["t", P("The Enterprise plan has custom pricing, unlimited seats and storage sized to your needs.",
                    "It adds a dedicated support manager, single sign-on for every member and an SLA of {f:policy.sla} monthly uptime.")],
            self.f("why"), ["t", f"Talk to sales from {c} under {{f:menu.billing}} to get a quote."], self.f("help")],
            self._created())
        self.add("pricing", "Pricing", "plans", [
            ["t", "Acme Cloud has four plans. Prices are per workspace per month."],
            ["t", "Starter: {f:plan.starter.usd} ({f:plan.starter.eur}), {f:plan.starter.seats}, {f:plan.starter.storage} of storage."],
            ["t", "Pro: {f:plan.pro.usd} ({f:plan.pro.eur}), {f:plan.pro.seats}, {f:plan.pro.storage} of storage."],
            ["t", "Business: {f:plan.business.usd} ({f:plan.business.eur}), {f:plan.business.seats}, {f:plan.business.storage} of storage."],
            ["t", "Enterprise: custom pricing. Every plan starts with a free trial of {f:policy.trial}."],
            ["t", "Extra seats are {f:billing.seat_usd} per month and extra storage {f:billing.storage_usd} per 100 GB per month."],
            self.f("faq_billing")], self._created())
        self.add("plans/compare", "Compare plans", "plans", [
            ["t", "This page compares what each plan includes."],
            ["t", P("API rate limits: Starter {f:plan.starter.rate}, Pro {f:plan.pro.rate}, Business {f:plan.business.rate}.",
                    "Enterprise limits are agreed with you.")],
            ["t", "Log retention: Starter {f:plan.starter.logs}, Pro {f:plan.pro.logs}, Business {f:plan.business.logs}."],
            ["t", "Storage: Starter {f:plan.starter.storage}, Pro {f:plan.pro.storage}, Business {f:plan.business.storage}."],
            self.f("help")], self._created())
        billing_faq = [
            ("Billing FAQ", ["t", P(f"Find invoices in {c} under {{f:menu.billing}}.",
                                    "A refund can be requested within {f:policy.refund} of a charge.")]),
            ("How refunds work", ["t", P("You can request a refund within {f:policy.refund} of being charged.",
                                         f"Open {c}, go to {{f:menu.billing}}, pick the invoice and choose Request refund.")]),
            ("Start a free trial", ["t", P("Every new workspace starts with a free trial of {f:policy.trial} on the Pro plan.",
                                           "No card is needed until the trial ends.")]),
            ("Cancel your subscription", ["t", P(f"Cancel from {{f:menu.billing}} in {c}.",
                                                 "Your data is deleted {f:policy.delete_after} after cancellation.")]),
            ("Add seats", ["t", P("Each extra seat costs {f:billing.seat_usd} per month.",
                                  f"Invite people from {{f:menu.members}} in {c}; seats are added automatically.")]),
            ("Buy more storage", ["t", P("Each extra 100 GB costs {f:billing.storage_usd} per month.",
                                         f"Buy it from {{f:menu.billing}} in {c}.")]),
        ]
        for title, para in billing_faq:
            self.add(f"billing/{slugify(title)}", title, "billing",
                     [*self.fs("intro", "before"), para, *self.fs("faq_billing", "steps", "tip", "related", "help")],
                     self._created())
        policies = [
            ("Service level agreement", ["t", P("The Business plan guarantees {f:policy.sla} monthly uptime.",
                                                "If we miss it, you receive a service credit of {f:policy.sla_credit} of that month's fee.")]),
            ("Backups", ["t", P("Automatic backups are taken every {f:policy.backup_every} and kept for {f:policy.backup_keep}.",
                                f"Restore them from {c} under Data → Backups.")]),
            ("Data retention after cancellation", ["t", "When you cancel, your data is deleted {f:policy.delete_after} after the subscription ends."]),
            ("Support hours", ["t", P("Our support team is available {f:policy.support_hours}.",
                                      "Enterprise customers can reach their support manager outside these hours for urgent issues.")]),
            ("File uploads", ["t", "Files up to {f:policy.upload_mb} can be uploaded through the console or the API."]),
            ("Sessions and sign-in", ["t", P("A console session lasts {f:policy.session}.",
                                             "Passwords must be at least {f:policy.password} long.")]),
            ("Maintenance windows", ["t", P("Planned maintenance happens {f:policy.maintenance}.",
                                            "We announce it at least 48 hours ahead on the status page.")]),
            ("Refund policy", ["t", P("Refunds can be requested within {f:policy.refund} of a charge.",
                                      "Refunds go back to the original payment method.")]),
            ("Free trial terms", ["t", "The free trial lasts {f:policy.trial}. At the end you choose a plan or the workspace is paused."]),
            ("Acceptable use", ["t", "Don't use Acme Cloud to send spam, host malware or attack other services."]),
            ("Security overview", ["t", P("Data is encrypted at rest and in transit.",
                                          "Passwords must be at least {f:policy.password} long, and sessions expire after {f:policy.session}.")]),
            ("Privacy and subprocessors", ["t", "We list every subprocessor we use and notify you 30 days before adding one."]),
        ]
        for title, para in policies:
            self.add(f"policies/{slugify(title)}", title, "policies",
                     [*self.fs("intro", "overview"), para, *self.fs("data", "why", "related", "help")], self._created())
        menus = [("Find your invoices", "menu.billing"), ("Connect an integration", "menu.integrations"),
                 ("Create an API key", "menu.api_keys"), ("Invite your team", "menu.members")]
        for title, key in menus:
            self.add(f"getting-started/{slugify(title)}", title, "getting-started", [
                *self.fs("intro", "before", "permissions"), ["t", f"Open {c} and go to {{f:{key}}}."],
                *self.fs("steps", "tip", "troubleshoot", "related", "help")], self._created())
        self.add("integrations", "Integrations", "integrations", [
            ["t", f"Acme Cloud connects to these services: {{list:integrations}}. Connect them in {c} under {{f:menu.integrations}}."],
            self.f("why"), self.f("help")], self._created())
        self.add("features", "Features", "features", [
            ["t", "Everything you can do with Acme Cloud: {list:features}."], self.f("why"), self.f("help")], self._created())
        for name, unit in FEATURES:
            self._feature(name, unit, self._created())
        for name in INTEGRATIONS:
            self._integration(name, self._created())
        for res in RESOURCES:
            self._api(res, self._created())
        for code, city in REGIONS:
            k = f"region.{code}"
            self.add(f"regions/{code}", f"The {code} region ({city})", "regions", [
                ["t", P(f"The {code} region is in {city}. It is {{f:{k}.status}}.",
                        "Data stored in a region stays in that region, including backups.")],
                *self.fs("overview", "data", "why", "help")], self._created())
        for i in range(1, 201):
            self._error(i)
        for _ in range(300):
            self._release_notes(self._created(), static=True)
        for _ in range(90):
            self._incident(self._created())

    def _feature(self, name, unit, created, later=True):
        k = slugify(name)
        c = self.console()
        a = self.add(f"features/{k}", name, "features", [
            *self.fs("intro", "why", "overview"),
            ["t", P(f"{name} is available on the {{f:feature.{k}.plan}} plan and above.",
                    f"A Pro workspace can have up to {{f:feature.{k}.limit}}.")],
            *self.fs("before", "permissions"),
            ["t", f"To set it up, open {c} and go to {{f:feature.{k}.menu}}, then choose New and follow the steps."],
            *self.fs("steps", "best", "notify", "audit", "api", "data", "tip", "troubleshoot", "related", "help")], created)
        guides = []
        for title in [f"Get started with {name}", f"Troubleshooting {name}"]:
            g = self.add(f"guides/{slugify(title)}", title, "guides", [
                *self.fs("intro", "before"),
                ["t", f"Go to {{f:feature.{k}.menu}} in {c}. If you don't see it, check that your workspace is on the {{f:feature.{k}.plan}} plan or above."],
                *self.fs("steps", "troubleshoot", "best"),
                ["t", f"If you reach the limit of {{f:feature.{k}.limit}}, remove ones you no longer need or contact sales."],
                *self.fs("tip", "related", "help")], created + timedelta(days=self.rng.randrange(1, 60)) if later else created)
            guides.append(g)
        return [a] + guides

    def _integration(self, name, created, later=True):
        k = slugify(name)
        c = self.console()
        a = self.add(f"integrations/{k}", f"The {name} integration", "integrations", [
            *self.fs("intro", "why"),
            ["t", P(f"The {name} integration is {{f:integration.{k}.status}}.",
                    f"Connect it in {c} under {{f:menu.integrations}} → {name}.")],
            *self.fs("before", "permissions", "overview"),
            ["t", P(f"Acme Cloud sends events to {name} through the webhook URL {{f:integration.{k}.webhook}}.",
                    f"Data syncs every {{f:integration.{k}.sync}}.")],
            *self.fs("steps", "data", "notify", "best", "tip", "troubleshoot", "help")], created)
        g = self.add(f"guides/set-up-{k}", f"Set up {name} step by step", "guides", [
            *self.fs("intro", "before", "permissions"),
            ["t", P(f"1. In {c}, open {{f:menu.integrations}} and choose {name}.",
                    f"2. Authorize Acme Cloud in {name}.",
                    f"3. Point {name}'s incoming webhook at {{f:integration.{k}.webhook}}.",
                    f"4. Wait up to {{f:integration.{k}.sync}} for the first sync.")],
            *self.fs("troubleshoot", "best", "related", "help")],
            created + timedelta(days=self.rng.randrange(1, 60)) if later else created)
        return [a, g]

    def _api(self, res, created):
        nice = res.replace("-", " ")
        verbs = [("list", "GET", f"/v2/{res}", f"List {nice}"), ("get", "GET", f"/v2/{res}/{{id}}", f"Get one of your {nice}"),
                 ("create", "POST", f"/v2/{res}", f"Create {nice}"), ("update", "PATCH", f"/v2/{res}/{{id}}", f"Update {nice}"),
                 ("delete", "DELETE", f"/v2/{res}/{{id}}", f"Delete {nice}")]
        for verb, method, path, title in verbs:
            paras = [["t", P(f"`{method} https://api.acme.cloud{path}` — {title.lower()}.",
                             "Authenticate with an API key in the Authorization header.")],
                     ["t", f"Create API keys in {self.console()} under {{f:menu.api_keys}}."]]
            if verb == "list":
                paras.append(["t", P(f"Results are paginated: pass `page_size` up to {{f:api.{res}.page}} and follow `next`.")])
                if f"cli.{res}.limit" in self.F:
                    paras.append(["t", f"From the command line: `acme {res} list` returns {{f:cli.{res}.limit}} by default; change it with --limit."])
            paras += [["t", "Rate limits depend on your plan; see Compare plans."], self.f("help")]
            self.add(f"api/{res}/{verb}", f"API: {title}", "api", paras, created)

    def _error(self, i):
        code = f"ACME-{1000 + i * 7}"
        r = self.rng
        kind = r.choice(["rate", "limit", "plan", "menu", "upload", "session", "generic"])
        if kind == "rate":
            p = r.choice(["starter", "pro", "business"])
            t = P(f"{code} means the workspace sent more API requests than its plan allows.",
                  f"On the {p.title()} plan the limit is {{f:plan.{p}.rate}}. Wait a minute and retry, or upgrade.")
        elif kind == "limit":
            name, unit = r.choice(FEATURES)
            k = slugify(name)
            t = P(f"{code} appears when you reach the limit for {name}.",
                  f"A Pro workspace can have up to {{f:feature.{k}.limit}}. Remove some, or move to a larger plan.")
        elif kind == "plan":
            name, unit = r.choice(FEATURES)
            k = slugify(name)
            t = P(f"{code} means {name} isn't included in your plan.",
                  f"It needs the {{f:feature.{k}.plan}} plan or above; upgrade under {{f:menu.billing}}.")
        elif kind == "menu":
            t = P(f"{code} means the API key was revoked or has expired.",
                  f"Create a new one in {self.console()} under {{f:menu.api_keys}}.")
        elif kind == "upload":
            t = P(f"{code} means the file is too large.", "The maximum upload size is {f:policy.upload_mb}.")
        elif kind == "session":
            t = P(f"{code} means your session expired.", "Sessions last {f:policy.session}; sign in again.")
        else:
            t = P(f"{code} is a temporary error on our side.", "Retry with exponential backoff; if it persists, check the status page.")
        self.add(f"errors/{code.lower()}", f"Error {code}", "errors", [["t", t], self.f("troubleshoot"), self.f("help")],
                 self._created())

    def _release_notes(self, when: datetime, static=False, lines: list[str] | None = None):
        r = self.rng
        if lines is None:
            pool = [f"Faster loading for {n}." for n, _ in FEATURES] + [f"Fixed a display issue in {n}." for n, _ in FEATURES] + \
                   [f"The {n} integration now retries failed deliveries." for n in INTEGRATIONS]
            lines = r.sample(pool, r.randint(2, 4))
        day = when.strftime("%Y-%m-%d")
        return self.add(f"changelog/{day}-{self.next_id}", f"Release notes, {when.strftime('%B %-d, %Y')}", "changelog",
                        [["t", "\n".join(f"- {x}" for x in lines)]], when)

    def _incident(self, when: datetime):
        r = self.rng
        what = r.choice(["Elevated API latency", "Delayed webhook deliveries", "Console sign-in errors",
                         "Slow dashboard loading", "Export jobs stuck", "Partial outage in one region"])
        code, _ = r.choice(REGIONS)
        mins = r.choice([12, 18, 25, 40, 55, 90])
        return self.add(f"status/incident-{when.strftime('%Y%m%d')}-{self.next_id}", f"Incident: {what} ({when.strftime('%b %-d')})",
                        "incidents", [["t", P(f"{what} affected some workspaces in {code} for {mins} minutes.",
                                              "The cause was found and fixed; no data was lost.")]], when)

    # --- what the record holds for an article now
    def row(self, a: Article) -> dict:
        return {"id": a.id, "slug": a.slug, "title": a.title, "category": a.category,
                "body": text_of(a, self.F, self.lists), "created_at": a.created_at}

    def by_fact(self, key: str) -> list[Article]:
        return [a for a in self.articles.values() if key in a.facts()]

    def mentions_list(self, name: str) -> list[Article]:
        return [a for a in self.articles.values() if any(p[0] == "t" and "{list:" + name + "}" in p[1] for p in a.paras)]


# ------------------------------------------------------------------------------------------------ the month
def office_time(rng: random.Random, day0: datetime, d: int) -> datetime:
    """Office hours on weekday d, or on the weekday before it if d falls on a weekend (never after the window)."""
    t = day0 + timedelta(days=d)
    while t.weekday() >= 5:
        t -= timedelta(days=1)
    return t + timedelta(hours=rng.randint(8, 17), minutes=rng.randint(0, 59), seconds=rng.randint(0, 59))


def new_value(rng: random.Random, f: Fact):
    v = f.value
    if f.kind in ("usd", "eur"):
        return rng.choice([x for x in (v - 5, v - 4, v + 4, v + 5, v + 10) if x > 0 and x != v])
    if f.kind in ("count", "gb", "rate"):
        return rng.choice([x for x in (int(v * 1.5), v * 2, int(v * 0.8)) if x != v and x > 0])
    if f.kind == "days":
        return {7: 14, 14: 30, 30: 45, 90: 120, 45: 60}.get(v, v + 7)
    if f.kind == "hours":
        return {6: 4, 12: 8}.get(v, v + 2)
    if f.kind == "minutes":
        return rng.choice([x for x in (5, 10, 15, 30, 60) if x != v])
    if f.kind == "percent":
        return {"99.9": "99.95", "10": "25"}.get(v, v)
    if f.kind == "status":
        return {"beta": "ga", "preview": "ga", "ga": "beta"}[v]
    if f.kind == "url":
        return re.sub(r"-[a-z0-9]{6}$", "-" + token(rng), v)
    if f.kind == "path":
        sec, name = v.split(" → ", 1)
        return f"{rng.choice([s for s in SECTIONS if s != sec])} → {name}" if not v.startswith("Settings → Billing") \
            else "Account → Billing and plans"
    if f.key == "policy.support_hours":
        return "Monday to Friday, 07:00 to 20:00 UTC"
    if f.key == "policy.maintenance":
        return "Saturdays, 22:00 to 23:30 UTC"
    if f.key.endswith(".plan"):
        return rng.choice([p for p in ["Starter", "Pro", "Business"] if p != v])
    raise ValueError(f.key)


CHANGEABLE_KINDS = ["plan.", "billing.", "policy.", "menu.", "feature.", "integration.", "api.", "cli.", "region."]


def distinct(w: World, key: str, value) -> bool:
    """Whether a value of this fact can be told apart in a reply: no other fact the help center states renders to
    something the value's pattern matches. Plan names and statuses are scored by the first one mentioned instead."""
    from sync.score import pattern
    f = w.F[key]
    if f.kind == "status" or key.endswith(".plan"):
        return True
    p = pattern(f.kind, render(Fact(key, f.kind, value, f.unit)))
    stated = set().union(*(a.facts() for a in w.articles.values()))
    return not any(p.search(render(w.F[o])) for o in stated if o != key)


def simulate(run: str) -> dict:
    cfg = RUNS[run]
    w = World(BASE_SEED)                    # the same help center for pilot and full run
    rng = random.Random(cfg["seed"])         # different changes and questions
    day0, days = cfg["start"], cfg["days"]
    end = day0 + timedelta(days=days)
    articles0 = [w.row(a) | {"updated_at": a.created_at} for a in w.articles.values()]
    for r in articles0:
        r["created_at"] = min(r["created_at"], day0.isoformat())
        r["updated_at"] = r["created_at"]
    plan: list[tuple[datetime, str, dict]] = []   # (time, kind, args), executed in time order below

    def schedule(kind, n, **kw):
        for _ in range(n):
            plan.append((office_time(rng, day0, rng.randrange(days - 1)), kind, kw))

    # fact changes: distinct facts that some active article states, spread over the month
    cands = [k for k, f in w.F.items() if f.changeable and any(k.startswith(p) for p in CHANGEABLE_KINDS)
             and w.by_fact(k) and not k.startswith(tuple(f"feature.{slugify(n)}." for n, _ in NEW_FEATURES))
             and not k.startswith(tuple(f"integration.{slugify(n)}." for n in NEW_INTEGRATIONS))
             and distinct(w, k, w.F[k].value)]
    weights = [6 if k.startswith(("plan.", "billing.", "policy.", "menu.")) else 1 for k in cands]
    picked: list[str] = []
    while len(picked) < cfg["counts"]["fact"]:
        k = rng.choices(cands, weights)[0]
        if k not in picked:
            picked.append(k)
    span = (days - 1) / len(picked)
    for i, k in enumerate(picked):
        plan.append((office_time(rng, day0, int(i * span)), "fact", {"key": k}))
    for kind in ["edit", "new_feature", "new_integration", "release_notes", "incident", "retire_integration",
                 "retire_feature", "prune", "rename", "rewrite"]:
        schedule(kind, cfg["counts"][kind])
    mig = day0 + timedelta(days=cfg["migration_day"], hours=21)
    while mig.weekday() >= 5:
        mig += timedelta(days=1)
    plan.append((mig, "migration", {}))
    plan.sort(key=lambda x: x[0])

    events: list[dict] = []
    history: dict[str, list[tuple[str, object]]] = {}   # fact -> [(time, value)] for questions
    retired: list[dict] = []
    launched: list[dict] = []
    protected: set[int] = set()   # articles that questions rely on keep existing
    new_features = [x for x in NEW_FEATURES]
    new_integrations = list(NEW_INTEGRATIONS)

    def save(t: datetime, a: Article, why: str):
        events.append({"t": t.isoformat(), "op": "save", "why": why, "row": w.row(a) | {"updated_at": t.isoformat()}})

    def delete(t: datetime, a: Article, why: str):
        events.append({"t": t.isoformat(), "op": "delete", "why": why, "id": a.id, "slug": a.slug})
        del w.articles[a.id]

    def resave(t, arts, why, gap=(4, 25)):
        for a in arts:
            t += timedelta(seconds=rng.randint(*gap))
            save(t, a, why)
        return t

    for t, kind, kw in plan:
        if kind == "fact":
            f = w.F[kw["key"]]
            old = f.value
            for _ in range(20):          # a new value that no other fact in the help center states either
                f.value = new_value(rng, Fact(f.key, f.kind, old, f.unit))
                if distinct(w, f.key, f.value):
                    break
            assert f.value != old and distinct(w, f.key, f.value), f.key
            arts = sorted(w.by_fact(f.key), key=lambda a: a.id)
            last = resave(t, arts, f"fact {f.key}")
            history.setdefault(f.key, [("", old)]).append((last.isoformat(), f.value))
            if rng.random() < 0.5:
                a = w._release_notes(last + timedelta(minutes=rng.randint(5, 90)),
                                     lines=[f"Changed: {fill('{f:' + f.key + '}', w.F, w.lists)} — " + f.question.rstrip('?') + "."])
                save(datetime.fromisoformat(a.created_at), a, "release notes")
        elif kind == "edit":
            a = rng.choice([a for a in w.articles.values() if any(p[0] == "f" for p in a.paras)])
            fi = [i for i, p in enumerate(a.paras) if p[0] == "f"]
            i = rng.choice(fi)
            kind_f = a.paras[i][1]
            a.paras[i] = ["f", kind_f, (a.paras[i][2] + rng.randint(1, len(FILLER[kind_f]) - 1)) % len(FILLER[kind_f])]
            save(t, a, "wording")
        elif kind == "rewrite":
            a = rng.choice([a for a in w.articles.values() if len(a.optional) >= 4 and a.id not in protected])
            drop = set(rng.sample(a.optional, len(a.optional) // 2))
            a.paras = [p for i, p in enumerate(a.paras) if i not in drop]
            a.optional = []
            save(t, a, "rewrite")
        elif kind == "rename":
            a = rng.choice([a for a in w.articles.values() if a.category in ("features", "guides", "integrations", "policies")])
            a.title = rng.choice(["How to use ", "All about ", "Working with ", "A guide to "]) + a.title[0].lower() + a.title[1:]
            a.slug = w.unique(a.slug.split("/")[0] + "/" + slugify(a.title), a.id)
            save(t, a, "rename")
        elif kind == "new_feature" and new_features:
            name, unit = new_features.pop(0)
            arts = w._feature(name, unit, t, later=False)
            w.active_features.append(name)
            arts += w.mentions_list("features")
            last = resave(t, arts, f"launch {name}")
            launched.append({"name": name, "t": last.isoformat(), "fact": f"feature.{slugify(name)}.menu"})
            for a in arts[:3]:
                protected.add(a.id)
        elif kind == "new_integration" and new_integrations:
            name = new_integrations.pop(0)
            arts = w._integration(name, t, later=False)
            w.active_integrations.append(name)
            arts += w.mentions_list("integrations")
            last = resave(t, arts, f"launch {name}")
            launched.append({"name": name, "t": last.isoformat(), "fact": f"integration.{slugify(name)}.webhook"})
            for a in arts[:2]:
                protected.add(a.id)
        elif kind == "release_notes":
            a = w._release_notes(t)
            save(t, a, "release notes")
        elif kind == "incident":
            a = w._incident(t)
            save(t, a, "incident")
        elif kind == "retire_integration":
            cands_i = [n for n in w.active_integrations if n in INTEGRATIONS
                       and not any(n == x["name"] for x in retired)
                       and not any(k.startswith(f"integration.{slugify(n)}.") for k in picked)]
            name = rng.choice(cands_i)
            k = slugify(name)
            w.active_integrations.remove(name)
            gone = [a for a in w.articles.values() if any(p[0] == "t" and f"integration.{k}." in p[1] for p in a.paras)]
            for a in gone:
                t += timedelta(seconds=rng.randint(4, 25))
                delete(t, a, f"retire {name}")
            t = resave(t, w.mentions_list("integrations"), f"retire {name}")
            a = w._release_notes(t + timedelta(minutes=10), lines=[f"Retired the {name} integration."])
            save(datetime.fromisoformat(a.created_at), a, "release notes")
            retired.append({"name": name, "t": t.isoformat(), "fact": f"integration.{k}.webhook",
                            "value": w.F[f"integration.{k}.webhook"].value})
        elif kind == "retire_feature":
            cands_f = [n for n, _ in FEATURES if n in w.active_features
                       and not any(k.startswith(f"feature.{slugify(n)}.") for k in picked)]
            name = rng.choice(cands_f)
            k = slugify(name)
            mentioned = [a for a in w.articles.values() if any(p[0] == "t" and f"feature.{k}." in p[1] for p in a.paras)]
            if any(a.category == "errors" for a in mentioned):
                continue   # an error code still refers to it; retire another time
            w.active_features.remove(name)
            for a in mentioned:
                t += timedelta(seconds=rng.randint(4, 25))
                delete(t, a, f"retire {name}")
            t = resave(t, w.mentions_list("features"), f"retire {name}")
            retired.append({"name": name, "t": t.isoformat(), "fact": f"feature.{k}.menu",
                            "value": w.F[f"feature.{k}.menu"].value})
        elif kind == "prune":
            a = rng.choice([a for a in w.articles.values() if a.category in ("incidents", "changelog", "errors")
                            and a.id not in protected])
            delete(t, a, "prune")
        elif kind == "migration":
            w.F["product.console"].value = CONSOLE_NEW
            events.append({"t": t.isoformat(), "op": "sql", "why": "migration",
                           "sql": f"UPDATE articles SET title = replace(title, '{CONSOLE_OLD}', '{CONSOLE_NEW}'), "
                                  f"body = replace(body, '{CONSOLE_OLD}', '{CONSOLE_NEW}') "
                                  f"WHERE body LIKE '%{CONSOLE_OLD}%' OR title LIKE '%{CONSOLE_OLD}%'",
                           "rows": sum(1 for a in w.articles.values() if "product.console" in a.facts())})
            history["product.console"] = [("", CONSOLE_OLD), (t.isoformat(), CONSOLE_NEW)]
    events.sort(key=lambda e: e["t"])
    assert all(e["t"] < end.isoformat() for e in events), "a change after the end of the window"
    final = {a.id: w.row(a) for a in w.articles.values()}

    # ---------------------------------------------------------------- questions
    q: list[dict] = []
    qn = cfg["questions"]
    changed = [(k, h) for k, h in history.items()]
    slots = []
    for k, h in changed:
        for when, value in h[1:]:
            for label, secs in DELAYS:
                at = datetime.fromisoformat(when) + timedelta(seconds=secs)
                if at < end:
                    slots.append((k, when, label, at))
    rng.shuffle(slots)
    # spread evenly over delays: take round-robin by delay label
    by_delay: dict[str, list] = {}
    for s in slots:
        by_delay.setdefault(s[2], []).append(s)
    chosen = []
    while len(chosen) < qn["changed"] and any(by_delay.values()):
        for label, _ in DELAYS:
            if by_delay.get(label) and len(chosen) < qn["changed"]:
                chosen.append(by_delay[label].pop())
    for k, when, label, at in chosen:
        h = history[k]
        f = w.F[k]
        right = [v for t_, v in h if t_ and t_ <= at.isoformat()][-1]
        earlier = [v for t_, v in h if (not t_ or t_ <= at.isoformat()) and v != right]
        q.append({"kind": "changed", "fact": k, "question": f.question, "t": at.isoformat(), "delay": label,
                  "changed_at": when, "right": render(Fact(k, f.kind, right, f.unit)),
                  "stale": [render(Fact(k, f.kind, v, f.unit)) for v in earlier], "fact_kind": f.kind})
    final_facts = set().union(*(a.facts() for a in w.articles.values()))
    stable = [k for k in sorted(final_facts) if k not in history and k != "product.console"
              and any(k.startswith(p) for p in CHANGEABLE_KINDS)]
    for k in rng.sample(stable, qn["unchanged"]):
        f = w.F[k]
        at = day0 + timedelta(seconds=rng.randrange(int((end - day0).total_seconds())))
        q.append({"kind": "unchanged", "fact": k, "question": f.question, "t": at.isoformat(), "delay": "",
                  "changed_at": "", "right": render(f), "stale": [], "fact_kind": f.kind})
    for kind, pool, n in [("deleted", retired, qn["deleted"]), ("new", launched, qn["new"])]:
        cand = []
        for x in pool:
            for label, secs in DELAYS:
                at = datetime.fromisoformat(x["t"]) + timedelta(seconds=secs)
                if at < end:
                    cand.append((x, label, at))
        rng.shuffle(cand)
        for x, label, at in sorted(cand[:n], key=lambda c: c[2]):
            f = w.F[x["fact"]]
            if kind == "deleted":
                q.append({"kind": kind, "fact": x["fact"], "question": f.question, "t": at.isoformat(), "delay": label,
                          "changed_at": x["t"], "right": "", "stale": [render(Fact(f.key, f.kind, x["value"], f.unit))],
                          "fact_kind": f.kind, "name": x["name"]})
            else:
                q.append({"kind": kind, "fact": x["fact"], "question": f.question, "t": at.isoformat(), "delay": label,
                          "changed_at": x["t"], "right": render(f), "stale": [], "fact_kind": f.kind, "name": x["name"]})
    q.sort(key=lambda x: x["t"])
    for i, x in enumerate(q):
        x["qid"] = f"{run}-{i:04d}"
    return {"run": run, "start": day0.isoformat(), "end": end.isoformat(), "articles": articles0, "events": events,
            "questions": q, "final": list(final.values()),
            "facts_changed": {k: [[t_, render(Fact(k, w.F[k].kind, v, w.F[k].unit))] for t_, v in h] for k, h in history.items()}}


def prepare() -> None:
    for run in RUNS:
        out = DIR / run
        out.mkdir(parents=True, exist_ok=True)
        d = simulate(run)
        for name in ("articles", "events", "questions", "final", "facts_changed"):
            (out / f"{name}.json").write_text(json.dumps(d[name], indent=1, ensure_ascii=False))
        (out / "meta.json").write_text(json.dumps({"run": run, "start": d["start"], "end": d["end"]}, indent=1))
        print(run, summary(d))


def load(run: str) -> dict:
    out = DIR / run
    d = {name: json.loads((out / f"{name}.json").read_text()) for name in
         ("articles", "events", "questions", "final", "facts_changed", "meta")}
    return d


def summary(d: dict) -> dict:
    from collections import Counter
    ev = Counter((e["op"], e["why"].split(" ")[0]) for e in d["events"])
    return {"articles_at_start": len(d["articles"]), "articles_at_end": len(d["final"]),
            "chars_at_start": sum(len(a["title"]) + len(a["body"]) for a in d["articles"]),
            "events": {f"{a} {b}": n for (a, b), n in sorted(ev.items())},
            "questions": dict(Counter(q["kind"] for q in d["questions"]))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepare", action="store_true")
    a = ap.parse_args()
    if a.prepare:
        prepare()
    else:
        for run in RUNS:
            print(run, json.dumps(summary(load(run)), indent=1))


if __name__ == "__main__":
    main()
