from odoo import models, fields,api
from odoo.exceptions import UserError


class maintenance(models.Model):
    _name = 'maintenance.information'
    _description = 'maintenance information'
    _inherit = ['mail.thread']

    name = fields.Char(string = "Maintenance ID")
    type =  fields.Selection([
        ('daily_check', 'Daily check'),('period_check','Period check')
    ], string='Type', default='daily_check', tracking=True)
    datetime_start=fields.Datetime(string = "Datetime Start")
    datetime_finish = fields.Datetime(string="Datetime Finish")
    work_time = fields.Float(string = "Work time")
    user_created = fields.Char(string="Created by")
    user_confirmed = fields.Char(string="Confirmed by")
    user_done = fields.Char(string="Done by")
    user_cancel = fields.Char(string="Cancelled by")
    status = fields.Selection([
        ('processing', 'Processing'),
        ('waiting', 'Waiting'),
        ('replacing', 'Replacing'),
        ('done', 'Done'),
        ('complete', 'Complete'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='processing', tracking=True)
    factory = fields.Many2one("factory.information", string = "Factory")
    machine = fields.Many2one("machine.information",string = "Machine ID",domain="[('factory_id', '=', factory)]")
    model = fields.Many2one(string = "Model",related='machine.model_id', store=True )
    note_create = fields.Text(string="Note create")
    note_confirmed=fields.Text(string="Note confirmed")
    note_cancel = fields.Text(string="Note cancel")
    description = fields.Text(string="Write your description")
    replaced_component_ids = fields.One2many ("replace.information","maintenance", string = "Replaced component")
    export_ids = fields.One2many('export.information', 'maintenance_id', string="Export Records")
    export_count = fields.Integer(
        string="Receipt Count",
        compute="_compute_export_count",
        store=True
    )
    photo = fields.Binary(string='Machine Photo', attachment=True)

    def action_processing(self):
        for rec in self:
            old_status = rec.status
            rec.status = 'processing'
            if old_status != 'processing':
                self.env['notification.history'].notify_maintenance_status(rec, 'to_staff')

    def action_waiting(self):
        for rec in self:
            old_status = rec.status
            rec.write({
                'status': 'waiting',
                'user_created': self.env.user.login.split('@')[0]
            })
            if old_status != 'waiting':
                self.env['notification.history'].notify_maintenance_status(rec, 'to_leader')

    def action_replacing(self):
        for rec in self:
            old_status = rec.status
            rec.write({
                'status': 'replacing',
                'user_confirmed': self.env.user.login.split('@')[0]
            })
            if old_status != 'replacing':
                self.env['notification.history'].notify_maintenance_status(rec, 'to_staff')

    def action_done(self):
        for rec in self:
            export = self.env['export.information'].search([
                ('maintenance_id', '=', rec.id),
                ('status', '=', 'done')
            ], limit=1)
            if not export:
                raise UserError("Cannot change to Done status. Please wait until the export record is completed.")
            old_status = rec.status
            rec.write({
                'status': 'done',
                'user_done': self.env.user.login.split('@')[0]
            })
            if old_status != 'done':
                self.env['notification.history'].notify_maintenance_status(rec, 'to_leader')

    def action_complete(self):
        for rec in self:
            if rec.status != 'done':
                raise UserError("Can only change to Complete status from Done status.")
            rec.write({
                'status': 'complete',
                'datetime_finish': fields.Datetime.now()
            })

    def action_cancel(self):
        for rec in self:
            rec.write({
                'status': 'cancel',
                'user_cancel': self.env.user.login.split('@')[0]
            })

    def action_approve_popup(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Approve Confirmation',
            'res_model': 'maintenance.approval.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_maintenance_id': self.id,
            }
        }

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            vals['name'] = f'M{timestamp}'
        vals['user_created'] = self.env.user.login.split('@')[0]
        vals['datetime_start'] = fields.Datetime.now()
        record = super(maintenance, self).create(vals)
        if record.status == 'waiting':
            self.env['notification.history'].notify_maintenance_status(record, 'to_leader')
        record.message_post(
            body=f"New maintenance record created: {record.name}",
            message_type='notification'
        )
        return record

    @api.depends('export_ids.status')
    def _compute_export_count(self):
        for record in self:
            exports = self.env['export.information'].search([
                ('maintenance_id', '=', record.id),
                ('status', '=', 'done')
            ])
            record.export_count = len(exports)

    def action_open_receipt(self):
        """
        Mở form view của các phiếu Export liên quan.
        """
        return {
            'type': 'ir.actions.act_window',
            'name': 'Export Receipts',
            'view_mode': 'tree,form',
            'res_model': 'export.information',
            'domain': [('maintenance_id', '=', self.id), ('status', '=', 'done')],
            'context': {'default_maintenance_id': self.id},
        }

    def action_open_current_export(self):
        """
        Mở export record hiện tại đang ở trạng thái waiting
        """
        export = self.env['export.information'].search([
            ('maintenance_id', '=', self.id),
            ('status', '=', 'waiting')
        ], limit=1)

        if export:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Export Record',
                'res_model': 'export.information',
                'res_id': export.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Warning',
                'message': 'No waiting export record found for this maintenance',
                'type': 'warning',
            }
        }

    def write(self, vals):
        result = super(maintenance, self).write(vals)
        if 'status' in vals:
            for record in self:
                old_status = record._origin.status  # Lấy trạng thái cũ
                new_status = vals['status']  # Trạng thái mới

                # Trường hợp 1: từ processing sang waiting
                if old_status == 'processing' and new_status == 'waiting':
                    self.env['notification.history'].sudo().notify_maintenance_status(record, 'to_leader')

                # Trường hợp 2: từ waiting sang processing (bị từ chối)
                elif old_status == 'waiting' and new_status == 'processing':
                    self.env['notification.history'].sudo().notify_maintenance_status(record, 'to_staff')

                # Trường hợp 3: từ replacing sang done
                elif old_status == 'replacing' and new_status == 'done':
                    self.env['notification.history'].sudo().notify_maintenance_status(record, 'to_leader')

                # Trường hợp 4: từ done sang replacing (bị từ chối)
                elif old_status == 'done' and new_status == 'replacing':
                    self.env['notification.history'].sudo().notify_maintenance_status(record, 'to_staff')

                # Cập nhật trạng thái máy khi hoàn thành
                if new_status == 'complete' and record.machine:
                    record.machine._compute_status()

        return result

class replaceInformation(models.Model):
    _name = 'replace.information'
    _description = 'Replaced component'

    maintenance = fields.Many2one("maintenance.information", string = "machine")
    component = fields.Many2one("component.information", string="Component")
    models = fields.Many2one("detail.information", compute='_compute_models',store=True,  string="Models")
    quantity = fields.Integer(string = "Quantity")
    receive = fields.Integer(string = "Receive")
    reason = fields.Text(string = "Reason")

    @api.depends('maintenance.model')
    def _compute_models(self):
        for record in self:
            record.models = record.maintenance.model.id if record.maintenance.model else False

class MaintenanceApprovalWizard(models.TransientModel):
    _name = 'maintenance.approval.wizard'
    _description = 'Maintenance Approval Wizard'

    warehouse_id = fields.Many2one("warehouse.information", string="Warehouse", required=True)

    def action_confirm_approval(self):
        maintenance = self.env['maintenance.information'].browse(self._context.get('active_id'))
        if not maintenance:
            return

        export = self.env['export.information'].create({
            'warehouse_id': self.warehouse_id.id,
            'export_code': f"EXP-{maintenance.id}",
            'status': 'new',
        })

        for component in maintenance.replaced_component_ids:
            self.env['export.line.information'].create({
                'name': export.id,
                'component': component.component.id,
                'export_requested': component.quantity,
                'status': 'new',
            })

        maintenance.write({
            'user_confirmed': self.env.user.login.split('@')[0],
            'status': 'replacing'
        })

        self.env['notification.history'].notify_export_status(
            export,
            'to_warehousestaff',
            message=f"New export record [{export.export_code}] has been created for maintenance [{maintenance.name}]"
        )
