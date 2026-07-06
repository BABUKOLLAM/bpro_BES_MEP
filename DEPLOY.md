# bpro LMS + PMS — Production Deployment Runbook

## What you need

- A VPS with **2 vCPU / 4 GB RAM / 40 GB disk** minimum (Hetzner, DigitalOcean,
  AWS Lightsail, or an Indian provider like E2E Networks all work). Ubuntu 24.04.
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
git clone <your-repo-url> bpro-lms-pms && cd bpro-lms-pms/deploy
cp .env.example .env            # then edit: strong POSTGRES_PASSWORD
nano ../config/odoo.prod.conf   # change admin_passwd
nano Caddyfile                  # set real domains
docker compose -f docker-compose.prod.yml up -d
```

Caddy obtains and renews HTTPS certificates automatically.

## 3. First boot

```bash
# create + initialize the production database
docker compose -f docker-compose.prod.yml exec odoo \
  odoo -c /etc/odoo/odoo.conf -d bpro \
  -i base,bpro_base,bpro_pms,bpro_lms,bpro_branding,bpro_onboarding,bpro_billing,bpro_scorm,l10n_in \
  --without-demo=all --stop-after-init
docker compose -f docker-compose.prod.yml restart odoo
```

Note `l10n_in` — the Indian chart of accounts/GST for bpro Corporate's
invoicing. Then log in as `admin`/`admin` and **immediately**:

1. Change the admin login/password (Settings → Users) and enable **2FA**.
2. Rename company 1 to *bpro Corporate*, upload the logo.
3. Settings → Technical → System Parameters: `web.base.url` = `https://app.bprolms.com`.

## 4. Outgoing email

Settings → Technical → Outgoing Mail Servers:

- SMTP: `smtp.gmail.com`, port 587, TLS
- User: `tech@bpropms.com` + a Google Workspace **App Password**
  (same setup as ZAG SIGNS uses)

## 5. Backups

```bash
crontab -e
# 30 2 * * * /root/bpro-lms-pms/scripts/backup.sh >> /var/log/bpro-backup.log 2>&1
```

Copy `~/bpro-backups` off-server periodically (rclone to Google Drive works well).

## 6. Going live checklist

- [ ] `admin_passwd` changed in `config/odoo.prod.conf`
- [ ] Strong super-admin password + 2FA on `tech@bpropms.com`
- [ ] `scripts/remove_test_data.py` reviewed and run (archives all @test users
      and demo client companies)
- [ ] SMTP tested (Settings → Outgoing Mail Servers → Test Connection)
- [ ] Backup cron installed and first backup verified restorable
- [ ] Billing plans created with real pricing (bpro PMS → Billing → Plans)
- [ ] First real client onboarded via the wizard, portal domain added to
      Caddyfile, `docker compose ... restart caddy`

## 7. Updating the app (new addon code)

```bash
cd bpro-lms-pms && git pull
docker compose -f deploy/docker-compose.prod.yml exec odoo \
  odoo -c /etc/odoo/odoo.conf -d bpro -u bpro_base,bpro_pms,bpro_lms,bpro_branding,bpro_onboarding,bpro_billing,bpro_scorm --stop-after-init
docker compose -f deploy/docker-compose.prod.yml restart odoo
```

## Scaling later

- 4 GB RAM comfortably serves ~10 client companies of 50-100 employees.
- Grow: raise `workers` in odoo.prod.conf (2×CPU+1) and VPS size.
- Heavy growth: move Postgres to a managed instance, add a second Odoo
  container behind Caddy (sessions are DB-backed, this Just Works).
