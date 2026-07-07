{
    "name": "bpro Branding",
    "summary": "bpro LMS + PMS branding for the SaaS platform",
    "version": "18.0.1.0.0",
    "category": "Hidden",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["web", "website"],
    "data": [
        "data/branding_data.xml",
        "views/login_templates.xml",
    ],
    "assets": {
        "web._assets_primary_variables": [
            ("prepend", "bpro_branding/static/src/scss/bpro_variables.scss"),
        ],
        "web.assets_frontend": [
            "bpro_branding/static/src/scss/bpro_login.scss",
            "bpro_branding/static/src/js/login_show_password.js",
        ],
    },
    "installable": True,
    "auto_install": False,
}
