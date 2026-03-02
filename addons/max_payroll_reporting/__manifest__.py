{
    "name": "MAX Payroll Reporting",
    "version": "18.0.1.0.0",
    "summary": "Advanced payroll cost analytics with SQL view",
    "category": "Human Resources/Payroll",
    "author": "MAX",
    "license": "OEEL-1",
    "depends": [
        "hr_payroll",
        "hr_contract",
        "account",
        "analytic",
    ],
    "data": [
        "security/payroll_cost_report_security.xml",
        "security/ir.model.access.csv",
        "views/payroll_cost_report_views.xml",
    ],
    "installable": True,
    "application": False,
}
