from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMenuGroupAssignment(TransactionCase):
    """The post_init_hook's own assignments are exercised implicitly by
    every other bpro_* module's test suite (bpro_navigation is a
    dependency-free add-on layered on top of whatever's installed), so
    these tests target the reusable pieces instead: the five seeded
    groups exist and are well-formed, and a fresh group with no menus
    assigned behaves correctly as a citizen of the model (no fallback
    dependent on the hook having run for any specific app)."""

    def test_five_groups_are_seeded_in_order(self):
        groups = self.env["bpro.menu.group"].search([])
        self.assertEqual(
            groups.mapped("name"),
            ["Sales", "Production", "Accounts", "HR", "General"],
        )

    def test_exactly_one_fallback_group(self):
        fallback = self.env["bpro.menu.group"].search([("is_fallback", "=", True)])
        self.assertEqual(len(fallback), 1)
        self.assertEqual(fallback.name, "General")

    def test_assigning_a_menu_shows_up_on_the_group(self):
        group = self.env["bpro.menu.group"].create({"name": "Test Group"})
        menu = self.env["ir.ui.menu"].create({"name": "Test Root Menu"})
        menu.bpro_group_id = group.id
        self.assertIn(menu, group.menu_ids)

    def test_seeded_groups_are_ordered_by_sequence(self):
        groups = self.env["bpro.menu.group"].search([])
        sequences = groups.mapped("sequence")
        self.assertEqual(sequences, sorted(sequences))
