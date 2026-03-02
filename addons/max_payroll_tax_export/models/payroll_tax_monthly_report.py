from odoo import fields, models, tools

from .tax_template import TAX_EXPORT_HEADERS


class PayrollTaxMonthlyReport(models.Model):
    _name = 'payroll.tax.monthly.report'
    _description = 'Payroll Tax Monthly Report'
    _auto = False
    _rec_name = 'employee_id'
    _order = 'year desc, month desc, employee_id'

    payslip_id = fields.Many2one('hr.payslip', string='قسيمة الراتب', readonly=True)
    employee_id = fields.Many2one('hr.employee', string='الموظف', readonly=True)
    contract_id = fields.Many2one('hr.contract', string='العقد', readonly=True)
    company_id = fields.Many2one('res.company', string='الشركة', readonly=True)
    month = fields.Integer(string='الشهر', readonly=True)
    year = fields.Integer(string='السنة', readonly=True)

    national_id = fields.Char(string='الرقم القومي', readonly=True)
    employee_code = fields.Char(string='كود الموظف', readonly=True)
    employee_name = fields.Char(string='اسم الموظف', readonly=True)
    basic_salary = fields.Float(string='المرتب الأساسي', readonly=True)
    taxable_allowances = fields.Float(string='إضافات وبدلات اخرى خاضعة', readonly=True)
    deductions = fields.Float(string='استقطاعات', readonly=True)
    employee_social_insurance = fields.Float(string='حصة العامل فى التأمينات', readonly=True)
    employer_social_insurance = fields.Float(string='حصة الشركة في التأمينات', readonly=True)
    tax_amount = fields.Float(string='الضريبة المحتسبة عن الفترة', readonly=True)
    net_salary = fields.Float(string='صافي الأجر النهائي', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH line_agg AS (
                    SELECT
                        pl.slip_id,
                        SUM(CASE WHEN UPPER(pl.code) = 'BASIC' THEN pl.total ELSE 0 END) AS basic_salary,
                        SUM(CASE WHEN UPPER(pl.code) = 'NET' THEN pl.total ELSE 0 END) AS net_salary,
                        SUM(CASE WHEN UPPER(pl.code) = 'TAX' THEN ABS(pl.total) ELSE 0 END) AS tax_amount,
                        SUM(
                            CASE
                                WHEN UPPER(pl.code) ~ '(SI_EMP|SOC_EMP|EMP_SI|EMPLOYEE_INSURANCE|INS_EMP)'
                                THEN ABS(pl.total)
                                ELSE 0
                            END
                        ) AS employee_social_insurance,
                        SUM(
                            CASE
                                WHEN UPPER(pl.code) ~ '(SI_COMP|SOC_COMP|ER_SI|EMPLOYER_INSURANCE|INS_COMP)'
                                THEN ABS(pl.total)
                                ELSE 0
                            END
                        ) AS employer_social_insurance,
                        SUM(
                            CASE
                                WHEN pl.total > 0
                                    AND UPPER(pl.code) NOT IN ('BASIC', 'NET', 'TAX')
                                    AND UPPER(pl.code) !~ '(SI_COMP|SOC_COMP|ER_SI|EMPLOYER_INSURANCE|INS_COMP)'
                                THEN pl.total
                                ELSE 0
                            END
                        ) AS taxable_allowances,
                        SUM(
                            CASE
                                WHEN pl.total < 0
                                    AND UPPER(pl.code) NOT IN ('TAX')
                                    AND UPPER(pl.code) !~ '(SI_EMP|SOC_EMP|EMP_SI|EMPLOYEE_INSURANCE|INS_EMP)'
                                THEN ABS(pl.total)
                                ELSE 0
                            END
                        ) AS deductions
                    FROM hr_payslip_line pl
                    GROUP BY pl.slip_id
                )
                SELECT
                    ROW_NUMBER() OVER (ORDER BY ps.date_to DESC, ps.employee_id, ps.id) AS id,
                    ps.id AS payslip_id,
                    ps.employee_id,
                    ps.contract_id,
                    ps.company_id,
                    EXTRACT(MONTH FROM ps.date_to)::integer AS month,
                    EXTRACT(YEAR FROM ps.date_to)::integer AS year,
                    COALESCE(emp.identification_id, '') AS national_id,
                    COALESCE(emp.barcode, emp.registration_number, emp.work_email, '') AS employee_code,
                    COALESCE(emp.name, '') AS employee_name,
                    COALESCE(la.basic_salary, 0.0) AS basic_salary,
                    COALESCE(la.taxable_allowances, 0.0) AS taxable_allowances,
                    COALESCE(la.deductions, 0.0) AS deductions,
                    COALESCE(la.employee_social_insurance, 0.0) AS employee_social_insurance,
                    COALESCE(la.employer_social_insurance, 0.0) AS employer_social_insurance,
                    COALESCE(la.tax_amount, 0.0) AS tax_amount,
                    COALESCE(la.net_salary, 0.0) AS net_salary
                FROM hr_payslip ps
                JOIN hr_employee emp ON emp.id = ps.employee_id
                LEFT JOIN line_agg la ON la.slip_id = ps.id
                WHERE ps.state IN ('done', 'paid')
            )
            """
        )

        self.env.cr.execute(
            """
            CREATE INDEX IF NOT EXISTS hr_payslip_tax_report_company_period_employee_idx
            ON hr_payslip (company_id, date_to, employee_id)
            """
        )
        self.env.cr.execute(
            """
            CREATE INDEX IF NOT EXISTS hr_payslip_line_tax_report_slip_code_idx
            ON hr_payslip_line (slip_id, code)
            """
        )


_EXTRA_HEADERS = TAX_EXPORT_HEADERS[12:]
for _index, _header in enumerate(_EXTRA_HEADERS, start=13):
    setattr(
        PayrollTaxMonthlyReport,
        f'col_{_index:03d}',
        fields.Char(string=_header, readonly=True),
    )
