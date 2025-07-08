
from odoo import api, fields, models, tools
from odoo.exceptions import UserError

class wareHouseInformation(models.Model):
    _name = 'warehouse.information'
    _description = 'Warehouse information'

    name = fields.Char(string = "Warehouse Code")
    factory_id = fields.Many2one("factory.information", string = "Factory")
    phone = fields.Char(string = "Phone")
    email = fields.Char(string = "Email")

class StoringInformation(models.Model):
    _name = 'storing.information'
    _description = 'Storing'

    component_id = fields.Many2one("component.information", string = "Component")
    warehouse_id = fields.Many2one ("warehouse.information", string = "Warehouse")
    amount = fields.Integer (string = "Amount",default=15)
    unit = fields.Selection ([('piece','Piece')], string = "Unit",default = 'piece')
    reorder_min = fields.Integer(string = "Reorder min")
    note = fields.Text (string = "Note")

class ImportHistoryInformation(models.Model):
    _name = 'import.information'
    _description = 'Import history'

    import_code = fields.Char(string = "Import code")
    warehouse_id = fields.Many2one("warehouse.information",string = "Warehouse")
    import_date = fields.Date (string = "Import date")
    status = fields.Selection([('new','New'),('confirmed','Confirmed'),('done','Done'),('cancel','Cancel')], string = "Status",default = "new")
    user_created = fields.Char(string="Created by")
    user_confirmed = fields.Char(string="Confirmed by")
    user_done = fields.Char(string="Done by")
    user_cancel = fields.Char(string="Cancelled by")
    supplier = fields.Char (string = "Supplier")
    description = fields.Text (string = "Description")
    note = fields.Text (string = "Note")
    import_line_ids = fields.One2many('import.line.information', 'name', string="Import Lines")
    def action_im_new(self):
        for rec in self:
            rec.write({
                'status': 'new',
                'user_created': self.env.user.login.split('@')[0]
            })

    def action_im_confirmed(self):
        for rec in self:
            rec.write({
                'status': 'confirmed',
                'user_confirmed': self.env.user.login.split('@')[0]
            })

    def action_im_done(self):
        for rec in self:
            rec.write({
                'status': 'done',
                'user_done': self.env.user.login.split('@')[0]
            })

    def action_im_cancel(self):
        for rec in self:
            rec.write({
                'status': 'cancel',
                'user_cancel': self.env.user.login.split('@')[0]
            })

    @api.model
    def write(self, vals):
        result = super(ImportHistoryInformation, self).write(vals)

        if 'status' in vals:
            for record in self:
                record.import_line_ids.write({'status': vals['status']})
        if 'warehouse_id' in vals:
            for record in self:
                if record.import_line_ids:
                    record.import_line_ids.write({'warehouse_id': vals['warehouse_id']})
        return result

class ImportLineInformation(models.Model):
    _name = 'import.line.information'
    _description = 'Import history line'

    name = fields.Many2one("import.information",string = "ID")
    warehouse_id = fields.Many2one("warehouse.information", string="Warehouse")
    component = fields.Many2one("component.information", string = "Component")
    status = fields.Selection([('new','New'),('waiting', 'Waiting'),('confirmed','Confirmed'),('done','Done'),('cancel','Cancel')], string = "Status")
    import_amount = fields.Integer(string = "Import amount")

    @api.model
    def write(self, vals):
        result = super(ImportLineInformation, self).write(vals)
        if 'status' in vals and vals['status'] == 'done':
            for record in self:
                storing_record = self.env['storing.information'].search([
                    ('component_id', '=', record.component.id),
                    ('warehouse_id', '=', record.warehouse_id.id)
                ], limit=1)

                if storing_record:
                    storing_record.sudo().write({'amount': storing_record.amount + record.import_amount})
        return result


class ExportHistoryInformation(models.Model):
    _name = 'export.information'
    _description = 'Export history'

    export_code = fields.Char(string="Export code")
    warehouse_id = fields.Many2one("warehouse.information", string="Warehouse")
    export_date = fields.Date(string="Export date")
    status = fields.Selection([('new', 'New'),('waiting', 'Waiting'), ('confirmed', 'Confirmed'), ('done', 'Done'), ('cancel', 'Cancel')],
                              string="Status",default = "new")
    user_created = fields.Char(string="Created by")
    user_confirmed = fields.Char(string="Confirmed by")
    user_done = fields.Char(string="Done by")
    user_cancel = fields.Char(string="Cancelled by")
    supplier = fields.Char(string="Supplier")
    description = fields.Text(string="Description")
    note = fields.Text(string="Note")
    export_line_ids = fields.One2many('export.line.information', 'name', string="Export Lines")
    maintenance_id = fields.Many2one('maintenance.information', string='Maintenance')
    deny_reason = fields.Text(string="Deny Reason")

    def action_ex_new(self):
        for rec in self:
            rec.write({
                'status': 'new',
                'user_created': self.env.user.login.split('@')[0]
            })

    def action_ex_waiting(self):
        for rec in self:
            rec.write({
                'status': 'waiting',
                'user_created': self.env.user.login.split('@')[0]
            })
            self.env['notification.history'].notify_export_status(rec, 'to_leader')

    def action_ex_confirmed(self):
        for rec in self:
            rec.write({
                'status': 'confirmed',
                'user_confirmed': self.env.user.login.split('@')[0]
            })
            self.env['notification.history'].notify_export_status(rec, 'to_warehousestaff')

    def action_ex_done(self):
        for rec in self:
            rec.write({
                'status': 'done',
                'user_done': self.env.user.login.split('@')[0]
            })

    def action_ex_cancel(self):
        for rec in self:
            rec.write({
                'status': 'cancel',
                'user_cancel': self.env.user.login.split('@')[0]
            })

    def action_done(self):
        self.write({'status': 'done'})
        for line in self.export_line_ids:
            if line.maintenance_id:
                line.maintenance_id.message_post(body="Export completed for component: %s" % line.component.name)

    def action_deny_export_popup(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Deny Export',
            'res_model': 'export.deny.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_export_id': self.id,
            }
        }

    @api.model
    def write(self, vals):
        result = super(ExportHistoryInformation, self).write(vals)

        if 'status' in vals:
            for record in self:
                record.export_line_ids.write({'status': vals['status']})

                if vals['status'] == 'done':
                    for export_line in record.export_line_ids:
                        replaced_component = record.maintenance_id.replaced_component_ids.filtered(
                            lambda comp: comp.id == export_line.component.id
                        )
                        if replaced_component:
                            replaced_component.receive = export_line.export_amount

        if 'warehouse_id' in vals:
            for record in self:
                if record.export_line_ids:
                    record.export_line_ids.write({'warehouse_id': vals['warehouse_id']})

        return result


class ExportLineInformation(models.Model):
    _name = 'export.line.information'
    _description = 'Export history line'

    name = fields.Many2one("export.information", string="ID")
    warehouse_id = fields.Many2one("warehouse.information", string="Warehouse")
    maintenance_id = fields.Many2one('maintenance.information', string="Maintenance")
    component = fields.Many2one("component.information", string="Component")
    status = fields.Selection([('new', 'New'),('waiting', 'Waiting'), ('confirmed', 'Confirmed'), ('done', 'Done'), ('cancel', 'Cancel')],
                                  string="Status")
    export_amount = fields.Integer(string="Export amount")
    export_requested = fields.Integer(string= "Export requested")

    @api.model
    def write(self, vals):
        result = super(ExportLineInformation, self).write(vals)
        if 'status' in vals and vals['status'] == 'done':
            for record in self:
                replacing_records = self.env['replace.information'].search(
                    [('component', '=', record.component.id)])
                for replacing in replacing_records:
                    replacing.write({'receive': record.export_amount})

                storing_record = self.env['storing.information'].search([
                    ('component_id', '=', record.component.id),
                    ('warehouse_id', '=', record.warehouse_id.id)
                ], limit=1)

                if storing_record:
                    if storing_record.amount < record.export_amount:
                        raise UserError(
                            f"Not enough stock for component {record.component.name}! "
                            f"Available: {storing_record.amount}, Requested: {record.export_amount}"
                        )
                    # Giảm số lượng trong storing
                    storing_record.sudo().write({'amount': storing_record.amount - record.export_amount})
                else:
                    raise UserError(
                        f"No stock record found for component {record.component.name} in warehouse {record.warehouse_id.name}!"
                    )
        return result
class ExportDenyWizard(models.TransientModel):
    _name = 'export.deny.wizard'
    _description = 'Export Deny Wizard'

    export_id = fields.Many2one('export.information', string='Export Record')
    deny_reason = fields.Text(string='Deny Reason', required=True)

    def action_confirm_deny(self):
        if self.export_id:
            self.export_id.write({
                'status': 'new',
                'deny_reason': self.deny_reason
            })
            self.env['notification.history'].notify_export_status(
                self.export_id,
                'to_warehousestaff',
                message=f"Export has been denied. Reason: {self.deny_reason}"
            )