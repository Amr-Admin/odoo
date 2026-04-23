{
    'name': 'MAX Payroll Tax Export',
    'version': '18.0.1.0.0',
    'summary': 'Monthly Egyptian payroll tax portal export (XLSX)',
    'category': 'Human Resources/Payroll',
    'author': 'MAX',
    'license': 'LGPL-3',
    'depends': ['hr_payroll', 'mail'],
    'data': [
        'security/payroll_tax_security.xml',
        'security/ir.model.access.csv',
        'views/payroll_tax_monthly_report_views.xml',
        'views/payroll_tax_export_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
}
