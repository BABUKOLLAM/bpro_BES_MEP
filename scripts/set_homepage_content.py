"""Sets the public homepage content for ME Polymers - a "wow" landing
page with a production banner, a dedicated products section, module
highlights, and a login CTA, replacing the plain earlier version.

This exists as a script (not addon XML data with inherit_id="website.
homepage") because the live homepage is a per-WEBSITE customized copy -
Odoo's copy-on-write mechanism creates a standalone view record (same
key, website_id set, no inherit_id) the first time a page is edited via
the Website Builder, and that specific copy is what's actually served,
NOT the generic addon-shipped website.homepage view. An inherit_id-based
override in an addon would attach to the generic view and silently have
no effect on what's live. Confirmed by inspecting both records directly:
env.ref('website.homepage') resolves to the generic stub (~200 chars),
while the live page is a separate website-specific record (~9000+
chars, website_id set, inherit_id empty).

Falls back to writing the generic website.homepage view if no
website-specific copy exists yet (e.g. on a fresh install before anyone
has touched the Website Builder) - correct for that case too, since the
generic view is what would be served until someone customizes it.

Images referenced below live in addons/bpro_branding/static/src/img/
homepage/ - representative industry stock photography (Pexels, free
commercial-use license), not literal photos of this facility. Swap
those files for real photos whenever available; no script change is
needed, just replace the files with the same names.

Run via odoo shell:

    docker compose -f deploy/docker-compose.prod.yml exec -i odoo \\
      /entrypoint.sh odoo shell -c /etc/odoo/odoo.conf -d bpro --no-http \\
      < scripts/set_homepage_content.py

Idempotent: safe to re-run.
"""

ARCH = r"""<t name="Home" t-name="website.homepage">
    <t t-call="website.layout">
        <t t-set="pageName" t-value="'homepage'"/>
        <div id="wrap" class="oe_structure">

<style>
    .bes-page { --bes-ink: #17281f; --bes-forest: #1f3327; --bes-forest-2: #2a4636; --bes-line: #3c5a48;
                --bes-paper: #f6f4ef; --bes-accent: #7fd858; --bes-accent-ink: #14210e; --bes-muted: #b7c6bd;
                font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    .bes-hero { background: radial-gradient(1100px 520px at 15% -10%, #2c4a37 0%, var(--bes-forest) 55%, var(--bes-ink) 100%);
                color: var(--bes-paper); padding: 6rem 0 5.5rem; overflow: hidden; }
    .bes-eyebrow { letter-spacing: .22em; text-transform: uppercase; font-size: .78rem; color: #9fd6ae;
                   font-weight: 600; margin-bottom: 1.1rem; }
    .bes-hero h1 { font-size: 2.9rem; font-weight: 700; line-height: 1.08; letter-spacing: -0.01em; color: #fff; }
    .bes-hero h1 .accent { color: var(--bes-accent); }
    .bes-hero p.lead { color: var(--bes-muted); font-size: 1.12rem; max-width: 34rem; margin-top: 1.4rem; }
    .bes-btn-primary { background: var(--bes-accent); color: var(--bes-accent-ink); font-weight: 700;
                        padding: .85rem 1.9rem; border-radius: 4px; text-decoration: none; display: inline-block;
                        transition: transform .15s ease, box-shadow .15s ease; }
    .bes-btn-primary:hover { color: var(--bes-accent-ink); transform: translateY(-1px);
                              box-shadow: 0 10px 24px rgba(127,216,88,.25); }
    .bes-btn-ghost { border: 1px solid rgba(255,255,255,.35); color: #fff; padding: .8rem 1.7rem; border-radius: 4px;
                      text-decoration: none; display: inline-block; margin-left: .9rem; }
    .bes-btn-ghost:hover { color: #fff; background: rgba(255,255,255,.08); }
    .bes-badge { display: inline-flex; align-items: center; gap: .5rem; background: rgba(255,255,255,.08);
                  border: 1px solid rgba(255,255,255,.15); color: var(--bes-paper); font-size: .85rem;
                  padding: .45rem .9rem; border-radius: 999px; margin-bottom: 1.6rem; }
    .bes-badge b { color: var(--bes-accent); }
    .bes-hero-photo { border-radius: 14px; overflow: hidden; box-shadow: 0 30px 60px rgba(0,0,0,.45);
                       border: 1px solid rgba(255,255,255,.12); position: relative; }
    .bes-hero-photo img { width: 100%; height: 100%; object-fit: cover; display: block; min-height: 340px; }
    .bes-hero-photo .cap { position: absolute; left: 0; right: 0; bottom: 0; padding: .9rem 1.1rem;
                            background: linear-gradient(0deg, rgba(0,0,0,.65), transparent);
                            color: #eafbef; font-size: .8rem; letter-spacing: .04em; }

    .bes-section { padding: 4.5rem 0; }
    .bes-section.dark { background: var(--bes-ink); color: var(--bes-paper); }
    .bes-section.light { background: var(--bes-paper); color: var(--bes-forest); }
    .bes-kicker { text-transform: uppercase; letter-spacing: .2em; font-size: .78rem; font-weight: 700;
                   color: #6f8a78; margin-bottom: .6rem; }
    .bes-section.dark .bes-kicker { color: #7fa38c; }
    .bes-h2 { font-size: 2.1rem; font-weight: 700; letter-spacing: -0.01em; margin-bottom: 1rem; }

    .bes-photo-frame { border-radius: 12px; overflow: hidden; box-shadow: 0 18px 40px rgba(23,40,31,.14); }
    .bes-photo-frame img { width: 100%; height: 100%; object-fit: cover; display: block; min-height: 300px; }

    .bes-client-card { background: #fff; border: 1px solid #e3ded2; border-radius: 10px; padding: 1.8rem 2rem;
                         box-shadow: 0 18px 40px rgba(23,40,31,.06); margin-top: 1.6rem; }
    .bes-client-card h3 { font-weight: 700; color: var(--bes-forest); margin-bottom: .4rem; }
    .bes-client-card .addr { color: #6b7c73; font-size: .92rem; margin-top: .8rem; }

    .bes-tag { display: inline-block; font-weight: 600; font-size: .78rem; letter-spacing: .03em;
                padding: .38rem .85rem; border-radius: 999px; margin: 0 .5rem .5rem 0;
                background:#21362a; color:#eafbef; border: 1px solid #33503f; }

    .bes-feature { padding: 1.7rem 1.5rem; border-radius: 10px; background: #21362a; border: 1px solid #33503f;
                    height: 100%; }
    .bes-feature .icon { width: 2.4rem; height: 2.4rem; border-radius: 8px; background: rgba(127,216,88,.12);
                          color: var(--bes-accent); display: flex; align-items: center; justify-content: center;
                          font-size: 1.15rem; margin-bottom: .9rem; }
    .bes-feature h4 { color: #fff; font-weight: 700; margin: .55rem 0 .5rem; font-size: 1.05rem; }
    .bes-feature p { color: var(--bes-muted); font-size: .92rem; margin: 0; }

    .bes-cta { background: linear-gradient(120deg, var(--bes-forest) 0%, #16241c 100%); color: #fff;
                border-radius: 14px; padding: 3rem; text-align: center; }
    .bes-cta h3 { font-size: 1.9rem; font-weight: 700; margin-bottom: .6rem; }
    .bes-cta p { color: var(--bes-muted); margin-bottom: 1.6rem; }

    .bes-footer { background: var(--bes-ink); color: #93a89c; padding: 2.4rem 0; font-size: .88rem; }
    .bes-footer a { color: #c9dccf; text-decoration: none; }
    .bes-footer a:hover { color: #fff; }
    .bes-footer .credit { color: #6f8a78; margin-top: .3rem; display: flex; align-items: center;
                           gap: .5rem; justify-content: flex-end; }
    .bes-footer .credit img { height: 18px; width: auto; border-radius: 3px; opacity: .9; }
    .bes-footer .credit a { color: #9fd6ae; }
    @media (max-width: 991px) { .bes-hero-photo { margin-top: 2.5rem; } }
</style>

<div class="bes-page">

    <section class="bes-hero">
        <div class="container">
            <div class="row align-items-center g-5">
                <div class="col-lg-7">
                    <span class="bes-badge">&#9679; <b>Live</b> &#8212; private business system for ME Polymers Private Limited</span>
                    <div class="bes-eyebrow">bpro Enterprise Suite</div>
                    <h1>The <span class="accent">CRM &amp; ERP</span><br/>built exclusively for<br/>ME Polymers.</h1>
                    <p class="lead">Sales, production, inventory, finance and HR &#8212; one private system
                        running ME Polymers' business end to end, from quotation to GST-ready invoice.</p>
                    <div class="mt-4">
                        <a href="/web/login" class="bes-btn-primary">Login to Dashboard &#8594;</a>
                        <a href="#about" class="bes-btn-ghost">About this system</a>
                    </div>
                </div>
                <div class="col-lg-5">
                    <div class="bes-hero-photo">
                        <img src="/bpro_branding/static/src/img/homepage/production-hero.jpg"
                             alt="EVA sheet material handled on the production floor"/>
                        <div class="cap">On the production floor &#8212; sheet material in process</div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <section class="bes-section light" id="about">
        <div class="container">
            <div class="row align-items-center g-5">
                <div class="col-lg-6 o_colored_level">
                    <div class="bes-kicker">About the company</div>
                    <h2 class="bes-h2">ME Polymers Private Limited &amp; MAYFIELD.</h2>
                    <p style="color:#4d5d54; font-size:1.05rem;">Innovative polymer solutions specializing in EVA
                        sheets, mats, and recycled eco-materials for industrial and commercial applications &#8212;
                        part of the Mayfield Corporate group of companies.</p>
                    <div class="bes-client-card">
                        <h3>ME Polymers Pvt. Ltd.</h3>
                        <div style="color:#7fa38c; font-weight:600; font-size:.8rem; letter-spacing:.08em; text-transform:uppercase;">Polymers &amp; Eco-Materials</div>
                        <div class="addr">
                            KAUZARIYYA Compound, Edathala, Aluva, Kerala 683561<br/>
                            <span t-esc="'+91 97471 38875'"/>  &#183;  care@mepcrm.in
                        </div>
                    </div>
                </div>
                <div class="col-lg-6">
                    <div class="bes-photo-frame">
                        <img src="/bpro_branding/static/src/img/homepage/production-floor.jpg"
                             alt="Production line at work"/>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <section class="bes-section dark">
        <div class="container">
            <div class="row align-items-center g-5">
                <div class="col-lg-6">
                    <div class="bes-photo-frame">
                        <img src="/bpro_branding/static/src/img/homepage/eva-sheets.jpg"
                             alt="Colorful EVA sheet stock"/>
                    </div>
                </div>
                <div class="col-lg-6">
                    <div class="bes-kicker">What we manufacture</div>
                    <h2 class="bes-h2" style="color:#fff;">EVA sheets, mats &amp; eco-materials.</h2>
                    <p style="color: var(--bes-muted); font-size:1.05rem;">A full range of EVA-based sheet and mat
                        products, including recycled eco-material lines, built for industrial and commercial use
                        &#8212; from flooring and packaging to specialty foam applications.</p>
                    <div class="mt-3">
                        <span class="bes-tag">EVA Sheets</span>
                        <span class="bes-tag">EVA Mats</span>
                        <span class="bes-tag">Recycled Eco-Materials</span>
                        <span class="bes-tag">Custom Colors &amp; Sizes</span>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <section class="bes-section dark" style="padding-top:0;">
        <div class="container">
            <div class="bes-kicker">What it runs</div>
            <h2 class="bes-h2" style="color:#fff;">One system, every department</h2>
            <div class="row g-3 mt-2">
                <div class="col-md-4 col-lg-2">
                    <div class="bes-feature"><div class="icon"><i class="fa fa-handshake-o"/></div><h4>Sales &amp; CRM</h4>
                        <p>Quotations, orders, discount approvals, targets.</p></div>
                </div>
                <div class="col-md-4 col-lg-2">
                    <div class="bes-feature"><div class="icon"><i class="fa fa-industry"/></div><h4>Production</h4>
                        <p>Work orders, BOMs, capacity, output tracking.</p></div>
                </div>
                <div class="col-md-4 col-lg-2">
                    <div class="bes-feature"><div class="icon"><i class="fa fa-cubes"/></div><h4>Inventory</h4>
                        <p>Stock, reorder levels, adjustment approvals.</p></div>
                </div>
                <div class="col-md-4 col-lg-2">
                    <div class="bes-feature"><div class="icon"><i class="fa fa-balance-scale"/></div><h4>Finance</h4>
                        <p>GST invoicing, 3-way match, AR ageing.</p></div>
                </div>
                <div class="col-md-4 col-lg-2">
                    <div class="bes-feature"><div class="icon"><i class="fa fa-users"/></div><h4>HR &amp; Admin</h4>
                        <p>Employees, expenses, approvals.</p></div>
                </div>
                <div class="col-md-4 col-lg-2">
                    <div class="bes-feature"><div class="icon"><i class="fa fa-truck"/></div><h4>Fleet &amp; Logistics</h4>
                        <p>Dispatch, vendor delivery performance.</p></div>
                </div>
            </div>
        </div>
    </section>

    <section class="bes-section light">
        <div class="container">
            <div class="bes-cta">
                <h3>Ready to get to work?</h3>
                <p>Log in with your ME Polymers account to continue.</p>
                <a href="/web/login" class="bes-btn-primary">Login to bpro Enterprise Suite &#8594;</a>
            </div>
        </div>
    </section>

    <footer class="bes-footer">
        <div class="container">
            <div class="row">
                <div class="col-md-6">
                    <div style="color:#c9dccf; font-weight:700;">bpro Enterprise Suite</div>
                    <div>Private CRM &amp; ERP for ME Polymers Private Limited</div>
                </div>
                <div class="col-md-6 text-md-end">
                    <div><a href="mailto:care@mepcrm.in">care@mepcrm.in</a>  &#183;  +91 97471 38875</div>
                    <div class="credit">
                        <span>Powered by</span>
                        <img src="/web/image/website/1/logo" alt="bpro"/>
                        <span>&#183;  Designed &amp; developed by Dr. Babu. B.
                             &#183;  <a href="https://www.drbabu.in" target="_blank">www.drbabu.in</a></span>
                    </div>
                </div>
            </div>
        </div>
    </footer>

</div>
        </div>
    </t>
</t>"""

website = env["website"].search([], limit=1)
if not website:
    raise SystemExit("no website found")

specific = env["ir.ui.view"].search(
    [("key", "=", "website.homepage"), ("website_id", "=", website.id)], limit=1
)
if specific:
    specific.write({"arch": ARCH})
    target = f"website-specific view id={specific.id}"
else:
    generic = env.ref("website.homepage", raise_if_not_found=False)
    if not generic:
        raise SystemExit("no website.homepage view found at all")
    generic.write({"arch": ARCH})
    target = f"generic view id={generic.id} (no website-specific copy existed yet)"

env.cr.commit()
print(f"homepage content updated on {target}")
