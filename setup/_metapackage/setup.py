import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo-addons-ecosoft-odoo-budgeting",
    description="Meta package for ecosoft-odoo-budgeting Odoo addons",
    version=version,
    install_requires=[
        'odoo-addon-budget_activity>=16.0dev,<16.1dev',
        'odoo-addon-budget_activity_expense>=16.0dev,<16.1dev',
        'odoo-addon-budget_activity_purchase>=16.0dev,<16.1dev',
        'odoo-addon-budget_activity_purchase_request>=16.0dev,<16.1dev',
        'odoo-addon-budget_control>=16.0dev,<16.1dev',
        'odoo-addon-budget_control_advance_clearing>=16.0dev,<16.1dev',
        'odoo-addon-budget_control_expense>=16.0dev,<16.1dev',
        'odoo-addon-budget_control_purchase>=16.0dev,<16.1dev',
        'odoo-addon-budget_control_purchase_request>=16.0dev,<16.1dev',
        'odoo-addon-budget_plan>=16.0dev,<16.1dev',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 16.0',
    ]
)
