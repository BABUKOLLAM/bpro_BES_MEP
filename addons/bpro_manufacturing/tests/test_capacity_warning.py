from datetime import datetime, timedelta

from .common import MfgTestCommon


class TestCapacityWarning(MfgTestCommon):
    def test_no_warning_when_not_overlapping(self):
        mo1 = self._mo()
        mo1.button_plan()
        wo1 = mo1.workorder_ids

        mo2 = self._mo()
        mo2.button_plan()
        wo2 = mo2.workorder_ids

        # button_plan already avoided overlapping them (default_capacity=1)
        self.assertFalse(wo1.bpro_capacity_warning)
        self.assertFalse(wo2.bpro_capacity_warning)

    def test_warning_when_manually_forced_to_overlap(self):
        mo1 = self._mo()
        mo1.button_plan()
        wo1 = mo1.workorder_ids

        mo2 = self._mo()
        mo2.button_plan()
        wo2 = mo2.workorder_ids

        # force wo2 onto exactly the same slot as wo1, simulating a manual
        # drag that the automated scheduler would never produce itself
        wo2.write(
            {
                "date_start": wo1.date_start,
                "date_finished": wo1.date_finished,
            }
        )
        self.assertTrue(
            wo2.bpro_capacity_warning,
            "overlapping a fully-booked work center must surface a warning",
        )
