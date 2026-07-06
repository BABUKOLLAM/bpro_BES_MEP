{
    "name": "bpro SCORM",
    "summary": "SCORM 1.2 package player for legacy course content (roadmap P4)",
    "description": """
SCORM support for bpro LMS:
* Upload a SCORM 1.2 .zip on a SCORM Package record
* Package is extracted server-side; launch file found via imsmanifest.xml
* Built-in player exposes the SCORM 1.2 JavaScript API (window.API)
* lesson_status completed/passed marks the linked course slide as done,
  feeding normal eLearning completion and the bpro training reports
""",
    "version": "18.0.1.0.0",
    "category": "Website/eLearning",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["website_slides", "bpro_base", "bpro_pms"],
    "data": [
        "security/ir.model.access.csv",
        "security/scorm_security.xml",
        "views/scorm_views.xml",
        "views/player_template.xml",
    ],
    "installable": True,
}
