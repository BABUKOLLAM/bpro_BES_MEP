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

**Super admin (all companies): `tech@bpropms.com` / `bpro#1234`** — change this password before production.
Test logins (local dev): `hr.a@test`, `hod.a@test`, `emp.a@test`, `hr.b@test` — password `bpro@2026`.
**Remove all @test users before any production rollout.**

## Lifecycle automation (roadmap P3)

- New employee record → auto-enrolled in all visible **Induction**-tagged courses
- **bpro LMS: Annual Re-Induction** cron (every 12 months) → re-assigns **Re-Induction**-tagged
  courses to all client employees, resetting completion
- Publishing a **Policy Updation**-tagged course → auto-enrolls every employee it is visible to
- Each performance goal shows live **Training Progress %** from its linked courses

## Roadmap status

- [x] P0-P2: multi-company architecture, four-tier security (checklist 3.4: 10/10 green)
- [x] P3: induction/re-induction/policy automation (certificates pending)
- [x] P5: role dashboards — bpro PMS → Reporting (Training Compliance + Goals Analysis),
      auto-scoped: HR = company, HOD = department, employee = self, super admin = all clients
- [x] P6: competencies (global or client-owned) linked to courses; **Training Needs**
      flagged on appraisals auto-enroll the employee in matching courses when the
      appraisal completes; **bpro 360** tab on the employee form (goals + appraisals +
      training needs + avg goal progress + avg training completion + last rating);
      training progress % on each goal
- [x] P7 (core): **Onboard New Client** wizard (bpro PMS menu, super admin only) —
      company + HR admin + first department + induction enrollment in one flow
- [x] P4: SCORM 1.2 — upload packages (bpro PMS → Configuration → SCORM Packages),
      built-in player at /scorm/play/<id>, completion flows into course tracking
- [x] P7 (rest): white-label website per client (onboarding wizard) + `bpro_billing`
      per-seat subscriptions (bpro PMS → Billing) with daily invoice cron
- [x] Production kit: `deploy/` (compose + Caddy HTTPS), `config/odoo.prod.conf`,
      `scripts/backup.sh`, `scripts/remove_test_data.py` — see **DEPLOY.md**
- [ ] P8: pilot with 1-2 real clients (needs a server + domain — see DEPLOY.md)

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
