from datetime import datetime
import requests
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import _, json
from odoo.addons.nayax_pos_auth.crypto_utils import decrypt_data, encrypt_data, generate_key, get_token, handle_request_with_relogin

class ProductTemplate(models.Model):
    _inherit = "product.template"
    sent_to_api = fields.Boolean("Sent to API", default=False)
    sirius_item_id = fields.Integer("API Item ID", readonly=True)
    is_modifier = fields.Boolean("Is Modifier", default=False)
    prices = fields.Char("Prices")
    list_price = fields.Float(digits=(12, 6)) # This change will tell the system to expect more decimals.


    @api.model_create_multi
    def create(self, vals_list):

        config = self.env['ir.config_parameter'].sudo()
        token = get_token(config)


        templates = super(ProductTemplate, self).create(vals_list)
        for template in templates:
            if self.add_new_item(template):
                template.sent_to_api = True 
            print('*****************')

        return templates



    def write(self, vals):

        config = self.env['ir.config_parameter'].sudo()
        token = get_token(config)
        
        res = super(ProductTemplate, self).write(vals)
        for template in self:
            if template.sent_to_api:
                self.update_item(template)
        return res

 
  
    def add_new_item(self, template):
        secret_key = generate_key()  # Generate the key for decryption

        config = self.env['ir.config_parameter'].sudo()
        #self.env['api.auth'].search([], order="id desc", limit=1)
        token = get_token(config)
        api_url = "https://gateway-api-srv.stage.bnayax.com/api/item"
        from_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
        list_price = template.list_price

        headers = {
            "Authorization": f"Bearer {token.strip()}",
            "Cache-Control": "no-cache",
            "Content-Type": "text/plain",
            "User-Agent": "PostmanRuntime/7.43.0",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "accept": "application/vnd.item-upitec.v1.0+json",
            "Content-Type": "application/json"
        }


            # Prepare the request body for each created product
        payload = {
                "barcodes": [],
                "cestCode": None,
                "code": template.default_code,
                "directSupply": False,
                "distributionRecommendation": False,
                "downloadToPOS": True,
                "frozenFrom": None,
                "frozenTo": None,
                "giftCard": False,
                "giftCardSubTenderID": None,
                "giftCardTenderID": None,
                "history": False,
                "htmlDescription": None,
                "imageBasketSetId": None,
                "inventoryItem": True,
                "isAllowZeroPrice": False,
                "isConsignmentItem": False,
                "isECommerce": False,
                "isFrozen": False,
                "isKiosk": False,
                "isModifier": False,
                "isRequestModifier": True,
                "isReviewAllowed": False,
                "isTareRequired": False,
                "isValid": True,
                "isValidateCode": False,
                "itemBrandID": None,
                "itemHierarchyValues": {
                    "1": 1,
                    "2": None,
                    "3": None,
                    "4": None,
                    "5": None
                },
                "itemModelID": None,
                "itemUnitType": 1,
                "languageDataAdditionalInfo": [],
                "languageDataNutritionFacts": [],
                "languageDataShortDisplayName": [
                    {
                        "languageId": 1,
                        "name": template.name
                    }
                ],
                "languageDataShortPrintName": [
                    {
                        "languageId": 1,
                        "name": template.name
                    }
                ],
                "linkedItemIds": [],
                "manufactureID": None,
                "metric1": None,
                "metric2": None,
                "metric3": None,
                "ncmCode": None,
                "numberingId": 9,
                "prefferedSupplierID": None,
            "prices": [
                {
                    "priceNumberId": 2,  
                    "fromDate": from_date,  
                    "price": list_price,  
                    "isDeleted": False
                }
            ],
                "properties": [],
                "purchaseItem": True,
                "purchaseNote": None,
                "purchaseRecommendation": False,
                "refundable": True,
                "registrationDate": None,
                "saleItem": True,
                "shortDisplayName": template.name,
                "shortPrintName": template.name,
                "supplierCatNum": None,
                "taxClassId": None,
                "udf": [],
                "validFrom": None,
                "validTo": None
            }

        print(f"Debug: Payload for template ID {template.id}: {payload}")

        try:
                print(f"Debug: Sending request for template ID: {template.id}")
                is_expired, response_json =   handle_request_with_relogin(api_url,payload, "POST" ,headers,config ,secret_key)
                
                print(response_json)

                if response_json.get("status") == "OK":
                    template.sirius_item_id = response_json.get("data", {}).get("id")
                    self.update_item(template)
                    return True



        except requests.exceptions.RequestException as e:
                raise UserError(f"Failed to send data to the API: {e}")
        

    def update_item(self, template):
            if not template.sirius_item_id:
                return
            api_url = f"https://gateway-api-srv.stage.bnayax.com/api/item/{template.sirius_item_id}"
            secret_key = generate_key()  # Generate the key for decryption

            config = self.env['ir.config_parameter'].sudo()
            token = get_token(config)

            headers = {
                "Authorization": f"Bearer {token.strip()}",
                "Cache-Control": "no-cache",
                "Content-Type": "text/plain",
                "User-Agent": "PostmanRuntime/7.43.0",
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "accept": "application/vnd.item-upitec.v1.0+json",
                "Content-Type": "application/json"
            }

            try:
                print(f"Debug: Sending GET request for template ID: {template.sirius_item_id}")
                is_expired, response_json =   handle_request_with_relogin(api_url,'', "GET" ,headers,config ,secret_key)

                get_response = requests.get(api_url, headers=headers)
                get_response.raise_for_status()
                item_data = get_response.json()
                # Extract GUID and code
                guid = item_data.get("data", {}).get("guid", "")
                code = item_data.get("data", {}).get("code", "")
                price_number_id = item_data.get("data", {}).get("prices", [{}])[0].get("priceNumberId", "")
                price_id = item_data.get("data", {}).get("prices", [{}])[0].get("Id", "")


                print('*****************************************************')

                print(template.read())
                list_price = template.list_price
                from_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
                if not guid:
                    raise UserError("GUID not found in the response.")
                
                print(f"Debug: Extracted GUID: {guid}")
            
            except requests.exceptions.RequestException as e:
                raise UserError(f"Failed to fetch item data: {e}")

            payload = {
                "additionalInfo": "",
                "barcodes": [],
                "code": code,
                "collections": [],
                "currentStock": [],
                "directSupply": False,
                "distributionRecommendation": False,
                "downloadToPOS": True,
                "frozenFrom": None,
                "frozenTo": None,
                "giftCard": False,
                "giftCardSubTenderID": None,
                "giftCardTenderID": None,
                "guid": guid,
                "history": False,
                "htmlDescription": None,
                "imageBasketSetId": None,
                "inventoryItem": True,
                "isAllowZeroPrice": False,
                "isComboMeal": False,
                "isConsignmentItem": False,
                "isECommerce": False,
                "isFrozen": False,
                "isKiosk": False,
                "isModifier": False,
                "isRequestModifier": True,
                "isReviewAllowed": False,
                "isTareRequired": False,
                "isValid": True,
                "itemBrandID": None,
                "itemHierarchyValues": {
                    "1": 1,
                    "2": None,
                    "3": None,
                    "4": None,
                    "5": None
                },
                "itemModelID": None,
                "itemUnitType": 1,
                "languageDataAdditionalInfo": [
                    {
                        "languageId": 1,
                        "name": ""
                    }
                ],
                "languageDataNutritionFacts": [
                    {
                        "languageId": 1,
                        "name": ""
                    }
                ],
                "languageDataShortDisplayName": [
                    {
                        "languageId": 1,
                        "name": template.name
                    }
                ],
                "languageDataShortPrintName": None,
                "linkedItemIds": [],
                "manufactureID": None,
                "metric1": None,
                "metric2": None,
                "metric3": None,
                "nutritionFacts": "",
                "prefferedSupplierID": None,
                "prices": [
                {
                    "id": price_id,  # This ID can be dynamically set as needed
                    "priceNumberId": price_number_id,  # Adjust accordingly
                    "fromDate": from_date,  # Dynamic fromDate
                    "price": list_price,  # Use the list price from the template
                    "guid": guid,  # This should match the GUID
                    "isDeleted": False
                }
            ],
                "properties": [],
                "purchaseItem": True,
                "purchaseNote": None,
                "purchaseRecommendation": False,
                "refundable": True,
                "registrationDate": None,
                "saleItem": True,
                "shortDisplayName": template.name,
                "shortPrintName": template.name,
                "supplierCatNum": None,
                "taxClassId": None,
                "udf": [],
                "validFrom": None,
                "validTo": None
            }

            print(f"Debug: Payload for template ID {template.id}: {payload}")

            try:
                print(f"Debug: Sending PUT request for template ID: {template.id}")
                is_expired, response_json =   handle_request_with_relogin(api_url,payload, "PUT" ,headers,config ,secret_key)
                print(f"Debug: Response: {response_json}")
            except requests.exceptions.RequestException as e:
                raise UserError(f"Failed to send data to the API: {e}")

    def display_notification(self, title, message, notification_type='info'):
        """Display notification to the user."""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': notification_type,
                'sticky': False,
            },
        }