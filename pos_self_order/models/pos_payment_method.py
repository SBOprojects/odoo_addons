from odoo import models, api


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    # will be overridden.
    def _payment_request_from_kiosk(self, order):
        pass
# kad_shahd
    @api.model
    def _load_pos_self_data_domain(self, data):
        if data['pos.config']['data'][0]['self_ordering_mode'] == 'kiosk':
            # Only include the cash payment method
            return [('use_payment_terminal', '=', False),  # Assuming cash doesn't use terminal
                    ]  # This could be 'cash' or another condition specific to cash payments
        else:
            return [('id', '=', False)]






