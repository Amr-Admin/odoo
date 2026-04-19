{
    "name": "HR Payroll Custom Detailed Report",
    "version": "18.0.1.0.0",
    "summary": "Detailed payroll reporting by employee, contract, and payslip lines",
    "category": "Human Resources/Payroll",
    "license": "LGPL-3",
    "depends": [
        "hr",
        "hr_contract",
        "hr_payroll",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_payroll_detailed_report_views.xml",
    ],
    "installable": True,
    "application": False,
}
