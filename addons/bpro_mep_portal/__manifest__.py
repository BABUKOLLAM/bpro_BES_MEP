{
    "name": "ME Polymers Portal — Landing & Login",
    "summary": "ME Polymers-branded landing page and login for the mepcrm.in ERP",
    "description": """
Public-facing identity for ME Polymers Private Limited's internal ERP
(mepcrm.in). Deliberately a SEPARATE addon from bpro_hrms_portal: the
two products (ME Polymers Mini ERP vs bpro HCM HRMS Suite Pro) serve
different customer bases from the same VPS and must never share
branding, palette, or copy.

* Landing page (/) - an internal-system gateway, not a marketing site:
  company identity, the ERP's functional coverage (sales to dispatch to
  books), and a sign-in call to action. Industrial slate + cyan palette
  drawn from the ME Polymers logo.
* Login - centered elevated card over a dark industrial backdrop with
  the company logo and "Internal Business System" framing. Overrides
  bpro_branding's minimal card (priority 30 > 20); bpro_branding's
  show-password toggle on the inner form keeps working.
""",
    "version": "18.0.1.0.0",
    "category": "Hidden",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["web", "website"],
    "data": [
        "views/landing_templates.xml",
        "views/login_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "bpro_mep_portal/static/src/scss/mep_portal.scss",
            "bpro_mep_portal/static/src/js/mep_portal.js",
        ],
    },
    "installable": True,
    "auto_install": False,
}
