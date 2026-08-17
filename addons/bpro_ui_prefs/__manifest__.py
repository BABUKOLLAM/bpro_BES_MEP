{
    "name": "bpro UI Preferences — Language & Theme Systray",
    "summary": "Always-visible language switcher and Day/Night/Auto theme toggle in the top bar",
    "description": """
Two permanent controls in the backend systray (top-right, visible on
every screen):

* Language switcher - globe icon listing every installed language;
  selecting one saves it on the user's own account and reloads.
* Theme toggle - cycles Day / Night / Auto. Odoo 18 Community has no
  built-in dark mode, so Night applies a curated dark stylesheet over
  the backend's main surfaces (forms, lists, kanban, control panel,
  dialogs, dropdowns, chatter). Auto follows the device's own
  light/dark preference live. The choice persists per browser
  (localStorage) and applies before first paint - no flash.
""",
    "version": "18.0.1.0.0",
    "category": "Hidden",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["web"],
    "assets": {
        "web.assets_backend": [
            "bpro_ui_prefs/static/src/systray/ui_prefs.js",
            "bpro_ui_prefs/static/src/systray/ui_prefs.xml",
            "bpro_ui_prefs/static/src/systray/ui_prefs.scss",
            "bpro_ui_prefs/static/src/dark_theme.scss",
        ],
    },
    "installable": True,
    "auto_install": False,
}
