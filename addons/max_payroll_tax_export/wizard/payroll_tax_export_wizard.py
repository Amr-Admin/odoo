import base64
from io import BytesIO

from odoo import _, fields, models
from odoo.exceptions import UserError

from ..models.tax_template import TAX_EXPORT_HEADERS


class PayrollTaxExportWizard(models.TransientModel):
    _name = 'payroll.tax.export.wizard'
    _description = 'Payroll Tax Export Wizard'

    month = fields.Selection(
        [(str(i), str(i)) for i in range(1, 13)],
        string='Month',
        required=True,
        default=lambda self: str(fields.Date.today().month),
    )
    year = fields.Integer(string='Year', required=True, default=lambda self: fields.Date.today().year)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    file_data = fields.Binary(string='File', readonly=True)
    file_name = fields.Char(string='File Name', readonly=True)

    def action_export(self):
        self.ensure_one()
        report_model = self.env['payroll.tax.monthly.report']
        records = report_model.search([
            ('month', '=', int(self.month)),
            ('year', '=', self.year),
            ('company_id', '=', self.company_id.id),
        ], order='employee_name, id')

        if not records:
            raise UserError(_('No payroll data found for the selected period.'))

        output = BytesIO()
        import xlsxwriter

        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Payroll Tax Export')
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
        text_format = workbook.add_format({'align': 'right', 'border': 1})
        num_format = workbook.add_format({'align': 'right', 'border': 1, 'num_format': '#,##0.00'})

        for col, header in enumerate(TAX_EXPORT_HEADERS):
            sheet.write(0, col, header, header_format)
            sheet.set_column(col, col, 20)

        for row_idx, rec in enumerate(records, start=1):
            values = [
                rec.national_id or '',
                rec.employee_code or '',
                rec.employee_name or '',
                rec.month,
                rec.year,
                rec.basic_salary,
                rec.taxable_allowances,
                rec.deductions,
                rec.employee_social_insurance,
                rec.employer_social_insurance,
                rec.tax_amount,
                rec.net_salary,
            ]
            values.extend([''] * (len(TAX_EXPORT_HEADERS) - len(values)))

            for col_idx, value in enumerate(values):
                if isinstance(value, (int, float)) and col_idx >= 5:
                    sheet.write_number(row_idx, col_idx, value, num_format)
                else:
                    sheet.write(row_idx, col_idx, value, text_format)

        workbook.close()
        output.seek(0)

        filename = f'payroll_tax_export_{self.year}_{self.month}_{self.company_id.id}.xlsx'
        self.write({
            'file_data': base64.b64encode(output.read()),
            'file_name': filename,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
