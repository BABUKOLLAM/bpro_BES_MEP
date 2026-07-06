{
    "name": "bpro Client Onboarding",
    "summary": "One-flow onboarding of a new client organisation (roadmap P7)",
    "description": """
Client onboarding wizard for bpro Super Admins:
* Creates the client company under bpro Corporate
* Creates the Client HR Admin user + employee
* New employees are auto-enrolled in global Induction courses
""",
    "version": "18.0.1.0.0",
    "category": "Administration",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["bpro_base", "bpro_lms", "website"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/client_onboarding_views.xml",
    ],
    "installable": True,
}
