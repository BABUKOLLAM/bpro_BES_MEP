# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An **Odoo 18 Community** ERP deployment for **Team bpro**: a multi-company
white-label SaaS (bpro LMS + PMS: Learning Management + Performance
Management) that has grown, for its India client **ME Polymers**, into a
much larger custom suite — "BES" (Business Enterprise Suite) — covering
Sales/CRM, Inventory, Manufacturing, Finance, HR/Payroll/Recruitment,
Attendance, Project, Quality, Plant & Machinery, Fleet, Logistics,
Helpdesk, Field Sales, Collections, and an executive dashboard, all as
custom addons layered on stock Odoo Community apps. Everything lives in
`addons/`; there is no separate frontend or backend service.

Single Odoo instance, **single database, multi-company**: client
organisations are child companies of a root **bpro Corporate** company.
Content owned by bpro Corporate (Induction, Compliance, Policy courses)
is visible to all clients; each client's own data stays isolated to its
company via record rules (see Security below).

README.md and DEPLOY.md describe the original bpro LMS/PMS product in
detail; this file focuses on orienting an AI assistant across the full
current addon set.

## Running locally

```bash
colima start            # start the Docker VM (macOS/Colima only, if not running)
docker compose up -d    # start Odoo 18 + Postgres 16
```

Open http://localhost:8069 — create a database (master password is
`admin_passwd` in `config/odoo.conf`), then install the desired `bpro_*`
apps from the Apps menu (clear the default *Apps* filter, search "bpro").

After changing addon code:

```bash
docker compose restart odoo
# then upgrade the module(s) — either via Apps → module → Upgrade, or:
docker compose exec odoo odoo -c /etc/odoo/odoo.conf -d <dbname> -u <module1>,<module2> --stop-after-init
docker compose restart odoo
```

`addons/` is bind-mounted into the container at `/mnt/extra-addons`, so
Python/XML edits are visible immediately — only a restart (+ `-u` upgrade
for data/view/field changes) is needed, no rebuild.

## Tests

Every `bpro_*` addon that has business logic ships tests under
`addons/<module>/tests/`, using Odoo's `TransactionCase`/`HttpCase` and a
`--test-tags /<module>` filter. Run them against a **throwaway database**
on a non-default HTTP port so they never collide with a live dev/prod
instance on 8069:

```bash
docker compose exec odoo odoo -c /etc/odoo/odoo.conf -d bpro_test --http-port 8071 \
  -i bpro_base,bpro_pms,bpro_lms,bpro_branding,bpro_onboarding,bpro_billing,bpro_scorm,bpro_approval,bpro_xlsx_export,bpro_inventory,bpro_sales,bpro_manufacturing,bpro_finance,bpro_hr,bpro_logistics,bpro_quality,bpro_plant,bpro_project,bpro_fleet,bpro_dashboard,bpro_helpdesk,bpro_field_sales,bpro_collections,l10n_in,website_payment \
  --test-tags /bpro_pms,/bpro_lms,/bpro_billing,/bpro_onboarding,/bpro_scorm,/bpro_approval,/bpro_xlsx_export,/bpro_inventory,/bpro_sales,/bpro_manufacturing,/bpro_finance,/bpro_hr,/bpro_logistics,/bpro_quality,/bpro_plant,/bpro_project,/bpro_fleet,/bpro_dashboard,/bpro_helpdesk,/bpro_field_sales,/bpro_collections \
  --stop-after-init --without-demo=all
docker compose exec db psql -U odoo -d postgres -c 'DROP DATABASE bpro_test;'
```

Expect the log line `... 0 failed, 0 error(s) of N tests`. This exact
command (list of modules kept in sync with `ls addons/`) is what
`.github/workflows/test.yml` runs on every push/PR to `main` — CI adds
`bpro_recruitment` and `bpro_attendance` as they land; **when you add a
new testable addon, add it to both the `-i` and `--test-tags` lists in
the workflow, or its tests silently never run in CI.**

**To run a single module's tests** (much faster while iterating), narrow
both `-i`/`--test-tags` to just that module and its dependency chain,
e.g. for `bpro_sales`:

```bash
docker compose exec odoo odoo -c /etc/odoo/odoo.conf -d bpro_test --http-port 8071 \
  -i bpro_base,bpro_approval,bpro_sales -c /etc/odoo/odoo.conf \
  --test-tags /bpro_sales --stop-after-init --without-demo=all
docker compose exec db psql -U odoo -d postgres -c 'DROP DATABASE bpro_test;'
```

`--test-tags /<module>` runs every test in that module; append
`:ClassName` or `:ClassName.test_method` to narrow further (standard
Odoo test-tag syntax).

CI's health-check step polls `docker compose ps db` for "healthy" up to
60s before running tests, and always tears the stack down (`docker
compose down -v`) afterward, win or lose.

## Repository layout

```
addons/           every custom module (bpro_* suite + vendored OCA payroll)
config/           odoo.conf (local dev) / odoo.staging.conf / odoo.prod.conf
deploy/           production docker-compose + Caddyfile (HTTPS) + static file mounts
docker-compose.yml  local dev stack (Odoo 18 + Postgres 16, ports 8069/8072)
scripts/          one-off ops scripts run via `odoo shell` (see below)
docs/             end-user manual
DEPLOY.md         full production runbook — read before touching deploy/ or config/*.prod/staging
README.md         product-level description of the original LMS+PMS roadmap
```

`scripts/` are standalone Python/bash utilities invoked with `odoo shell
-c ... -d ... < script.py` (not addon code, not auto-run) for first-boot
setup (`setup_india_accounting.py`, `set_menu_order.py`,
`set_homepage_content.py`) and pre-launch/ops cleanup (`remove_test_data.py`,
`remove_me_polymers_demo_data.py`, `backup.sh`, `healthcheck.sh`). Each
has a module docstring explaining why it's a script rather than addon
data — read that before assuming the same result could be had with a
normal XML data file or view inheritance.

## Addon structure and conventions

Every `bpro_*` addon follows the same Odoo skeleton:
`__manifest__.py`, `models/`, `views/`, `security/` (`ir.model.access.csv`
+ an `ir.rule`/`res.groups` XML file), `tests/`, optionally `data/`,
`report/`, `controllers/`, `wizard/`, `static/`.

Conventions to follow when adding to or creating a `bpro_*` module:

- **Model names** are namespaced `bpro.<domain>.<thing>` (e.g.
  `bpro.approval.mixin`, `bpro.policy`, `bpro.ar.aging.wizard`,
  `bpro.field.journey.plan`). Fields added onto *native* Odoo models
  (e.g. `hr.employee`, `sale.order`) get a `bpro_` prefix
  (`bpro_sales_area_ids`, `bpro_on_time`) to stay visibly distinct from
  native fields in the same view.
- **Manifest**: `version` is always `18.0.1.0.0`; `license` is
  `LGPL-3`; `author`/`website` are `Team bpro` / `https://bpropms.com`.
  The `description` is written as a mini design doc explaining *what
  native Odoo/Enterprise gap this module fills and why* — read a
  module's manifest description first, it's the fastest way to
  understand its purpose and boundaries (what's deliberately left to
  native Odoo).
- **Every manifest's `data:` list order matters** — security
  (`ir.model.access.csv` then rule/group XML) before `views`/`data`
  that reference those access rules.
- **Multi-company scoping**: any model that isn't inherently
  company-scoped via `bpro_base`'s record rules on `hr.employee` needs
  its own `company_id` field (default `self.env.company`) and, where
  relevant, its own `ir.rule` — copy the three-tier pattern (see
  Security below) rather than inventing a new one.
- **Tests** use `odoo.tests.common.TransactionCase`/`HttpCase`, tagged
  implicitly by the addon's `--test-tags /<module>` convention.
  `bpro_base/tests/common.py` is the canonical example of a shared test
  fixture (two companies, one department each, one user per role tier)
  — new security-sensitive tests across the suite build on the same
  shape rather than duplicating company/user setup.

### Philosophy: extend native Odoo, don't replace it

Every module's manifest description explicitly states what it fills in
versus what's already native. Default to this same split when adding
functionality: if Odoo Community already does it (e.g. lead capture,
quotation generation, BOM/routing, batch picking), configure it — don't
duplicate it in a `bpro_*` model. Custom code exists specifically for
gaps: BES BRD requirements Odoo Community doesn't cover, or the ones
that are Enterprise-only and unavailable in this Community image
(Quality, Payroll, Fixed Assets, Helpdesk, `stock_barcode`,
`account_reports` are all built from scratch here for exactly that
reason — see each module's manifest for specifics).

## Security model (read `addons/bpro_base` first)

`bpro_base` defines the **four-tier role hierarchy** every other module's
security reuses, each tier implying the one below (`implied_ids`):

1. `group_employee` — self-service only
2. `group_hod` — own department only
3. `group_client_hr` — own company only (also implies native
   `hr.group_hr_user`)
4. `group_super_admin` — all companies, all data, client onboarding

And the matching **three-tier `ir.rule` domain pattern** applied to
`hr.employee`/`hr.employee.public` (and copied by other modules onto
their own models):

- self: `[('user_id', '=', user.id)]`
- HOD: `[('department_id.manager_id.user_id', '=', user.id)]`
- HR/company: `[('company_id', 'in', company_ids)]`
- super admin: `[(1, '=', 1)]`

New modules with department/company/self-sensitive data should reuse
`bpro_base`'s existing groups rather than defining parallel roles (see
`bpro_recruitment`'s `bpro.vacancy.request`, which scopes
`group_hod`/`group_client_hr` this same way).

### Threshold-gated approvals (`bpro_approval`)

`bpro.approval.mixin` (`addons/bpro_approval/models/bpro_approval_mixin.py`)
is the shared building block for "block this action once some amount
exceeds a per-company configurable threshold, require a manager to
approve" — used across Sales (discount %), Inventory (stock-adjustment
value), Finance (3-way-match tolerance), Project (budget overrun), and
more. A host model must override `_approval_policy_key()`,
`_approval_amount()`, and `_approval_group_xmlid()`, and store the
threshold itself in `bpro.policy` (per-company key/value config,
`addons/bpro_approval/models/bpro_policy.py`).

**Critical gotcha when using this mixin**: call
`action_request_approval()` proactively, as soon as the threshold-crossing
value is saved (in `create`/`write`) — never call it just before raising
a `UserError` to block the same action. Odoo rolls back the whole
transaction (including any writes made earlier in that same call) when
an exception propagates out of an action, so a request-approval write
made right before the raise is silently discarded. The blocking action
itself should only *read* `approval_state`, never write to it in the
same call that might raise. `approval_state` can only be set to
`approved`/`rejected` via `action_approve()`/`action_reject()` (which
check `_approval_check_is_approver()`) — `create()`/`write()` on the
mixin explicitly reject any other path setting a decided state, so
don't try to set it directly via a data file or migration script.

### Excel export (`bpro_xlsx_export`)

`bpro.xlsx.export.mixin` is the shared "export report wizard lines to
.xlsx with a column picker" building block, used by every
Finance/Inventory report wizard. Deliberately kept dependency-free of
`bpro_finance`/`bpro_inventory` (both depend on it, not on each other)
— new report wizards should inherit this mixin rather than hand-rolling
an export button.

## Deployment

Full runbook: **DEPLOY.md** (VPS sizing, DNS, first-boot module install,
India GST/accounting setup order, backups, staging, going-live checklist,
update-in-place procedure) — read it before changing anything under
`deploy/` or `config/*.prod.conf`/`*.staging.conf`.

Two gotchas worth knowing before touching prod/staging config without
reading the full runbook:

- `config/odoo.prod.conf` and `deploy/Caddyfile` are **single-file**
  Docker bind mounts. `git pull` on the server replaces files via
  unlink+recreate, which detaches a running container from the file (it
  keeps the old, deleted inode) — a plain `restart` does **not** pick up
  the change; you must `up -d --force-recreate <service>`.
- Module install/upgrade on the production image must go through
  `/entrypoint.sh odoo ...`, not a bare `odoo ...` — the entrypoint is
  what translates the container's `HOST`/`USER`/`PASSWORD` env vars into
  the Postgres connection (`odoo.prod.conf` has none hardcoded).

## CI

`.github/workflows/test.yml` (GitHub Actions, `Regression Suite`) runs on
every push/PR to `main`: brings up `docker compose`, waits for Postgres
health, runs the same install+test-tags command documented above against
a `bpro_test` DB on port 8071, and greps the Odoo test-runner's own
summary line for `0 failed, 0 error(s)` — a partial pass still fails CI.
Logs are dumped on failure; the stack is always torn down with `docker
compose down -v`.
