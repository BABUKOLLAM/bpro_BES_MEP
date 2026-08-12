/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";
import { useService } from "@web/core/utils/hooks";
import { onWillStart } from "@odoo/owl";

patch(NavBar.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.bproMenuGroups = [];
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
            this.bproMenuGroups.map((g) => [g.id, { id: g.id, name: g.name, apps: [] }])
        );
        for (const app of apps) {
            const groupId = menuIdToGroupId[app.id] ?? fallback.id;
            buckets.get(groupId).apps.push(app);
        }
        return [...buckets.values()].filter((bucket) => bucket.apps.length);
    },
});
