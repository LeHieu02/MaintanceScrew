from odoo import api, fields, models, tools

class factoryInformation(models.Model):
    _name = 'factory.information'
    _description = 'factory information'

    id_name = fields.Char(string="ID Factory")
    name = fields.Char(string="Name")
    email = fields.Char(string="Email")
    phone = fields.Char(string="Phone")
    location = fields.Char(string="Location")
    site_area = fields.Integer(string = "Site Area")
    numberOfEmployee = fields.Integer(string="Number of employee")
    description = fields.Char(string = "Description")

class factoryMachine(models.Model):
    _name = 'machine.information'
    _description = 'machine'


    name = fields.Char(string="Machine Code")
    machine_serial = fields.Char(string="Serial machine")
    model_id = fields.Many2one("detail.information",string="Machine Model ID")
    factory_id = fields.Many2one("factory.information", string = "Name of Factory")
    date_added = fields.Date(string = "Date added")
    QR_code = fields.Binary(string = "QR code")
    status=fields.Selection([('active','Active'),('inactive','Inactive')],compute='_compute_status',default = "active", store=True)
    schedule_maintenance = fields.Date(string = "Schedule maintenance date")
    note = fields.Text(string = "Note")
    maintenance_id = fields.One2many('maintenance.information', 'machine', string='Maintenance Records')

    @api.depends('maintenance_id.status')
    def _compute_status(self):
        for record in self:
            if not record.maintenance_id:
                record.status = 'active'
            else:
                non_complete_maintenance = record.maintenance_id.filtered(
                    lambda m: m.status != 'complete'
                )
                record.status = 'inactive' if non_complete_maintenance else 'active'

    def action_open_maintenance_tree(self):
        """Mở tree view của các phiếu bảo trì liên quan đến máy"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Maintenance Records',
            'view_mode': 'tree,form',
            'res_model': 'maintenance.information',
            'domain': [('machine', '=', self.id)],
            'context': {'default_machine': self.id},
            'target': 'current',
        }
class factoryComponent(models.Model):
    _name = 'component.information'
    _description = 'component'

    name = fields.Char(string="Component Code")
    componentSerial = fields.Char(string="Component Serial")
    model_ids = fields.Many2many("detail.information","model_component_rel","component_id","model_id",string = "Model")
    manufacturer = fields.Char(string="Manufacturer")
    description = fields.Text(string="Description")

class errorInformation(models.Model):
    _name = 'error.information'
    _description = 'Error'

    machine_id = fields.Many2one("machine.information")
    error_code = fields.Char(string = "Error code")
    description = fields.Char(string = "Description")
    checked = fields.Char (string = "Checked items")