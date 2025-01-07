from odoo import models, fields

class ProductCategory(models.Model):
    _inherit = 'product.category'

    nayax_category_code = fields.Char(string='Nayax Category Code', required=True)
    
    def _create_or_update_categories(self, categories_data):
        for data in categories_data:
            category = self.search([('nayax_category_code', '=', data.get('nayax_category_code'))], limit=1)
            if category:
                category.write(data)
            else:
                self.create(data)

class PosCategory(models.Model):
    _inherit = 'pos.category'

    nayax_category_code = fields.Char(string='Nayax Category Code', required=True)
    
    def _create_or_update_categories(self, categories_data):
        for data in categories_data:
            category = self.search([('nayax_category_code', '=', data.get('nayax_category_code'))], limit=1)
            if category:
                category.write(data)
            else:
                self.create(data)


class PosCategory(models.Model):
    _inherit = 'product.attribute.value'

    sirius_item_id = fields.Integer("API Item ID", readonly=True)
    