from odoo import fields, models, tools


class PayrollCostReport(models.Model):
    _name = "payroll.cost.report"
    _description = "Payroll Cost Report"
    _auto = False
    _rec_name = "payslip_id"
    _order = "date_to desc, employee_id"

    payslip_id = fields.Many2one("hr.payslip", string="Payslip", readonly=True)
    employee_id = fields.Many2one("hr.employee", string="Employee", readonly=True)
    contract_id = fields.Many2one("hr.contract", string="Contract", readonly=True)
    department_id = fields.Many2one("hr.department", string="Department", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True)
    date_from = fields.Date(string="Date From", readonly=True)
    date_to = fields.Date(string="Date To", readonly=True)

    project_id = fields.Many2one("account.analytic.account", string="Project", readonly=True)

    basic_salary = fields.Monetary(string="Basic Salary", currency_field="currency_id", readonly=True)
    allowances = fields.Monetary(string="Allowances", currency_field="currency_id", readonly=True)
    deductions = fields.Monetary(string="Deductions", currency_field="currency_id", readonly=True)
    net_salary = fields.Monetary(string="Net Salary", currency_field="currency_id", readonly=True)
    employer_cost = fields.Monetary(string="Employer Cost", currency_field="currency_id", readonly=True)
    analytic_amount = fields.Monetary(
        string="Analytic Distribution Amount",
        currency_field="currency_id",
        readonly=True,
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH payslip_amounts AS (
                    SELECT
                        hsl.slip_id,
                        SUM(CASE WHEN UPPER(hsl.code) = 'BASIC' THEN hsl.total ELSE 0 END) AS basic_salary,
                        SUM(CASE
                            WHEN hsl.total > 0 AND UPPER(hsl.code) NOT IN ('BASIC', 'NET')
                            THEN hsl.total
                            ELSE 0
                        END) AS allowances,
                        SUM(CASE WHEN hsl.total < 0 THEN ABS(hsl.total) ELSE 0 END) AS deductions,
                        SUM(CASE WHEN UPPER(hsl.code) = 'NET' THEN hsl.total ELSE 0 END) AS net_salary,
                        SUM(CASE
                            WHEN UPPER(src.code) IN ('EMPLOYER', 'COMP')
                            THEN hsl.total
                            ELSE 0
                        END)
                        + SUM(CASE
                            WHEN UPPER(hsl.code) = 'NET' THEN hsl.total ELSE 0 END) AS employer_cost
                    FROM hr_payslip_line hsl
                    LEFT JOIN hr_salary_rule_category src ON src.id = hsl.category_id
                    GROUP BY hsl.slip_id
                ),
                analytic_amounts AS (
                    SELECT
                        hp.id AS slip_id,
                        CASE
                            WHEN dist.key ~ '^[0-9]+$' THEN dist.key::int
                            ELSE NULL
                        END AS project_id,
                        SUM(aml.balance * (dist.value::numeric / 100.0)) AS analytic_amount
                    FROM hr_payslip hp
                    JOIN account_move am ON am.id = hp.move_id
                    JOIN account_move_line aml ON aml.move_id = am.id
                    CROSS JOIN LATERAL jsonb_each_text(
                        COALESCE(aml.analytic_distribution, jsonb_build_object('0', '100'))
                    ) AS dist(key, value)
                    GROUP BY hp.id, project_id
                )
                SELECT
                    ROW_NUMBER() OVER (
                        ORDER BY hp.date_to DESC, hp.employee_id, COALESCE(aa.project_id, 0)
                    ) AS id,
                    hp.id AS payslip_id,
                    hp.employee_id,
                    hp.contract_id,
                    he.department_id,
                    hp.company_id,
                    rc.currency_id,
                    hp.date_from,
                    hp.date_to,
                    aa.project_id,
                    COALESCE(pa.basic_salary, 0.0) AS basic_salary,
                    COALESCE(pa.allowances, 0.0) AS allowances,
                    COALESCE(pa.deductions, 0.0) AS deductions,
                    COALESCE(pa.net_salary, 0.0) AS net_salary,
                    COALESCE(pa.employer_cost, 0.0) AS employer_cost,
                    COALESCE(aa.analytic_amount, 0.0) AS analytic_amount
                FROM hr_payslip hp
                JOIN hr_employee he ON he.id = hp.employee_id
                JOIN res_company rc ON rc.id = hp.company_id
                LEFT JOIN payslip_amounts pa ON pa.slip_id = hp.id
                LEFT JOIN analytic_amounts aa ON aa.slip_id = hp.id
                WHERE hp.state IN ('done', 'paid')
            )
            """
        )

        self.env.cr.execute(
            """
            CREATE INDEX IF NOT EXISTS hr_payslip_report_company_date_employee_idx
            ON hr_payslip (company_id, date_to, employee_id)
            """
        )
        self.env.cr.execute(
            """
            CREATE INDEX IF NOT EXISTS hr_payslip_report_move_idx
            ON hr_payslip (move_id)
            """
        )
        self.env.cr.execute(
            """
            CREATE INDEX IF NOT EXISTS hr_payslip_line_report_slip_code_cat_idx
            ON hr_payslip_line (slip_id, code, category_id)
            """
        )
        self.env.cr.execute(
            """
            CREATE INDEX IF NOT EXISTS account_move_line_report_move_idx
            ON account_move_line (move_id)
            """
        )
