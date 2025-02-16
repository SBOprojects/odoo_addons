
# kad_shahd
import logging
import re
import requests
import werkzeug

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError, AccessError

_logger = logging.getLogger(__name__)
TIMEOUT = 10

class PosPaymentMethod(models.Model):

    _inherit = 'pos.payment.method'
    api_key = fields.Char(string="Payment Device IP ", copy=False)
    public_api_key = fields.Char(string="Public IP", copy=False)
    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('nayax', 'Nayax')]
    

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ['api_key']
        params += ['public_api_key']

        return params
    


    def save_api_key(self):
        for record in self:
            if not record.api_key:
                raise UserError(_("API key cannot be empty!"))
            _logger.info("API key saved for payment method: %s", record.name)
            # Here, you can add any logic needed to use the api_key for other purposes
            # For example, updating a related model or making an API call
            record.write({'api_key': record.api_key , 'public_api_key': record.public_api_key})
            return True
        
