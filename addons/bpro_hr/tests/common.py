from odoo.tests.common import TransactionCase


class HrTestCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.env["account.chart.template"].try_loading(
            "generic_coa", cls.company, install_demo=False
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "HR Test Expense Product",
                "list_price": 100.0,
                "can_be_expensed": True,
            }
        )
        cls.employee = cls.env["hr.employee"].create({"name": "HR Test Employee"})

    def _sheet(self, amount):
        return self.env["hr.expense.sheet"].create(
            {
                "name": "Test Expense Report",
                "employee_id": self.employee.id,
                "expense_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Test Expense",
                            "employee_id": self.employee.id,
                            "product_id": self.product.id,
                            "total_amount": amount,
                        },
                    )
                ],
            }
        )
