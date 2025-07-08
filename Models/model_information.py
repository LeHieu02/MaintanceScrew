from odoo import api, models, fields
from odoo.exceptions import UserError
import openpyxl


class modelGroupInformation(models.Model):
    _name = 'group.information'
    _description = 'group information'

    category_id = fields.Many2one("category.information",string = "Category")
    name = fields.Char(string = "Group")
    detail_list = fields.One2many("detail.information","group_id","Detail list")
    group_id = fields.Char("Group ID")


    def show_group_details(self):
        self.ensure_one()
        if not self.id:
            raise UserError("No group selected!")
        return {
            'type': 'ir.actions.act_window',
            'name': 'Detail Kanban View',
            'view_mode': 'kanban,form',
            'res_model': 'detail.information',  # Model chi tiết
            'domain': [('group_id', '=', self.id)],  # Hiển thị chi tiết liên quan tới group hiện tại
            'context': {'default_group_id': self.id, 'view_type': 'form'},  # Hiển thị toàn màn hình hoặc pop-up (tùy chọn)
        }



class modelCategoryInformation(models.Model):
    _name = 'category.information'
    _description = 'category information'

    name = fields.Char("Name")
    no = fields.Integer("No")
    group_list = fields.One2many("group.information", "category_id", string = "Group list")
    category_id = fields.Char("Category ID")
    def name_get(self):
        result = []
        for record in self:
            name = record.name if record.name else "Unnamed"  # Kiểm tra nếu không có tên
            result.append((record.id, name))
        return result

