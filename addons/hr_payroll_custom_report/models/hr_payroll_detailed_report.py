from odoo import fields, models, tools


class HrPayrollDetailedReport(models.Model):
    _name = "hr.payroll.detailed.report"
    _description = "Payroll Detailed Report"
    _auto = False
    _rec_name = "employee_id"
    _order = "employee_id, date_from desc"

    employee_id = fields.Many2one("hr.employee", string="Employee", readonly=True)
    contract_id = fields.Many2one("hr.contract", string="Contract", readonly=True)
    payslip_id = fields.Many2one("hr.payslip", string="Payslip", readonly=True)

    employee_code = fields.Char(string="Employee Code", readonly=True)
    name = fields.Char(string="Employee Name", readonly=True)
    name_ar = fields.Char(string="Employee Name (Arabic)", readonly=True)
    identification_id = fields.Char(string="Identification No.", readonly=True)
    department_id = fields.Many2one("hr.department", string="Department", readonly=True)
    job_id = fields.Many2one("hr.job", string="Job Position", readonly=True)
    hire_date = fields.Date(string="Hire Date", readonly=True)
    end_date = fields.Date(string="End Date", readonly=True)
    analytic_account_id = fields.Integer(string="Analytic Account ID", readonly=True)

    wage = fields.Float(string="Contract Wage", readonly=True)
    transportation_allowance = fields.Float(string="Transportation Allowance", readonly=True)

    basic = fields.Float(string="BASIC", readonly=True)
    other_allowances = fields.Float(string="Other Allowances", readonly=True)
    gross = fields.Float(string="GROSS", readonly=True)
    net = fields.Float(string="NET", readonly=True)

    date_from = fields.Date(string="Period Start", readonly=True)
    date_to = fields.Date(string="Period End", readonly=True)
    period_month = fields.Integer(string="Month", readonly=True)
    period_year = fields.Integer(string="Year", readonly=True)

    def _get_analytic_account_select(self):
        self.env.cr.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'hr_contract' AND column_name = 'analytic_account_id'
            LIMIT 1
            """
        )
        return "ct.analytic_account_id" if self.env.cr.fetchone() else "NULL::integer"

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        analytic_account_select = self._get_analytic_account_select()
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH line_agg AS (
                    SELECT
                        pl.slip_id,
                        SUM(CASE WHEN UPPER(pl.code) = 'BASIC' THEN pl.total ELSE 0 END) AS basic,
                        SUM(CASE WHEN UPPER(pl.code) = 'OA' THEN pl.total ELSE 0 END) AS other_allowances,
                        SUM(CASE WHEN UPPER(pl.code) = 'GROSS' THEN pl.total ELSE 0 END) AS gross,
                        SUM(CASE WHEN UPPER(pl.code) = 'NET' THEN pl.total ELSE 0 END) AS net,
                        SUM(CASE WHEN UPPER(pl.code) IN ('TRANSPORT', 'TRANSPORTATION', 'TRANS') THEN pl.total ELSE 0 END)
                            AS transportation_allowance
                    FROM hr_payslip_line pl
                    GROUP BY pl.slip_id
                )
                SELECT
                    ps.id AS id,
                    ps.id AS payslip_id,
                    ps.employee_id,
                    ps.contract_id,
                    COALESCE(emp.barcode, emp.identification_id) AS employee_code,
                    emp.name,
                    emp.name_ar,
                    emp.identification_id,
                    emp.department_id,
                    emp.job_id,
                    ct.date_start AS hire_date,
                    ct.date_end AS end_date,
                    {analytic_account_select} AS analytic_account_id,
                    ct.wage,
                    COALESCE(la.transportation_allowance, 0.0) AS transportation_allowance,
                    COALESCE(la.basic, 0.0) AS basic,
                    COALESCE(la.other_allowances, 0.0) AS other_allowances,
                    COALESCE(la.gross, 0.0) AS gross,
                    COALESCE(la.net, 0.0) AS net,
                    ps.date_from,
                    ps.date_to,
                    EXTRACT(MONTH FROM ps.date_to)::integer AS period_month,
                    EXTRACT(YEAR FROM ps.date_to)::integer AS period_year
                FROM hr_payslip ps
                JOIN hr_employee emp ON emp.id = ps.employee_id
                LEFT JOIN hr_contract ct ON ct.id = ps.contract_id
                LEFT JOIN line_agg la ON la.slip_id = ps.id
                WHERE ps.state IN ('done', 'paid')
            )
            """
        )
