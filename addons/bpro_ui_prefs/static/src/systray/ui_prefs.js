/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { _t } from "@web/core/l10n/translation";

const THEME_KEY = "bpro_theme_mode"; // "day" | "night" | "auto"
const darkMedia = window.matchMedia("(prefers-color-scheme: dark)");

function storedMode() {
    const mode = browserStorageGet();
    return ["day", "night", "auto"].includes(mode) ? mode : "auto";
}

function browserStorageGet() {
    try {
        return window.localStorage.getItem(THEME_KEY);
    } catch {
        return null;
    }
}

function browserStorageSet(mode) {
    try {
        window.localStorage.setItem(THEME_KEY, mode);
    } catch {
        // private browsing - theme still applies for this page's lifetime
    }
}

function applyTheme() {
    const mode = storedMode();
    const dark = mode === "night" || (mode === "auto" && darkMedia.matches);
    document.documentElement.setAttribute(
        "data-bpro-theme",
        dark ? "dark" : "light"
    );
}

// Apply immediately at asset-load time (before the web client mounts) so
// there is no light flash, and track OS-level changes while in Auto.
applyTheme();
darkMedia.addEventListener("change", () => {
    if (storedMode() === "auto") {
        applyTheme();
    }
});

export class BproThemeSwitch extends Component {
    static template = "bpro_ui_prefs.ThemeSwitch";
    static props = {};

    setup() {
        this.state = useState({ mode: storedMode() });
    }

    get modes() {
        return [
            { id: "day", icon: "fa-sun-o", label: _t("Day") },
            { id: "night", icon: "fa-moon-o", label: _t("Night") },
            { id: "auto", icon: "fa-adjust", label: _t("Auto") },
        ];
    }

    get current() {
        return this.modes.find((m) => m.id === this.state.mode) || this.modes[2];
    }

    cycle() {
        const modes = this.modes;
        const idx = modes.findIndex((m) => m.id === this.state.mode);
        const next = modes[(idx + 1) % modes.length];
        this.state.mode = next.id;
        browserStorageSet(next.id);
        applyTheme();
    }
}

export class BproLangSwitch extends Component {
    static template = "bpro_ui_prefs.LangSwitch";
    static components = { Dropdown, DropdownItem };
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.state = useState({ langs: [] });
        this.currentLang = (user.context && user.context.lang) || "en_US";
        onWillStart(async () => {
            // [[code, name], ...] for installed/active languages only
            this.state.langs = await this.orm.call("res.lang", "get_installed", []);
        });
    }

    get currentCode() {
        return this.currentLang.split("_")[0].toUpperCase();
    }

    async setLang(code) {
        if (code === this.currentLang) {
            return;
        }
        // lang is one of res.users SELF_WRITEABLE_FIELDS - every internal
        // user may change it on their own record.
        await this.orm.write("res.users", [user.userId], { lang: code });
        window.location.reload();
    }
}

registry
    .category("systray")
    .add("bpro_ui_prefs.theme", { Component: BproThemeSwitch }, { sequence: 3 });
registry
    .category("systray")
    .add("bpro_ui_prefs.lang", { Component: BproLangSwitch }, { sequence: 4 });
