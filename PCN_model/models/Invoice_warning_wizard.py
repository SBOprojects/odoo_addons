from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools import _

class InvoiceConfirmationWizard(models.TransientModel):
    _name = 'invoice.confirmation.wizard'
    _description = 'Confirm or Cancel File Download'

    invoice_report_id = fields.Many2one('invoice.report.wizard', string="Invoice Report")
    missing_vat_count = fields.Integer("Number of Invoices without VAT ID")
    invoices_details = fields.Html("Invoices Details")
    invoice_ids = fields.Many2many('account.move', string="Invoices")  # Add Many2many field for invoices

    def action_confirm(self):


        # Process selected invoices and generate TXT file
        self.invoice_report_id.create_custom_txt()
        return self.invoice_report_id.download_file()

    def action_cancel(self):
        """Cancels the file download."""
        return {'type': 'ir.actions.act_window_close'}
    
    def _default_invoices_details(self):
        return self._context.get('default_invoices_details', '')

    _defaults = {
        'invoices_details': _default_invoices_details,
    }
