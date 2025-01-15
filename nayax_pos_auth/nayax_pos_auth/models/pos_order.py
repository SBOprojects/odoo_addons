
from datetime import datetime
import json
import threading
import time
import requests
import schedule
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import _
from odoo.addons.nayax_pos_auth.crypto_utils import decrypt_data, encrypt_data, generate_key, get_token, handle_request_with_relogin


class PosOrder(models.Model):
    _inherit = "pos.order"
    order_draft_id = fields.Integer(string='Draft Order ID')
    _processed_orders = set()

    @api.model_create_multi
    def create(self, vals_list):
        print('999999999999999999999999999999999999')
        secret_key = generate_key()  # Generate the key for decryption

        config = self.env['ir.config_parameter'].sudo()
        #self.env['api.auth'].search([], order="id desc", limit=1)
        encrypted_access_token = config.get_param('external_access_token')
        if not encrypted_access_token:
        # Raise UserError with message instead of display_notification
            raise UserError(
                _('Authentication Token Missing\nPlease log in to the Sirius Model first.')
            )
        access_token = decrypt_data(encrypted_access_token, secret_key)
        orders = super().create(vals_list)
        # Call the add_order method for each created order
        # for order in orders:
        #       order.add_order(order)        
        return orders
    

    @api.model
    def _process_order(self, order, existing_order):
        """Override the method to add a print statement and call the super method."""
        # Add your custom print statement
        print('***********************************************************************')
        result = super(PosOrder, self)._process_order(order, existing_order)
        if existing_order:
            
            print(order)
            self.update_order_draft(order)
        return result
    
    def write(self, values):
            """
            Override the write method to ensure add_order is called only once per order
            and only after calling the parent write method.
            """
            # Debug statement
            print('55555555555599999999999999999999999999999999')

            # Call the original write method first
            result = super(PosOrder, self).write(values)

            # Check conditions and call add_order if needed
            for order in self:
                if order.state == 'paid' and order.order_draft_id == 0:
                    if order.id not in self._processed_orders:
                        print(self._processed_orders)
                        print(f"Order {order.name} state: {order.state}")
                        self._processed_orders.add(order.id)
                        self.add_order(order)

            # Return the result of the super write method
            return result

    def add_order(self, order):
        api_url = "https://gateway-api-srv.stage.bnayax.com/api/transaction-draft"
        secret_key = generate_key()  # Generate the key for decryption

        config = self.env['ir.config_parameter'].sudo()
        token = get_token(config)

        # Now we can safely strip the token
        headers = {
        "Authorization": f"Bearer {token.strip()}",
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "Accept": "application/vnd.transaction-upitec.v1.0+json",
        "User-Agent": "PostmanRuntime/7.43.0"

        }
        payload = self.payelod_data(order)
        
        try:
                print(f"Debug: Sending request for template ID:")

                
                response = requests.post(api_url, json=payload, headers=headers)
                is_expired, response_json =   handle_request_with_relogin(api_url,payload, "POST" ,headers,config ,secret_key)

                response.raise_for_status()  # Raise exception for HTTP errors
                print(f"Debug: Request sent successfully for template ID ")
                print(f"Debug: Response: {response_json}")


                if response_json.get("status") == "OK":
                        order.order_draft_id = response_json.get("data", {}).get("id")

                        print(order.order_draft_id)

        except requests.exceptions.RequestException as e:
                raise UserError(f"Failed to send data to the API: {e}")
        

    def get_order_by_draft_id(self,order):
        order_draft_id = order.get('order_draft_id')
        print(order_draft_id)
        api_url = f"https://gateway-api-srv.stage.bnayax.com/api/transaction-draft/{order_draft_id}"
        secret_key = generate_key()  # Generate the key for decryption

        config = self.env['ir.config_parameter'].sudo()
        token = get_token(config)

        # Now we can safely strip the token
        headers = {
        "Authorization": f"Bearer {token.strip()}",
        }
        try:
                print(f"Debug: Sending GET request for template ID: {order_draft_id}")
                is_expired, response_json =   handle_request_with_relogin(api_url,'', "GET" ,headers,config ,secret_key)
                print( response_json)
                return response_json
        except requests.exceptions.RequestException as e:
             raise UserError(f"Failed to fetch item data: {e}")

    def update_order_draft(self, order):
        order_befor_update = self.get_order_by_draft_id(order)
        order_draft_id = order.get('order_draft_id')

        api_url = f"https://gateway-api-srv.stage.bnayax.com/api/transaction-draft/{order_draft_id}"
        secret_key = generate_key()  # Generate the key for decryption

        config = self.env['ir.config_parameter'].sudo()
        #self.env['api.auth'].search([], order="id desc", limit=1)
        token = get_token(config)

        headers = {
            "Authorization": f"Bearer {token.strip()}",
            "Content-Type": "application/json",
        }   
        guid = order_befor_update.get('data', {}).get('guid')
        print(guid)
        payload =self.payelod_data_update(order,guid)

        print(payload)
        
        try:
            print(f"Debug: Sending PUT request for template ID: {order_draft_id}")
            is_expired, response_json =   handle_request_with_relogin(api_url,payload, "PUT" ,headers,config ,secret_key)
            print(f"Debug: Response: {response_json}")

        except requests.exceptions.RequestException as e:
            raise UserError(f"Failed to send data to the API: {e}")
  
    def payelod_data(self,order):
        print(order.read()[0]) 
        order_data = order.read()[0]


        cashierNumber =    order_data['user_id'][0]
        # openTransactionEmployeeId = order_data['employee_id']
        if order_data['partner_id']:
            partnerCode = order_data['partner_id'][0]
            partnername = order_data['partner_id'][1]
            name_parts = partnername.split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''
        else:
            partnerCode = None
            first_name = None
            last_name = None

        amount = order_data['amount_paid']
        currencyAmount = order_data['amount_paid']

        tip_tender_list_amount = order_data['amount_difference'] 
        tip_tender_List_currency_amount= order_data['amount_difference'] 
        draftTransactionNumber = f"{order_data['id']:04d}"
        transactionRemarks = order_data['name']


        # Ensure that 'create_date' and 'write_date' are in the correct format
        draftTransactionDate = order_data['create_date'].strftime('%Y-%m-%d %H:%M:%S.%f') if order_data['create_date'] else None
        transactionStartDateTime = order_data['write_date'].strftime('%Y-%m-%d %H:%M:%S.%f') if order_data['write_date'] else None
        updateDraftStatusDateTime = order_data['create_date'].strftime('%Y-%m-%d %H:%M:%S.%f') if order_data['create_date'] else None

        items = []

        # Fetch all order lines
        order_lines = self.env['pos.order.line'].search([('order_id', '=', order_data['id'])])

        # Iterate through each order line and construct the JSON data
        for line in order_lines:
            item_amount = line.price_subtotal_incl
            product = self.env['product.product'].search([('id', '=', line.product_id.id)], limit=1)
            if product:
                sirius_item_id = product.sirius_item_id
            else:
                sirius_item_id = None
            item_code = sirius_item_id  # Assuming 'default_code' as the item code
            item_name = line.full_product_name
            line_number = line.id
            item_price = line.price_unit
            item_qty = line.qty
            vat_amount = line.price_subtotal_incl - line.price_subtotal  # VAT amount calculation

             # Modifier extraction logic
            modifiers = []
            print(f"Processing item1: {line.full_product_name}")
            if '(' in line.full_product_name and ')' in line.full_product_name:
                try:
                    modifier_str = line.full_product_name.split('(', 1)[1].rsplit(')', 1)[0]
                    modifier_names = [mod.strip() for mod in modifier_str.split(',')]

                    for mod_name in modifier_names:
                         # Find the modifier in product.template.attribute.value model
                        modifier_record = self.env['product.template.attribute.value'].search([('name', '=', mod_name)], limit=1)
                        modifier_price = modifier_record.price_extra if modifier_record else 0.0
                        print(f"Modifier Product: {mod_name}, Price: {modifier_price}")
                        modifiers.append({
                            "itemModifierName": mod_name,
                            "price": modifier_price,  # Get the price from model
                            "quantity": 1,
                        })
                except:
                    print("Error in modifiers1")

            # Append the formatted item data to the list
            items.append({
                "amount": item_amount,
                # TODO: should to change it to  item_code after add items to sirius
                "itemCode": 1000  ,  
                "itemName": item_name,
                "lineNumber": line_number,
                "price": item_price,
                "quantity": item_qty,
                "vatAmount": vat_amount,
                "modifiers":modifiers,
            })


        # Print the JSON structure
       
        payload = {
                "cashierNumber": cashierNumber,
                "openTransactionEmployeeId": 1,
                "createAbsentObjects": False,
                "posCode": "1",
                "storeCode": "1",
                "items":items,
                "partners": [
                    {
                        "partnerCode": partnerCode,
                        "partnerFirstName": first_name,
                        "partnerlastName": last_name
                    }
                ],
                "payments": {
                    "cashList": [
                        {
                            "amount": amount,
                            "cashRounding": False,
                            "currencyAmount": currencyAmount,
                            "currencyCode": "1",
                            "guid": "d69edcf8-dae9-4fe0-a015-b78d6249a5d8"
                        }
                    ],
                    "tipTenderList": [
                        {
                            "amount": tip_tender_list_amount,
                            "linked": "d69edcf8-dae9-4fe0-a015-b78d6249a5d8",
                            "currencyAmount": tip_tender_List_currency_amount,
                            "currencyCode": "NIS",
                            "guid": "84f4236e-87b4-44e4-b6c8-6c56fcbac0e0"
                        }
                    ]
                },
                "status": 0,
                "draftTransactionDate": draftTransactionDate,
                "draftTransactionNumber": draftTransactionNumber,
                "transactionRemarks": transactionRemarks,
                "transactionStartDateTime": transactionStartDateTime,
                "transactionType": 1,
                "draftTransactionStatus": "OPENED",
                "updateDraftStatusDateTime": updateDraftStatusDateTime,
                "extendedData": {
                    "kioskServiceType": "2"
                }
            }
        return payload   

    def payelod_data_update(self, order, guid):
        cashierNumber = order.get('user_id') # Ensure it's set to 100 or dynamically based on some logic if needed
        partner_id = order.get('partner_id')
        partnerCode = partner_id[0] if isinstance(partner_id, (list, tuple)) else None
        partnerName = partner_id[1] if isinstance(partner_id, (list, tuple)) and len(partner_id) > 1 else ''

        name_parts = partnerName.split(' ', 1)
        first_name = name_parts[0] if partnerName else None
        last_name = name_parts[1] if len(name_parts) > 1 else None

        amount = order.get('amount_paid', 0)
        currencyAmount = amount

        tip_tender_list_amount = order.get('amount_difference', 0)
        tip_tender_List_currency_amount = tip_tender_list_amount
        draftTransactionNumber = f"{order.get('id', 0):04d}"
        transactionRemarks = order.get('name', '')

        # Ensure that 'create_date' and 'write_date' are properly formatted


        items = []

        # Fetch all order lines
        order_lines = self.env['pos.order.line'].search([('order_id', '=', order.get('id'))])
        draftTransactionDate = order.get('create_date')
        original_datetime = datetime.strptime(draftTransactionDate, "%Y-%m-%d %H:%M:%S")
        formatted_datetime = original_datetime.strftime("%Y-%m-%dT%H:%M:%S.") + f'{original_datetime.microsecond // 1000:03d}Z'



        transactionStartDateTime = order.get('write_date')
        original_datetime1 = datetime.strptime(transactionStartDateTime, "%Y-%m-%d %H:%M:%S")
        formatted_datetime2 = original_datetime.strftime("%Y-%m-%dT%H:%M:%S.") + f'{original_datetime1.microsecond // 1000:03d}Z'

        print(transactionStartDateTime)
        # Iterate through each order line and construct the JSON data
        for line in order_lines:
            item_amount = line.price_subtotal_incl
            product = self.env['product.product'].search([('id', '=', line.product_id.id)], limit=1)
            sirius_item_id = product.sirius_item_id if product else None

            # Modifier extraction logic
            modifiers = []
            print(f"Processing item2: {line.full_product_name}")
            if '(' in line.full_product_name and ')' in line.full_product_name:
                try:
                    modifier_str = line.full_product_name.split('(', 1)[1].rsplit(')', 1)[0]
                    modifier_names = [mod.strip() for mod in modifier_str.split(',')]
                    for mod_name in modifier_names:
                        # Find the modifier in product.template.attribute.value model
                        modifier_record = self.env['product.template.attribute.value'].search([('name', '=', mod_name)], limit=1)
                        modifier_price = modifier_record.price_extra if modifier_record else 0.0  # Get the price from the model
                        modifiers.append({
                            "itemModifierName": mod_name,
                            "price": modifier_price,  # Get the price from model
                            "quantity": 1,
                        })
                except:
                    print("Error in modifiers2")
            
            items.append({
                "amount": item_amount,
                "itemCode": str(sirius_item_id or 1000),  # Ensure itemCode is a string
                "itemName": line.full_product_name,
                "lineNumber": line.id,
                "price": line.price_unit,
                "quantity": line.qty,
                "vatAmount": line.price_subtotal_incl - line.price_subtotal,
                 "modifiers":modifiers,
            })

        payload = {
            "cashierNumber": cashierNumber,
            "openTransactionEmployeeId": 1,
            "createAbsentObjects": False,
            "posCode": "1",
            "storeCode": "1",
            "guid": guid,
            "items": items,
            "partners": [
                {
                    "partnerCode": partnerCode,
                    "partnerFirstName": first_name,
                    "partnerlastName": last_name
                }
            ],
            "payments": {
                "cashList": [
                    {
                        "amount": amount,
                        "cashRounding": False,
                        "currencyAmount": currencyAmount,
                        "currencyCode": "1",
                        "guid": "d69edcf8-dae9-4fe0-a015-b78d6249a5d8"
                    }
                ],
                "tipTenderList": [
                    {
                        "amount": tip_tender_list_amount,
                        "linked": "d69edcf8-dae9-4fe0-a015-b78d6249a5d8",
                        "currencyAmount": tip_tender_List_currency_amount,
                        "currencyCode": "NIS",
                        "guid": "84f4236e-87b4-44e4-b6c8-6c56fcbac0e0"
                    }
                ]
            },
            "status": 0,
            "draftTransactionDate": formatted_datetime,
            "draftTransactionNumber": draftTransactionNumber,
            "transactionRemarks": transactionRemarks,
            "transactionStartDateTime": formatted_datetime2,
            "transactionType": 1,
            "draftTransactionStatus": "OPENED",
            "updateDraftStatusDateTime": formatted_datetime2,
            "extendedData": {
                "kioskServiceType": "2"
            }
        }

        return payload 