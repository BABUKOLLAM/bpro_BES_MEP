/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";
import { useService } from "@web/core/utils/hooks";
import { onWillStart, useState } from "@odoo/owl";

patch(NavBar.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.bproMenuGroups = [];
        // null = "no explicit choice yet": the group holding the current
        // app (or the first group) renders expanded until the user picks.
        this.bproNavState = useState({ expandedGroupId: null });
        onWillStart(async () => {
            this.bproMenuGroups = await this.orm.searchRead(
                "bpro.menu.group",
                [],
                ["name", "sequence", "is_fallback", "menu_ids"]
            );
        });
    },

    /**
     * Buckets the flat app list the native template already computes
     * (menuService.getApps()) into the bpro.menu.group sections fetched
     * above. One ORM call per NavBar mount, not per render - this runs
     * against a handful of rows so no caching layer beyond that.
     */
    getGroupedApps(apps) {
        if (!this.bproMenuGroups.length) {
            return [{ id: 0, name: false, apps }];
        }
        const menuIdToGroupId = {};
        for (const group of this.bproMenuGroups) {
            for (const menuId of group.menu_ids) {
                menuIdToGroupId[menuId] = group.id;
            }
        }
        const fallback =
            this.bproMenuGroups.find((g) => g.is_fallback) ||
            this.bproMenuGroups[this.bproMenuGroups.length - 1];
        const buckets = new Map(
            this.bproMenuGroups.map((g) => [
                g.id,
                // The fallback group ("General") renders as top-level
                // items rather than a collapsible submenu - its contents
                // (dashboard, settings, discuss...) are cross-functional
                // and deserve one-click access, not a second click.
                { id: g.id, name: g.name, isFallback: g.id === fallback.id, apps: [] },
            ])
        );
        for (const app of apps) {
            const groupId = menuIdToGroupId[app.id] ?? fallback.id;
            buckets.get(groupId).apps.push(app);
        }
        return [...buckets.values()].filter((bucket) => bucket.apps.length);
    },

    /**
     * Single-open accordion: only one group's submenu is expanded at a
     * time. Before the user makes an explicit choice, default to the
     * group containing the app they're currently working in, so opening
     * the switcher always starts from "where am I".
     */
    isBproGroupExpanded(group, groupedApps) {
        if (group.isFallback) {
            return true; // top-level items, never collapsed
        }
        if (this.bproNavState.expandedGroupId !== null) {
            return this.bproNavState.expandedGroupId === group.id;
        }
        const currentApp = this.menuService.getCurrentApp();
        const currentGroup = currentApp
            ? groupedApps.find((g) => g.apps.some((a) => a.id === currentApp.id))
            : null;
        const defaultGroup =
            currentGroup && !currentGroup.isFallback
                ? currentGroup
                : groupedApps.find((g) => !g.isFallback);
        return defaultGroup?.id === group.id;
    },

    toggleBproGroup(group, groupedApps, ev) {
        // The header lives inside the Dropdown's portal - a plain click
        // must toggle the submenu, never bubble into item-selection
        // handling that would close the whole apps menu.
        ev.stopPropagation();
        this.bproNavState.expandedGroupId = this.isBproGroupExpanded(group, groupedApps)
            ? 0 // 0 matches no group id -> everything collapsed
            : group.id;
    },
});
