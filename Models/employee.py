from odoo import models, fields

class employee(models.Model):
    _name = 'employee.information'
    _description = 'employee information'

    id_code = fields.Char(string = "ID Employee")
    name = fields.Char(string = "Name")
    email = fields.Char(string="Email")
    position = fields.Char(string="Position")
    # factory = fields.Char(string="Factory")
    factory_id = fields.Many2one("factory.information", string= "Factory")
    image = fields.Binary(string="Employee Image", max_width = 8, max_height = 8)
    sex = fields.Selection([('male','Male'),('female','Female')], string = "Gender")
    phone = fields.Integer (string = "Phone")
    birthday = fields.Date(string = "Birthday")
