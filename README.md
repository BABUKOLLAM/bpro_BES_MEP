# bpro LMS + PMS

Learning Management + Performance Management SaaS for organisations, by **Team bpro**.
Built on **Odoo 18 Community** with custom addons.

## Architecture

| Piece | What it is |
|---|---|
| Odoo 18 (Docker) | Application server, one database per client organisation (multi-tenant) |
| PostgreSQL 16 (Docker) | Database |
| `addons/bpro_pms` | Performance Management: goals, review cycles, appraisals (custom, from scratch) |
| `addons/bpro_lms` | Learning Management: builds on Odoo eLearning; links courses to performance goals |
| `addons/bpro_branding` | bpro branding for the platform |

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
