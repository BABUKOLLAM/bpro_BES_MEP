{
    "name": "bpro LMS — Learning Management",
    "summary": "Courses, training paths and certifications under the bpro brand",
    "description": """
bpro Learning Management System
===============================
Builds on Odoo eLearning (website_slides):
* Courses with videos, documents and quizzes
* Certifications and completion tracking
* Training linked to performance goals (with bpro PMS)
""",
    "version": "18.0.1.0.0",
    "category": "Website/eLearning",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["website_slides", "hr", "bpro_pms"],
    "data": [
        "views/lms_menus.xml",
    ],
    "application": True,
    "installable": True,
}
