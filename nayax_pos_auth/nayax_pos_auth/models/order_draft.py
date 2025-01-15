from odoo import models, fields, api
import requests

from odoo.exceptions import UserError

# kad_shahd

class OrderDraft(models.Model):
    _name = 'order.draft'
    order_id = fields.Integer(string='Order ID')
    order_number = fields.Integer(string='Order Number')
    order_name = fields.Char(string='Order Name')   
    table_number = fields.Char(string='Table Number')
    table_name = fields.Char(string='Table Name')  
    date_time = fields.Datetime(string='Date and Time')

    employee_id = fields.Many2one('hr.employee', string='Employee')
    total_to_pay = fields.Float(string='Total To Pay')
    total_paid = fields.Float(string='Total Paid')
    status = fields.Char(string='Status')
    locked_by = fields.Integer(string='Locked By')
    guid = fields.Char(string='GUID')
    total_tips_amount = fields.Float(string='Total Tips Amount')
    remark = fields.Char(string='Remark')
    is_bill_printed = fields.Boolean(string='Is Bill Printed')
    total_amount = fields.Float(string='Total Amount')
    rounding_amount = fields.Float(string='Rounding Amount')

