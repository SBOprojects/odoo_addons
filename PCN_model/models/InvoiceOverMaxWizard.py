from odoo import fields, models
from odoo.addons.PCN_model.models.custom_tax_config import MAX_AMOUNT


class InvoiceOverMaxWizard(models.TransientModel):
    _name = 'invoice.over.max.wizard'
    _description = 'Invoices Over Max Amount Without VAT ID'

    invoices_details = fields.Html("Invoices Details")
    invoice_ids = fields.Many2many('account.move', string="Invoices")

    def action_cancel(self):
        """Cancels the action and closes the wizard."""
        return {'type': 'ir.actions.act_window_close'}
