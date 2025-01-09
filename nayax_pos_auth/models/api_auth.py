import json
import requests
from odoo import models, fields, api
from odoo.addons.nayax_pos_auth.crypto_utils import decrypt_data, encrypt_data, generate_key, get_token
from odoo.exceptions import UserError
from cryptography.fernet import Fernet
from datetime import datetime, timedelta
from odoo import api, SUPERUSER_ID

class ApiAuth(models.Model):
    _name = 'api.auth'
    _description = 'API Authentication'

    login = fields.Char(required=True)
    password = fields.Char(required=True)
    token = fields.Char(readonly=True)
    refresh_token = fields.Char(readonly=True)
    session_id = fields.Char(readonly=True)
    auth_status = fields.Boolean(default=False)
    
    def authenticate(self):
        login_url = "https://gateway-api-srv.stage.bnayax.com/api/login"
        payload = {
            "login": self.login,
            "password": self.password,
            "extraClaims": {
                "additionalProp1": "string",
                "additionalProp2": "string",
                "additionalProp3": "string"
            }
        }
        headers = {
            'Content-Type': 'application/json'
        }
        config = self.env['ir.config_parameter'].sudo()
        secret_key = generate_key()  # Generate the key dynamically or load from environment
        try:
            response = requests.post(login_url, json=payload, headers=headers)
            response.raise_for_status()  # Raise HTTPError for bad responses
            response_data = response.json()

            if response_data.get('status') == 'OK' and response_data.get('data'):
                data = response_data['data']
                access_token = data.get('accessToken')
                refresh_token = data.get('refreshToken')
                session_id = data.get('sessionId')
                companies = data.get('companies', [])
                company_names = [company.get('name') for company in companies]

                print(f"Access token: {access_token}")
                print(f"Refresh token: {refresh_token}")
                print(f"Session ID: {session_id}")
                print(f"Company names: {company_names}")

                encrypted_access_token = encrypt_data(access_token, secret_key)
                encrypted_refresh_token = encrypt_data(refresh_token, secret_key)
                encrypted_session_id = encrypt_data(session_id, secret_key)
                encrypted_companies = encrypt_data(json.dumps(company_names), secret_key)
                encrypted_username = encrypt_data(self.login, secret_key)
                encrypted_password = encrypt_data(self.password, secret_key)

                # Bulk update config parameters using dict
                config_params = {
                    'external_access_token': encrypted_access_token,
                    'external_refresh_token': encrypted_refresh_token,
                    'external_session_id': encrypted_session_id,
                    'external_companies': encrypted_companies,
                    'external_username': encrypted_username,
                    'external_password': encrypted_password,
                }
                for key, value in config_params.items():
                    config.set_param(key, value)

                print(self.get_decrypted_tokens())
                return self.display_notification('Login Successful', f'Welcome, {data.get("firstName")} {data.get("lastName")}', 'success')
            else:
                self.clear_sensitive_data(config)
                return self.display_notification('Error', 'Unexpected response format.', 'danger')

        except requests.RequestException as e:
            self.clear_sensitive_data(config)
            return self.display_notification('Error', f'API Request failed: {str(e)}', 'danger')

    def clear_sensitive_data(self, config):
        keys_to_clear = [
            'external_access_token',
            'external_refresh_token',
            'external_session_id',
            'external_companies',
            'external_username',
            'external_password',
        ]
        for key in keys_to_clear:
            try:
                config.set_param(key, '')
            except Exception as e:
                print(f"Error clearing key {key}: {e}")


    def get_decrypted_tokens(self):
        secret_key = generate_key()
        config = self.env['ir.config_parameter'].sudo()
        encrypted_access_token = config.get_param('external_access_token')
        encrypted_refresh_token = config.get_param('external_refresh_token')
        encrypted_session_id = config.get_param('external_session_id')
        encrypted_companies = config.get_param('external_companies')
        
        # Decrypt all at once, avoids repeated calls to decrypt_data
        return (
            decrypt_data(encrypted_access_token, secret_key),
            decrypt_data(encrypted_refresh_token, secret_key),
            decrypt_data(encrypted_session_id, secret_key),
            json.loads(decrypt_data(encrypted_companies, secret_key)),
        )


    def send_all_products_to_api(self):
        products = self.env['product.template'].search([('sent_to_api', '=', False)])
        if not products:
            return self.display_notification('Info', 'No Products to Export', 'info')
        
        config = self.env['ir.config_parameter'].sudo()
        token = get_token(config)

        # Collect products that need to be exported before looping, allows us to do a batch write
        products_to_update = []
        for product in products:
            if self.export_item(product):
                products_to_update.append(product.id)

        # Use a batch write operation to update the products at the end.
        if products_to_update:
             self.env['product.template'].browse(products_to_update).write({'sent_to_api': True})
        
        return self.display_notification('Success', 'Complete Export All Products!', 'success')


    def export_item(self, template):
        api_url = "https://gateway-api-srv.stage.bnayax.com/api/item"
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
            "prices": [],
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
            response = requests.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            print(f"Debug: Request sent successfully for template ID {template.id}.")
            response_data = response.json()
            if response_data.get("status") == "OK":
                template.sirius_item_id = response_data.get("data", {}).get("id")
                return True
        except requests.exceptions.RequestException as e:
            raise UserError(f"Failed to send data to the API: {e}")
    def import_transactions(self):
        api_url = "https://gateway-api-srv.stage.bnayax.com/api/transaction-draft-order"
        config = self.env['ir.config_parameter'].sudo()
        token = get_token(config)

        headers = {
            "Authorization": f"Bearer {token.strip()}",
        }
        try:
             response = requests.get(api_url, headers=headers, timeout=30)
             response.raise_for_status()
             response_data = response.json()
             return {"result": "API call successful", "data": response_data}
        except requests.exceptions.RequestException as e:
            print(f"API Request Error: {e}")
            return {"error": str(e)}
        except Exception as e:
            print(f"Unexpected Error: {e}")
            return {"error": str(e)}
       
    def display_notification(self, title, message, notification_type='info'):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': notification_type,
                'sticky': False,
            }
        }
    @api.model
    def test_print_statement(self):
        print("Test cron job: Printing a statement every 30 seconds.")
    def export_all_items(self):
        base_url = "https://gateway-api-srv.stage.bnayax.com/api/export/item"
        config = self.env['ir.config_parameter'].sudo()
        token = get_token(config)

        headers = {
            "Authorization": f"Bearer {token.strip()}",
        }
        self._fetch_and_process_items(f"{base_url}?showModifier=false", headers, is_modifier=False)
        # self._fetch_and_process_items("https://gateway-api-srv.stage.bnayax.com/api/item/modifier/full?page=1&showKiosk=false", headers, is_modifier=True)
        return self.display_notification('Success', 'Complete Export All Items!', 'success')

    def _fetch_and_process_items(self, api_url, headers, is_modifier):
        try:
            response = requests.post(api_url, headers=headers, timeout=30)
            response.raise_for_status()
            response_data = response.json()
            print(f"API Response for {api_url}: {response_data}")

            # Fetch all existing categories at once to avoid repeated lookups
            existing_product_categories = {}
            existing_pos_categories = {}
            product_category_ids = {}
            pos_category_ids = {}
            attribute_values_map = {}

            for item in response_data.get('data', {}).get('responseList', []):
                product_name = item.get('shortDisplayName', 'Unnamed Product')
                sirius_item_id = item.get('id')
                hierarchy1 = item.get('hierarchy1')
                hierarchy2 = item.get('hierarchy2')
                hierarchy3 = item.get('hierarchy3')
                hierarchy4 = item.get('hierarchy4')
                hierarchy5 = item.get('hierarchy5')

                # Fetch categories from the db or create them if not existing
                pos_category_id, product_category_id = self._create_or_update_categories(hierarchy1, hierarchy2, hierarchy3, hierarchy4, hierarchy5,
                                                                                                existing_product_categories, existing_pos_categories,
                                                                                                product_category_ids, pos_category_ids)
                if is_modifier:
                    self._create_or_update_modifier(item, attribute_values_map)

                else:
                    prices = item.get('prices', [])
                    list_price = 0.0 # Set a default list_price if all price are null or no prices
                    if prices:
                        max_price_item = max(prices, key=lambda p: p.get('price', 0.0))
                        max_price = max_price_item.get('price', 0.0)
                        if item.get('isModifier') is True:
                            list_price = max_price
                        else:
                            if max_price > 0.0:
                                tax_rate = 0.17
                                list_price =max_price
                    existing_product = self.env['product.template'].search([('sirius_item_id', '=', sirius_item_id)], limit=1)
                    tax_rate = existing_product.taxes_id.amount if existing_product.taxes_id.amount != 0 else 1  # Default to 1 if tax rate is zero
                    price =max(prices, key=lambda p: p.get('price', 0.0)).get('price', 0.0)- max(prices, key=lambda p: p.get('price', 0.0)).get('price', 0.0) * (tax_rate*.01)
                    
                    print(f"Max price: {max(prices, key=lambda p: p.get('price', 0.0)).get('price', 0.0)}")
                    print(f"Tax rate: {tax_rate}")
                    print(f"Price to subtract: {price}")

                    product_values = {
                         'categ_id': product_category_id,
                        'pos_categ_ids': [(6, 0, [pos_category_id])],
                        'available_in_pos': True,
                        'is_modifier': False,
                        'prices': prices,
                        'list_price':  price,
                        }
                    if not existing_product:
                         product_values.update({
                                'name': product_name,
                                'sirius_item_id': sirius_item_id,
                            })
                         self.env['product.template'].create(product_values)
                    else:
                         existing_product.write(product_values)
        except requests.exceptions.RequestException as e:
            print(f"API Request Error: {e}")
            return {"error": str(e)}
        except Exception as e:
            print(f"Unexpected Error: {e}")
            return {"error": str(e)}
    
    def _create_or_update_categories(self, hierarchy1, hierarchy2, hierarchy3, hierarchy4, hierarchy5, 
                                      existing_product_categories, existing_pos_categories, 
                                      product_category_ids, pos_category_ids):
      """Creates or updates product and POS categories based on the Nayax hierarchy."""
      parent_product_category_id = False
      parent_pos_category_id = False
      categories = [hierarchy1, hierarchy2, hierarchy3, hierarchy4, hierarchy5]
      for category_level in categories:
           if category_level:
               category_name = category_level.get('displayName')
               category_code = category_level.get('code')
               if category_name and category_code:
                # Product Category handling
                product_category_key = (category_code, parent_product_category_id)
                if product_category_key not in product_category_ids:
                    existing_product_category = False
                    # Check if it's not a cached value
                    if category_code not in existing_product_categories:
                        existing_product_category = self.env['product.category'].search([
                            ('nayax_category_code', '=', category_code),
                            ('parent_id', '=', parent_product_category_id or False)], limit=1)
                        if existing_product_category:
                            existing_product_categories[category_code] = existing_product_category.id
                        else:
                            existing_product_categories[category_code] = False

                    if existing_product_categories.get(category_code):
                       parent_product_category_id = existing_product_categories.get(category_code)
                    else:
                        new_product_category = self.env['product.category'].create({
                            'name': category_name,
                            'nayax_category_code': category_code,
                            'parent_id': parent_product_category_id or False,
                        })
                        parent_product_category_id = new_product_category.id
                        existing_product_categories[category_code] = new_product_category.id
                    product_category_ids[product_category_key] = parent_product_category_id
                else:
                   parent_product_category_id = product_category_ids[product_category_key]
                
                # POS Category handling
                pos_category_key = (category_code, parent_pos_category_id)
                if pos_category_key not in pos_category_ids:
                   existing_pos_category = False
                   if category_code not in existing_pos_categories:
                       existing_pos_category = self.env['pos.category'].search([
                            ('nayax_category_code', '=', category_code),
                            ('parent_id', '=', parent_pos_category_id or False)], limit=1)
                       if existing_pos_category:
                           existing_pos_categories[category_code] = existing_pos_category.id
                       else:
                           existing_pos_categories[category_code] = False
                   if existing_pos_categories.get(category_code):
                       parent_pos_category_id = existing_pos_categories.get(category_code)
                       print(f"POS Category {category_name} Code: {category_code} already exists. Setting its as Parent for next level")
                   else:
                        new_pos_category = self.env['pos.category'].create({
                            'name': category_name,
                            'nayax_category_code': category_code,
                            'parent_id': parent_pos_category_id or False,
                        })
                        parent_pos_category_id = new_pos_category.id
                        existing_pos_categories[category_code] = new_pos_category.id
                        print(f"POS Category {category_name} Code: {category_code} created. Set it as Parent for next level")
                   pos_category_ids[pos_category_key] = parent_pos_category_id
                else:
                    parent_pos_category_id = pos_category_ids[pos_category_key]
      return parent_pos_category_id, parent_product_category_id

    def _create_or_update_modifier(self, item, attribute_values_map):
        modifier_name = item.get('shortDisplayName', 'Unnamed Modifier')
        sirius_item_id = item.get('id')
        prices = item.get('prices', [])
        if prices:
           price = max(prices, key=lambda p: p.get('price', 0.0)).get('price', 0.0)
        else:
            price = 0.0
        print(f"Processing price: {price}")
        # Create or update the attribute
        attribute = self.env['product.attribute'].search([('name', '=', 'Sirius Attributes')], limit=1)
        if not attribute:
            attribute = self.env['product.attribute'].create({
                'name': 'Sirius Attributes',
                'display_type': 'multi',
                'create_variant': 'no_variant',
            })
        # Create or update the attribute value
        attr_val_key = (attribute.id, modifier_name, price, sirius_item_id)
        if attr_val_key not in attribute_values_map:
             existing_value = self.env['product.attribute.value'].search([
                    ('attribute_id', '=', attribute.id),
                    ('name', '=', modifier_name),
                    ('default_extra_price', '=', price),
                    ('sirius_item_id', '=',sirius_item_id),

                ], limit=1)
             if not existing_value:
                new_value = self.env['product.attribute.value'].create({
                    'attribute_id': attribute.id,
                    'name': modifier_name,
                    'default_extra_price': price,
                    'sirius_item_id' :sirius_item_id
                    })
                attribute_values_map[attr_val_key] = new_value.id
                print(f"Created new modifier attribute value: {modifier_name}")
             else:
                  attribute_values_map[attr_val_key] = existing_value.id
                  print(f"modifier attribute value: {modifier_name} already exists.")
    #the shcedule export items with print statements (Rami)
    @api.model
    def _scheduler_export_all_items(self):
        print("Scheduled job: starting export all items.")
        self.export_all_items()
        print("Scheduled job: finished export all items.")

    def _fetch_and_process_modifiers_full(self, headers):
        api_url = "https://gateway-api-srv.stage.bnayax.com/api/item/modifier/full"
        try:
            response = requests.get(api_url, headers=headers, timeout=30)
            response.raise_for_status()
            response_data = response.json()
            print(f"API Response for Modifier Full: {response_data}")

            if response_data and response_data.get('data') and response_data.get('data').get('responseList'):
                for response_item in response_data.get('data').get('responseList'):
                    for modifier_group in response_item.get('groups', []):
                        self._create_or_update_modifier_group(modifier_group)
        except requests.exceptions.RequestException as e:
            print(f"API Request Error: {e}")
            return {"error": str(e)}
        except Exception as e:
            print(f"Unexpected Error: {e}")
            return {"error": str(e)}
    def _create_or_update_modifier_group(self, modifier_group_data):
        print(modifier_group_data)
        group_name = modifier_group_data.get('displayName')
        group_id = modifier_group_data.get('id')
        sirius_item_id = modifier_group_data.get('itemId')
        print(f'Processing Modifier Group: {group_name}')

        # Create or update the attribute
        attribute = self.env['product.attribute'].search([('name', '=', group_name)], limit=1)
        if not attribute:
            attribute = self.env['product.attribute'].create({
                'name': group_name,
                'display_type': 'multi',
                'create_variant': 'no_variant',
                'sirius_group_id': group_id
            })
        else:
            attribute.write({'sirius_group_id': group_id})
        product = self.env['product.template'].search([('sirius_item_id', '=', sirius_item_id)], limit=1)
        if not product:
             print(f"Product with sirius_item_id: {sirius_item_id} not found.")
             return
        attribute_value_ids = [] # To collect the ids of the attribute values we create or update
        for item_modifier in modifier_group_data.get('itemModifiers', []):
            modifier_name = item_modifier.get('itemName')
            sirius_item_id_line = item_modifier.get('itemId')
            line_product = self.env['product.template'].search([('sirius_item_id', '=', sirius_item_id_line)], limit=1)
            if not line_product:
                print(f"Product with sirius_item_id: {sirius_item_id_line} not found.")
                continue
            print(line_product.list_price)
            existing_value = self.env['product.attribute.value'].search([
                ('attribute_id', '=', attribute.id),
                ('name', '=', modifier_name),
                ('sirius_item_id', '=', sirius_item_id_line)
            ], limit=1)
            if not existing_value:
                new_value = self.env['product.attribute.value'].create({
                    'attribute_id': attribute.id,
                    'name': modifier_name,
                    'default_extra_price': line_product.list_price,
                    'sirius_item_id': sirius_item_id_line
                })
                attribute_value_ids.append(new_value.id)
                print(f"Created new modifier attribute value: {modifier_name} for group: {group_name}")
            else:
                existing_value.write({
                'default_extra_price': line_product.list_price,
                'sirius_item_id': sirius_item_id_line,
                })
                attribute_value_ids.append(existing_value.id)
                print(f"Modifier attribute value: {modifier_name} for group: {group_name} already exists. Updated Price and sirius id")
        existing_line = self.env['product.template.attribute.line'].search([
            ('product_tmpl_id', '=', product.id),
            ('attribute_id', '=', attribute.id)
        ], limit=1)
        if not existing_line:
            self.env['product.template.attribute.line'].create({
                'product_tmpl_id': product.id,
                'attribute_id': attribute.id,
                'value_ids': [(6, 0, attribute_value_ids)], # Add all available values of this attribute
            })
            print(f"Added attribute {group_name} to product: {product.id}")
        else:
            existing_line.write({
                'value_ids': [(4, val_id) for val_id in attribute_value_ids] # only add the value that we just created or updated
                })
            print(f"Attribute {group_name} already exists for product: {product.name}, updated values")

    def export_all_modifiers(self):
        config = self.env['ir.config_parameter'].sudo()
        token = get_token(config)
        headers = {
            "Authorization": f"Bearer {token.strip()}",
        }
        self._fetch_and_process_modifiers_full(headers)
        return self.display_notification('Success', 'Complete Export All Modifiers!', 'success')

    @api.model
    def _scheduler_export_all_items(self):
        print("Scheduled job: starting export all items.")
        self.export_all_items()
        print("Scheduled job: finished export all items.")