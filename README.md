# bpro LMS + PMS

Learning Management + Performance Management SaaS for organisations, by **Team bpro**.
Built on **Odoo 18 Community** with custom addons.

## Architecture

Follows the **bpro LMS & PMS Architecture Roadmap** (see `#7.B Pro PMS/bpro_LMS_PMS_Architecture_Roadmap_1.docx`):
one Odoo instance, **single database, multi-company** — clients are child companies of the
**bpro Corporate** master company. Global content (Induction, Compliance, Policy) is owned by
bpro Corporate and visible to all clients; client content stays isolated per company.

| Piece | What it is |
|---|---|
| Odoo 18 (Docker) | Application server, single DB, multi-company white-label SaaS |
| PostgreSQL 16 (Docker) | Database |
| `addons/bpro_base` | Four-tier roles (Super Admin / Client HR / HOD / Employee) + three-tier record rules (company / department / self) |
| `addons/bpro_pms` | Performance Management: goals, review cycles, appraisals (custom, from scratch) |
| `addons/bpro_lms` | Learning Management: Odoo eLearning + course taxonomy + global-vs-client content ownership + courses linked to goals |
| `addons/bpro_branding` | bpro branding for the platform |

Test logins (local dev): `hr.a@test`, `hod.a@test`, `emp.a@test`, `hr.b@test` — password `bpro@2026`.

## Run locally

```bash
colima start            # start the Docker VM (if not running)
docker compose up -d    # start Odoo + Postgres
```

Open http://localhost:8069 — create a database (master password is in `config/odoo.conf`),
then install the apps **bpro PMS** and **bpro LMS** from the Apps menu
(remove the default *Apps* filter and search "bpro").

After changing addon code:

```bash
docker compose restart odoo
# and upgrade the module inside Odoo (Apps → module → Upgrade), or:
docker compose exec odoo odoo -c /etc/odoo/odoo.conf -d <dbname> -u bpro_pms,bpro_lms --stop-after-init
docker compose restart odoo
```

## Multi-tenant SaaS model

Each client organisation gets its own Odoo database (`list_db = True` locally;
in production, database routing per subdomain via `dbfilter`). Billing/provisioning
layer to be added.

## Credentials

- Odoo master password: see `config/odoo.conf` (`admin_passwd`)
- Postgres: odoo / odoo (local dev only)
