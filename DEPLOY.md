# bpro LMS + PMS — Production Deployment Runbook

## What you need

- A VPS with **2 vCPU / 8 GB RAM / 40 GB disk** minimum (Hetzner, DigitalOcean,
  AWS Lightsail, or an Indian provider like E2E Networks all work). Ubuntu 24.04.
  Raised from the original 4 GB minimum now that the platform runs 22 addons
  (Manufacturing, Quality, Dashboard, etc. all add to base registry memory) —
  see `config/odoo.prod.conf`'s worker/memory-limit comments for the math.
- DNS control for `bprolms.com` (or whichever domain you choose).

## 1. DNS

Point these A-records at the server's IP:

- `app.bprolms.com` — main/admin portal
- one subdomain per client, matching the domain entered in the onboarding
  wizard (e.g. `bella.bprolms.com`)

## 2. Server setup (once)

```bash
ssh root@SERVER-IP
curl -fsSL https://get.docker.com | sh
git clone <your-repo-url> bpro-bes-mini-erp-odoo && cd bpro-bes-mini-erp-odoo/deploy
cp .env.example .env            # then edit: strong POSTGRES_PASSWORD
nano ../config/odoo.prod.conf   # change admin_passwd
nano Caddyfile                  # set real domains
docker compose -f docker-compose.prod.yml up -d
```

Caddy obtains and renews HTTPS certificates automatically.

`docker-compose.prod.yml` caps each service's logs at 10MB x 5 files
(json-file driver, timestamped JSON per line via `docker compose logs`).
Docker's default has no cap and will otherwise fill the disk over the
life of the deployment - don't remove the `logging:` block per service.

## 3. First boot

```bash
# create + initialize the production database
docker compose -f docker-compose.prod.yml exec odoo \
  /entrypoint.sh odoo -c /etc/odoo/odoo.conf -d bpro \
  -i base,bpro_base,bpro_pms,bpro_lms,bpro_branding,bpro_onboarding,bpro_billing,bpro_scorm,bpro_approval,bpro_xlsx_export,bpro_inventory,bpro_sales,bpro_manufacturing,bpro_finance,bpro_hr,bpro_logistics,bpro_quality,bpro_plant,bpro_project,bpro_fleet,bpro_dashboard,bpro_helpdesk,bpro_field_sales,bpro_collections,l10n_in,website_payment \
  --without-demo=all --stop-after-init --no-http
docker compose -f docker-compose.prod.yml restart odoo
```

`/entrypoint.sh` is required, not optional - it's what translates the
container's HOST/USER/PASSWORD env vars into the actual DB connection
(odoo.prod.conf deliberately has none hardcoded). Calling `odoo` directly
skips that translation and fails with a Postgres socket-connection error
even though the DB is reachable. `--no-http` avoids a port-already-in-use
error if the main odoo process is already running on 8069 in the same
container (true for every use of this command except the very first).

Then log in as `admin`/`admin` and **immediately**:

1. Change the admin login/password (Settings → Users) and enable **2FA**.
2. Rename company 1 to *bpro Corporate*, upload the logo.
3. Settings → Technical → System Parameters: `web.base.url` = `https://app.bprolms.com`.
4. Run the India accounting setup (do this before onboarding any real
   client — it puts the root company on India's GST chart of accounts
   with an April-March fiscal year, which every client company then
   inherits; Odoo refuses to change chart templates once any accounting
   entry exists, so this must happen while the database is still empty):

   ```bash
   docker compose -f docker-compose.prod.yml exec -i odoo \
     /entrypoint.sh odoo shell -c /etc/odoo/odoo.conf -d bpro --no-http \
     < ../scripts/setup_india_accounting.py
   ```

   (Must run inside `odoo shell`, not over XML-RPC — see the script's
   docstring for why.)

5. Optional: reorder the Apps switcher so the client's actual business
   apps appear before generic Odoo utility apps (Discuss, Calendar,
   Contacts, etc.) — a per-deployment preference, re-run any time the
   installed app list changes:

   ```bash
   docker compose -f docker-compose.prod.yml exec -i odoo \
     /entrypoint.sh odoo shell -c /etc/odoo/odoo.conf -d bpro --no-http \
     < ../scripts/set_menu_order.py
   ```

6. Optional: set the public homepage content (hero, product section,
   module highlights, login CTA). Also a script rather than addon data -
   see the script's docstring for why an `inherit_id="website.homepage"`
   view wouldn't actually affect the live page once the Website Builder
   has created a per-website copy:

   ```bash
   docker compose -f docker-compose.prod.yml exec -i odoo \
     /entrypoint.sh odoo shell -c /etc/odoo/odoo.conf -d bpro --no-http \
     < ../scripts/set_homepage_content.py
   ```

## 4. Outgoing email

Settings → Technical → Outgoing Mail Servers:

- SMTP: `smtp.gmail.com`, port 587, TLS
- User: `tech@bpropms.com` + a Google Workspace **App Password**
  (same setup as ZAG SIGNS uses)

## 5. Backups

```bash
crontab -e
# 30 2 * * * /root/bpro-bes-mini-erp-odoo/scripts/backup.sh >> /var/log/bpro-backup.log 2>&1
```

### Off-server copy

A macOS LaunchAgent (`com.bpro.offsitebackup`, installed on the
operator's Mac) pulls `~/bpro-backups` down via `rsync` over SSH daily at
9 AM. The puller lives client-side, not in this repo - the pull script is
`~/bpro-offsite-backups/pull_backup.sh` on that Mac, logging to
`~/bpro-offsite-backups/pull.log`. This is a real, verified off-site copy
(different provider, different physical location) with zero new
credentials required, but it has one real limitation: it only runs while
that Mac is on and network-reachable, so it is not a 24/7-guaranteed
copy. Confirm it ran recently:

```bash
tail -5 ~/bpro-offsite-backups/pull.log   # on the operator's Mac
```

**Recommended upgrade path**: move to automated cloud object storage
(Backblaze B2, AWS S3, or similar) once ready to provision an account -
those need only an API key/secret (no interactive OAuth), are cheap
(cents/month at this data volume), and don't depend on any single
laptop being powered on. `rclone` to Google Drive is also an option but
needs an OAuth-connected remote, set up interactively by whoever owns
the target Drive account.

### Uptime monitoring

`scripts/healthcheck.sh` runs every 5 minutes via cron, checks the live
site (`https://mepcrm.in/odoo/login`) and all three containers, and logs
every check plus a clearly marked line on any up/down state change:

```bash
crontab -e
# */5 * * * * /root/bpro-bes-mini-erp-odoo/scripts/healthcheck.sh
tail -f /var/log/bpro-healthcheck.log
```

**Known gap: this logs downtime, it does not page anyone.** There is no
outgoing alert (email/SMS/Slack) wired up - nobody gets notified in
real time if the site goes down, only if someone happens to check the
log. Closing this gap needs one of:

- A dedicated SMTP account (separate from Odoo's own mail config, since
  if Odoo itself is down it can't send its own downtime alert) - hand
  over host/port/user/password and the script can be extended to email
  on every state change, or
- A free external monitoring service (UptimeRobot, Better Uptime,
  Healthchecks.io) - these need an account signup, which has to be done
  by a human, not automated; once set up, hand over the ping
  URL/webhook and it's a small addition to the cron script.

### Verifying a backup actually restores

A backup you've never restored is a hope, not a plan. Test periodically —
this restores into a **throwaway database**, never `bpro` itself:

```bash
cd /root/bpro-bes-mini-erp-odoo/deploy
LATEST=$(ls -t ~/bpro-backups/bpro-db-*.dump | head -1)
docker compose -f docker-compose.prod.yml exec -T db psql -U odoo -d postgres \
    -c 'CREATE DATABASE bpro_restore_test OWNER odoo;'
docker compose -f docker-compose.prod.yml exec -T db pg_restore -U odoo \
    -d bpro_restore_test --no-owner < "$LATEST"

# sanity check: row counts should match the live db, and the ledger must
# balance to exactly 0.00 (every journal entry's debits = credits)
docker compose -f docker-compose.prod.yml exec -T db psql -U odoo \
    -d bpro_restore_test -c "SELECT round(sum(balance),2) FROM account_move_line;"

docker compose -f docker-compose.prod.yml exec -T db psql -U odoo -d postgres \
    -c 'DROP DATABASE bpro_restore_test;'
```

Last verified 2026-07-31: row counts on `res_partner`, `account_move`,
`account_move_line`, `sale_order`, `hr_employee`, and `ir_attachment` all
matched the live database exactly, and the ledger balance summed to
`0.00`.

## 6. Static downloads (e.g. the customer user manual)

Caddy serves `deploy/static/` directly at `/downloads/*` — no Odoo involved,
so it works even if the app is down. To publish a file:

```bash
cp bpro_user_manual.docx deploy/static/manuals/bpro_user_manual.docx
docker compose -f deploy/docker-compose.prod.yml restart caddy
```

It's then reachable at `https://app.bprolms.com/downloads/manuals/bpro_user_manual.docx`
(or under each client's own portal domain, since every site block gets the
same `handle_path` — see `deploy/Caddyfile`).

## 7. Going live checklist

- [ ] `admin_passwd` changed in `config/odoo.prod.conf`
- [ ] Strong super-admin password + 2FA on `tech@bpropms.com`
- [ ] `scripts/setup_india_accounting.py` run before onboarding any real
      client (must be done while the database has zero accounting entries)
- [ ] `scripts/remove_test_data.py` reviewed and run (archives all @test users
      and demo client companies)
- [ ] SMTP tested (Settings → Outgoing Mail Servers → Test Connection)
- [ ] Backup cron installed and first backup verified restorable
- [ ] Billing plans created with real pricing (bpro PMS → Billing → Plans)
- [ ] First real client onboarded via the wizard, portal domain added to
      Caddyfile, `docker compose ... restart caddy`

## 8. Updating the app (new addon code)

```bash
cd bpro-bes-mini-erp-odoo && git pull
docker compose -f deploy/docker-compose.prod.yml exec odoo \
  /entrypoint.sh odoo -c /etc/odoo/odoo.conf -d bpro -u bpro_base,bpro_pms,bpro_lms,bpro_branding,bpro_onboarding,bpro_billing,bpro_scorm,bpro_approval,bpro_xlsx_export,bpro_inventory,bpro_sales,bpro_manufacturing,bpro_finance,bpro_hr,bpro_logistics,bpro_quality,bpro_plant,bpro_project,bpro_fleet,bpro_dashboard,bpro_helpdesk,bpro_field_sales,bpro_collections --stop-after-init --no-http
docker compose -f deploy/docker-compose.prod.yml restart odoo
```

Keep this list in sync with `ls addons/` — a module left off here silently
never gets its migrations/data updates applied on deploy.

`git pull` on the server authenticates via a **read-only deploy key**
(`~/.ssh/bpro_deploy_key`, added to the GitHub repo's Deploy Keys, scoped
to this repo only, can't push). `addons/` and `config/odoo.prod.conf` are
directory/file bind mounts respectively — `addons/` changes are picked up
live by a running container (it's a directory mount, changes inside it
are visible immediately), but **`config/odoo.prod.conf` and
`deploy/Caddyfile` are single-*file* bind mounts**, and `git pull`
replaces files via unlink+recreate rather than editing in place. Docker's
bind mount for a single file is attached to the specific inode at
container-*creation* time, not the path — after `git pull` replaces the
file, an already-running container keeps looking at the old, now-deleted
inode's content. A plain `restart` does **not** fix this (it restarts the
process, not the mount namespace). If `config/odoo.prod.conf` or
`deploy/Caddyfile` changed, you must **force-recreate**, not just
restart:

```bash
docker compose -f deploy/docker-compose.prod.yml up -d --force-recreate odoo   # if odoo.prod.conf changed
docker compose -f deploy/docker-compose.prod.yml up -d --force-recreate caddy  # if Caddyfile changed
```

(Discovered 2026-08-05 setting up staging: `caddy reload` silently kept
serving the pre-`git pull` Caddyfile because of exactly this — reload
re-reads from the same already-open, now-stale file handle.)

## 9. Staging environment

A second, low-memory Odoo container running the same code against a
**separate database** (`bpro_staging`, on the *same* Postgres server as
production — not a second Postgres instance) and a separate Odoo
filestore volume. Deliberately lightweight because the VPS was sized for
one production instance and normally has only ~2 GB RAM free — see the
comment block in `deploy/docker-compose.staging.yml` for the full
trade-off (staging shares production's Postgres *engine*, so a runaway
staging query could affect prod DB performance — accepted deliberately
over paying for a second VPS).

**DNS**: `staging.mepcrm.in` needs an A record pointing at this server's
IP before Caddy can obtain it an HTTPS certificate (Caddy will keep
retrying automatically in the background once the record exists — no
further action needed here once DNS is added).

**Bring up / tear down**:
```bash
cd /root/bpro-bes-mini-erp-odoo/deploy
docker compose -f docker-compose.staging.yml up -d      # start
docker compose -f docker-compose.staging.yml down       # stop (keeps the DB/filestore)
```

**Refreshing staging from a production backup** (do this whenever
staging data goes stale):
```bash
cd /root/bpro-bes-mini-erp-odoo/deploy
docker compose -f docker-compose.staging.yml down
docker compose -f docker-compose.prod.yml exec -T db psql -U odoo -d postgres \
    -c 'DROP DATABASE bpro_staging;'
docker compose -f docker-compose.prod.yml exec -T db psql -U odoo -d postgres \
    -c 'CREATE DATABASE bpro_staging OWNER odoo;'
LATEST=$(ls -t ~/bpro-backups/bpro-db-*.dump | head -1)
docker compose -f docker-compose.prod.yml exec -T db pg_restore -U odoo \
    -d bpro_staging --no-owner < "$LATEST"

# CRITICAL — every refresh copies real customer data including SMTP config
# and cron jobs. Run these two before ever starting staging-odoo, or a
# restored copy of prod data can send real emails / run real scheduled
# jobs against real customer records:
docker compose -f docker-compose.prod.yml exec -T db psql -U odoo -d bpro_staging \
    -c "UPDATE ir_mail_server SET active = false;"
docker compose -f docker-compose.prod.yml exec -T db psql -U odoo -d bpro_staging \
    -c "UPDATE ir_cron SET active = false;"

docker compose -f docker-compose.staging.yml up -d
```

Re-enable specific cron jobs individually (Settings → Technical →
Scheduled Actions, in the staging UI) only for the ones you're actually
testing.

## Scaling later

- 8 GB RAM comfortably serves ~10 client companies of 50-100 employees
  running the full 22-addon platform.
- Grow: raise `workers` in odoo.prod.conf (2×CPU+1, keeping the memory-limit
  math above in mind) and VPS size.
- Heavy growth: move Postgres to a managed instance, add a second Odoo
  container behind Caddy (sessions are DB-backed, this Just Works).
