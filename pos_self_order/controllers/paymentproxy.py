from odoo import http
from odoo.http import request
import requests
import hashlib
import base64
import logging
import json

_logger = logging.getLogger(__name__)

class PaymentController(http.Controller):
      @http.route('/pos-self-order/get_payment_status', type='json', auth='public')
      def get_payment_status(self, order_id):
            company_num = '6312841'
            merchant_hash_key = '39YVLZ32VH'
            signature = self.generate_signature(company_num, order_id, merchant_hash_key)

            url = f"https://process.ecom.nayax.com/member/getStatus.asp?Order={order_id}&CompanyNum={company_num}&signature={signature}"
            try:
                  response = requests.get(url, headers={
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                  })
                  response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
                  _logger.info(f"Response from payment status request: {response.json()}")
                  return response.json()
            except requests.exceptions.RequestException as e:
                  _logger.error(f"Error fetching payment status: {str(e)}")
                  return {"error": f"Error fetching payment status: {str(e)}"}

      def generate_signature(self, companyNum, order, merchantHashKey):
            data = (companyNum + order + merchantHashKey).encode('utf-8')
            hash_object = hashlib.sha256(data)
            hash_base64 = base64.b64encode(hash_object.digest()).decode('utf-8')
            return hash_base64

class NayaxPaymentStatus(http.Controller):
      @http.route('/pos-self/<int:pos_config_id>/paymentstatus', type='http', auth="public", methods=['GET'], website=True)
      def payment_status(self, pos_config_id, **kwargs):
            return request.render('pos_self.payment_status_page_template', {'pos_config_id': pos_config_id})
      
      @http.route('/pos-self/nayax_payment_status/nayax_payment_success', type='json', auth="public", methods=['POST'], website=True)
      def nayax_payment_success(self, **kwargs):
            _logger.info('Payment Successful: %s', kwargs)
            return {"success": True, "message": "Payment was Success"}

      @http.route('/pos-self/nayax_payment_status/nayax_payment_pending', type='json', auth="public", methods=['POST'], website=True)
      def nayax_payment_pending(self, **kwargs):
            _logger.info('Payment Pending: %s', kwargs)
            return {"success": True, "message": "Payment is pending"}

      @http.route('/pos-self/nayax_payment_status/nayax_payment_failed', type='json', auth="public", methods=['POST'], website=True)
      def nayax_payment_failed(self, **kwargs):
            _logger.info('Payment Failed: %s', kwargs)
            return {"success": True, "message": "Payment has failed"}