from odoo import models, fields
import base64
import xlrd

class modelDetailInformation(models.Model):
    _name = 'detail.information'
    _description = 'detail information'

    ID_model = fields.Char(string = "ID Model")
    name = fields.Char(string = "Name")
    group_id = fields.Many2one("group.information",string = "Group")
    category_id = fields.Many2one(related='group_id.category_id', string="Category", store=True)
    manufacturer = fields.Char(string="Manufacturer")
    description = fields.Text(string = "Description")
    image = fields.Binary(string = "Image")
    part_scan_ids = fields.One2many ("part.scan.information","model_name", string = "Part scan")
    part_list_ids = fields.One2many("part.list.information","model_name", string = "Part list")

    def name_get(self):
        serial_name = []
        for record in self:
            name = record.serial if record.serial else "Unnamed"  # Kiểm tra nếu không có tên
            serial_name.append((record.id, name))
        return serial_name

    def action_import_partlist(self):
        """Hiển thị wizard để import Part List"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Import Part List',
            'res_model': 'import.partlist.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id}
        }

    def action_import_part_scan(self):
        """Hiển thị wizard để import Part Scan"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Import Part Scan',
            'res_model': 'import.partscan.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id}
        }
class partListInformation(models.Model):
    _name = 'part.list.information'
    _description = 'part list information'

    model_name = fields.Many2one('detail.information', string = "Name")
    no = fields.Integer (string = "No")
    component_serial = fields.Many2one ("component.information",string = "Component serial")
    description = fields.Text (string = "Description")
    quantity = fields.Integer(string = "Quantity")
class partScanInformation(models.Model):
    _name = 'part.scan.information'
    _description = 'part scan information'

    model_name = fields.Many2one('detail.information', string = "Name")
    no = fields.Integer (string = "No")
    image = fields.Binary (string = "Image")

