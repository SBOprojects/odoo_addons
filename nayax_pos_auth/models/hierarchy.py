from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import _

class ProductTemplateHierachy(models.Model):
    _name = "pos.hierachy"

    # Removing the default id, as Odoo automatically creates it
    custom_id = fields.Char(string='Custom ID', required=True, unique=True)  # Your custom identifier
    code = fields.Char(string='Code')
    displayName = fields.Char(string='Display Name')
    printName = fields.Char(string='Print Name')
    images = fields.Binary(string='Images')
