from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    name_ar = fields.Char(string="Arabic Name", help="Arabic display name used in payroll reports.")
