"""Create and seed the demo IT/DevOps SQLite database.

Usage: python scripts/seed_devops_db.py [--force]
"""
import random
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402

SCHEMA = """
CREATE TABLE departments (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE employees (
    id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    department_id INTEGER NOT NULL REFERENCES departments(id),
    title TEXT NOT NULL,
    location TEXT NOT NULL,
    hire_date DATE NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'on_leave', 'terminated'))
);
CREATE TABLE assets (
    id INTEGER PRIMARY KEY,
    asset_tag TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK (type IN ('laptop', 'monitor', 'phone', 'dock')),
    model TEXT NOT NULL,
    serial_number TEXT NOT NULL UNIQUE,
    assigned_to INTEGER REFERENCES employees(id),
    purchase_date DATE NOT NULL,
    warranty_expiry DATE NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('in_use', 'in_stock', 'repair', 'retired'))
);
CREATE TABLE servers (
    id INTEGER PRIMARY KEY,
    hostname TEXT NOT NULL UNIQUE,
    environment TEXT NOT NULL CHECK (environment IN ('prod', 'staging', 'dev')),
    provider TEXT NOT NULL CHECK (provider IN ('aws', 'azure', 'on_prem')),
    region TEXT NOT NULL,
    os TEXT NOT NULL,
    cpu_cores INTEGER NOT NULL,
    memory_gb INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('running', 'stopped', 'maintenance')),
    owner_department_id INTEGER NOT NULL REFERENCES departments(id),
    monthly_cost_usd REAL NOT NULL
);
CREATE TABLE deployments (
    id INTEGER PRIMARY KEY,
    service_name TEXT NOT NULL,
    server_id INTEGER NOT NULL REFERENCES servers(id),
    version TEXT NOT NULL,
    deployed_by INTEGER NOT NULL REFERENCES employees(id),
    deployed_at DATETIME NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('success', 'failed', 'rolled_back'))
);
CREATE TABLE incidents (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('sev1', 'sev2', 'sev3', 'sev4')),
    service_name TEXT NOT NULL,
    server_id INTEGER REFERENCES servers(id),
    reported_by INTEGER NOT NULL REFERENCES employees(id),
    assigned_to INTEGER REFERENCES employees(id),
    opened_at DATETIME NOT NULL,
    resolved_at DATETIME,
    status TEXT NOT NULL CHECK (status IN ('open', 'investigating', 'resolved'))
);
CREATE TABLE software_licenses (
    id INTEGER PRIMARY KEY,
    software TEXT NOT NULL,
    vendor TEXT NOT NULL,
    seats_total INTEGER NOT NULL,
    seats_used INTEGER NOT NULL,
    cost_per_seat_usd REAL NOT NULL,
    renewal_date DATE NOT NULL
);
CREATE TABLE access_requests (
    id INTEGER PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    system TEXT NOT NULL,
    access_level TEXT NOT NULL CHECK (access_level IN ('read', 'write', 'admin')),
    requested_at DATETIME NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected')),
    approved_by INTEGER REFERENCES employees(id)
);
"""

DEPARTMENTS = ["Engineering", "DevOps", "Data Science", "HR", "Finance", "Sales", "Design"]
TITLES = {
    "Engineering": ["Backend Engineer", "Frontend Engineer", "Mobile Engineer", "Engineering Manager", "QA Engineer"],
    "DevOps": ["DevOps Engineer", "Site Reliability Engineer", "IT Administrator"],
    "Data Science": ["Data Scientist", "ML Engineer", "Data Engineer"],
    "HR": ["HR Manager", "HR Executive", "Talent Acquisition Specialist"],
    "Finance": ["Accountant", "Finance Manager"],
    "Sales": ["Account Executive", "Business Developer"],
    "Design": ["UI/UX Designer", "Product Designer"],
}
FIRST = ["Ali", "Ahmed", "Sara", "Ayesha", "Usman", "Fatima", "Hamza", "Zainab", "Bilal", "Hira", "Omar", "Maryam",
         "Hassan", "Sana", "Imran", "Noor", "Faisal", "Amna", "Saad", "Iqra", "Danish", "Mahnoor", "Taha", "Rabia"]
LAST = ["Khan", "Ahmed", "Malik", "Hussain", "Raza", "Iqbal", "Sheikh", "Butt", "Chaudhry", "Qureshi", "Mirza", "Abbasi"]
LOCATIONS = ["Islamabad", "Lahore", "Karachi", "Remote"]
MODELS = {
    "laptop": ["MacBook Pro 14 M3", "MacBook Air M2", "Dell XPS 15", "Lenovo ThinkPad X1", "HP EliteBook 840"],
    "monitor": ["Dell U2723QE", "LG 27UL850", "Samsung S27A"],
    "phone": ["iPhone 15", "Pixel 8"],
    "dock": ["CalDigit TS4", "Dell WD19"],
}
SERVICES = ["auth-service", "billing-api", "web-frontend", "data-pipeline", "ml-inference", "notification-service",
            "hr-portal", "analytics-dashboard"]
SOFTWARE = [("GitHub Enterprise", "GitHub"), ("Jira", "Atlassian"), ("Confluence", "Atlassian"), ("Slack", "Salesforce"),
            ("Figma", "Figma"), ("JetBrains All Products", "JetBrains"), ("Microsoft 365", "Microsoft"),
            ("Datadog", "Datadog"), ("1Password Business", "AgileBits"), ("Postman Enterprise", "Postman")]
SYSTEMS = ["AWS Console", "Production DB", "GitHub Org", "Jenkins", "Grafana", "Kubernetes Cluster", "VPN", "HR Portal"]
INCIDENT_TITLES = ["High latency on {s}", "{s} returning 5xx errors", "Memory leak in {s}", "Disk full on host running {s}",
                   "SSL certificate expiring for {s}", "Failed cron job in {s}", "Database connection pool exhausted ({s})"]


def seed(path: Path) -> None:
    rnd = random.Random(42)
    today = date.today()
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)

    con.executemany("INSERT INTO departments (id, name) VALUES (?, ?)", list(enumerate(DEPARTMENTS, 1)))

    employees = []
    used = set()
    for eid in range(1, 61):
        while True:
            fn, ln = rnd.choice(FIRST), rnd.choice(LAST)
            if (fn, ln) not in used:
                used.add((fn, ln))
                break
        dept_id = rnd.choices(range(1, len(DEPARTMENTS) + 1), weights=[30, 8, 10, 4, 3, 4, 5])[0]
        dept = DEPARTMENTS[dept_id - 1]
        status = rnd.choices(["active", "on_leave", "terminated"], weights=[88, 5, 7])[0]
        employees.append((eid, f"{fn} {ln}", f"{fn.lower()}.{ln.lower()}@stixor.com", dept_id, rnd.choice(TITLES[dept]),
                          rnd.choice(LOCATIONS), today - timedelta(days=rnd.randint(30, 2200)), status))
    con.executemany("INSERT INTO employees VALUES (?, ?, ?, ?, ?, ?, ?, ?)", employees)
    active_ids = [e[0] for e in employees if e[7] == "active"]
    devops_ids = [e[0] for e in employees if e[3] in (1, 2) and e[7] == "active"]

    assets = []
    aid = 1
    for emp in employees:
        kinds = ["laptop"] + (["monitor"] if rnd.random() < 0.7 else []) + (["dock"] if rnd.random() < 0.3 else [])
        for kind in kinds:
            purchased = today - timedelta(days=rnd.randint(60, 1500))
            status = "in_use" if emp[7] != "terminated" else rnd.choice(["in_stock", "retired"])
            assets.append((aid, f"STX-{kind[:2].upper()}-{aid:04d}", kind, rnd.choice(MODELS[kind]), f"SN{rnd.randint(10**8, 10**9)}",
                           emp[0] if status == "in_use" else None, purchased,
                           purchased + timedelta(days=365 * rnd.choice([1, 2, 3])), status))
            aid += 1
    for _ in range(15):
        kind = rnd.choice(list(MODELS))
        purchased = today - timedelta(days=rnd.randint(30, 900))
        assets.append((aid, f"STX-{kind[:2].upper()}-{aid:04d}", kind, rnd.choice(MODELS[kind]), f"SN{rnd.randint(10**8, 10**9)}",
                       None, purchased, purchased + timedelta(days=730), rnd.choice(["in_stock", "repair"])))
        aid += 1
    con.executemany("INSERT INTO assets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", assets)

    servers = []
    for sid in range(1, 25):
        env = rnd.choices(["prod", "staging", "dev"], weights=[40, 30, 30])[0]
        provider = rnd.choices(["aws", "azure", "on_prem"], weights=[60, 25, 15])[0]
        region = {"aws": rnd.choice(["us-east-1", "eu-west-1", "ap-south-1"]),
                  "azure": rnd.choice(["eastus", "westeurope"]), "on_prem": "islamabad-dc"}[provider]
        cores = rnd.choice([2, 4, 8, 16, 32])
        mem = cores * rnd.choice([2, 4, 8])
        servers.append((sid, f"{env}-{rnd.choice(SERVICES).split('-')[0]}-{sid:02d}", env, provider, region,
                        rnd.choice(["Ubuntu 22.04", "Ubuntu 24.04", "Amazon Linux 2023", "Debian 12"]), cores, mem,
                        rnd.choices(["running", "stopped", "maintenance"], weights=[85, 8, 7])[0],
                        rnd.choice([1, 2, 3]), round(cores * 18.5 + mem * 2.1 + rnd.uniform(-10, 40), 2)))
    con.executemany("INSERT INTO servers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", servers)

    deployments = []
    for did in range(1, 201):
        when = datetime.combine(today, datetime.min.time()) - timedelta(minutes=rnd.randint(30, 60 * 24 * 90))
        deployments.append((did, rnd.choice(SERVICES), rnd.randint(1, len(servers)),
                            f"v{rnd.randint(1, 4)}.{rnd.randint(0, 20)}.{rnd.randint(0, 9)}", rnd.choice(devops_ids), when,
                            rnd.choices(["success", "failed", "rolled_back"], weights=[85, 9, 6])[0]))
    con.executemany("INSERT INTO deployments VALUES (?, ?, ?, ?, ?, ?, ?)", deployments)

    incidents = []
    for iid in range(1, 81):
        svc = rnd.choice(SERVICES)
        opened = datetime.combine(today, datetime.min.time()) - timedelta(minutes=rnd.randint(60, 60 * 24 * 120))
        status = rnd.choices(["open", "investigating", "resolved"], weights=[10, 10, 80])[0]
        resolved = opened + timedelta(minutes=rnd.randint(20, 60 * 48)) if status == "resolved" else None
        incidents.append((iid, rnd.choice(INCIDENT_TITLES).format(s=svc),
                          rnd.choices(["sev1", "sev2", "sev3", "sev4"], weights=[5, 15, 45, 35])[0], svc,
                          rnd.randint(1, len(servers)), rnd.choice(active_ids), rnd.choice(devops_ids), opened, resolved, status))
    con.executemany("INSERT INTO incidents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", incidents)

    licenses = []
    for lid, (sw, vendor) in enumerate(SOFTWARE, 1):
        total = rnd.choice([10, 25, 50, 75, 100])
        licenses.append((lid, sw, vendor, total, rnd.randint(int(total * 0.4), total), round(rnd.uniform(4, 60), 2),
                         today + timedelta(days=rnd.randint(-20, 365))))
    con.executemany("INSERT INTO software_licenses VALUES (?, ?, ?, ?, ?, ?, ?)", licenses)

    requests = []
    for rid in range(1, 61):
        status = rnd.choices(["pending", "approved", "rejected"], weights=[25, 60, 15])[0]
        requests.append((rid, rnd.choice(active_ids), rnd.choice(SYSTEMS), rnd.choice(["read", "write", "admin"]),
                         datetime.combine(today, datetime.min.time()) - timedelta(minutes=rnd.randint(60, 60 * 24 * 60)),
                         status, rnd.choice(devops_ids) if status != "pending" else None))
    con.executemany("INSERT INTO access_requests VALUES (?, ?, ?, ?, ?, ?, ?)", requests)

    con.commit()
    con.close()


def main() -> None:
    url = get_settings().resolved_db_url()
    if not url.startswith("sqlite:///"):
        sys.exit(f"Seeding only supports SQLite; DEVOPS_DATABASE_URL is {url}")
    path = Path(url[len("sqlite:///"):])
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if "--force" not in sys.argv:
            print(f"{path} already exists (use --force to recreate).")
            return
        path.unlink()
    seed(path)
    print(f"Seeded {path}")


if __name__ == "__main__":
    main()
