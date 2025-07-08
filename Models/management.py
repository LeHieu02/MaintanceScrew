from odoo import api, fields, models, tools

class managementFactory(models.Model):
    _name = 'management.factory.information'
    _description = 'Management factory'



class managementMaintenance(models.Model):
    _name = 'management.maintenance.information'
    _description = 'Management maintenance'