{
    'name': 'Maintenance Screw',
    'version': '1.0',
    'summary': 'Module to manage maintenance',
    'description': """
        This module helps maintenance and inventory in garment factories.
    """,
    'author': 'Le Trung Hieu',
    'depends': ['base','mail'],
    'data': [
    "security/security.xml",
    "security/ir.model.access.csv",
    "views/model_view.xml",
    "views/maintenance_view.xml",
    "views/employee_view.xml",
    "views/factory_view.xml",
    "views/warehouse_view.xml",
    "views/management_view.xml",
    "views/error_view.xml",
    "views/import_partscan_wizard_view.xml",
    "views/import_partlist_wizard_view.xml",
    "views/notification_view.xml",
    "views/fcm_token_menu.xml"
    ],
    'installable': True,
    'application': True,
}
