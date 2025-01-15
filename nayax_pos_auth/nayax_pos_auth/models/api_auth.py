import json

from build import _logger
from odoo import models, fields, api
import requests
from odoo.addons.nayax_pos_auth.crypto_utils import decrypt_data, encrypt_data, generate_key, get_token
from odoo.exceptions import UserError
from cryptography.fernet import Fernet

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
        """
        Handle the API authentication process when the button is clicked.
        """
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
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('status') == 'OK' and response_data.get('data'):
                    data = response_data['data']
                    access_token = data.get('accessToken')
                    refresh_token = data.get('refreshToken')
                    session_id = data.get('sessionId')
                    companies = data.get('companies', [])
                    company_names = [company.get('name') for company in companies]

                    # Print data before encryption
                    print(f"Access token: {access_token}")
                    print(f"Refresh token: {refresh_token}")
                    print(f"Session ID: {session_id}")
                    print(f"Company names: {company_names}")

                    # Encrypt tokens before storing them
                    encrypted_access_token = encrypt_data(access_token, secret_key)
                    encrypted_refresh_token = encrypt_data(refresh_token, secret_key)
                    encrypted_session_id = encrypt_data(session_id, secret_key)
                    encrypted_companies = encrypt_data(json.dumps(company_names), secret_key)
                    encrypted_username = encrypt_data(self.login, secret_key)  # Encrypt username
                    encrypted_password = encrypt_data(self.password, secret_key)  # Encrypt password

                    # Save encrypted tokens and session details in ir.config_parameter for global access
                    config.set_param('external_access_token', encrypted_access_token)
                    config.set_param('external_refresh_token', encrypted_refresh_token)
                    config.set_param('external_session_id', encrypted_session_id)
                    config.set_param('external_companies', encrypted_companies)
                    config.set_param('external_username', encrypted_username)  # Save encrypted username
                    config.set_param('external_password', encrypted_password)  # Save encrypted password

                    print(self.get_decrypted_tokens())  # Print decrypted tokens to verify

                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Login Successful',
                            'message': f'Welcome, {data.get("firstName")} {data.get("lastName")}',
                            'type': 'success',
                            'sticky': False,
                        },
                    }
                else:
                    self.clear_sensitive_data(config)

                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Error',
                            'message': 'Unexpected response format.',
                            'type': 'danger',
                            'sticky': False,
                        },
                    }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Login Failed',
                        'message': response.json().get('message', 'Login failed!'),
                        'type': 'danger',
                        'sticky': False,
                    },
                }
        except requests.RequestException as e:
            self.clear_sensitive_data(config)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': f'API Request failed: {str(e)}',
                    'type': 'danger',
                    'sticky': False,
                },
            }

    def clear_sensitive_data(self, config):
        """
        Clear sensitive data from ir.config_parameter.
        """
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
                    config.set_param(key, '')  # Set value to empty string
                    _logger.info(f"Cleared key: {key}")
                except Exception as e:
                    _logger.warning(f"Failed to clear key {key}: {e}")




    def get_decrypted_tokens(self):
        """
        Retrieve and decrypt stored tokens from the ir.config_parameter table.
        """
        secret_key = generate_key()  # Use the same key for decryption
        config = self.env['ir.config_parameter'].sudo()

        encrypted_access_token = config.get_param('external_access_token')
        encrypted_refresh_token = config.get_param('external_refresh_token')
        encrypted_session_id = config.get_param('external_session_id')
        encrypted_companies = config.get_param('external_companies')

        access_token = decrypt_data(encrypted_access_token, secret_key)
        refresh_token = decrypt_data(encrypted_refresh_token, secret_key)
        session_id = decrypt_data(encrypted_session_id, secret_key)
        company_names = json.loads(decrypt_data(encrypted_companies, secret_key))

        return access_token, refresh_token, session_id, company_names


    def send_all_products_to_api(self):
        """
        Send all product.template objects to the API using the _send_to_api method.
        """
        products = self.env['product.template'].search([('sent_to_api', '=', False)])  # Fetch all product records
        if not products:
           return  
        config = self.env['ir.config_parameter'].sudo()
        #self.env['api.auth'].search([], order="id desc", limit=1)
        token = get_token(config)

        for product in products:
            if self.export_item(product):
                product.write({'sent_to_api': True})  # Update the field in the database
        return self.display_notification('Success', 'Complete Export All Products!', 'success')

    def export_item(self, template):
        api_url = "https://gateway-api-srv.stage.bnayax.com/api/item"
        config = self.env['ir.config_parameter'].sudo()
        #self.env['api.auth'].search([], order="id desc", limit=1)
        token = get_token(config)

        # Now we can safely strip the token
        headers = {
            "Authorization": f"Bearer {token.strip()}",  # Only call strip if token is valid
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

            # Send the POST request
        try:
                print(f"Debug: Sending request for template ID: {template.id}")

                response = requests.post(api_url, json=payload, headers=headers)
                response.raise_for_status()  # Raise exception for HTTP errors
                print(f"Debug: Request sent successfully for template ID {template.id}.")
                print(f"Debug: Response: {response.json()}")

                response_data = response.json()

                if response_data.get("status") == "OK":
                    template.sirius_item_id = response_data.get("data", {}).get("id")
                    return True  # Indicate success


        except requests.exceptions.RequestException as e:
                raise UserError(f"Failed to send data to the API: {e}")
        

    def import_transactions(self):
        api_url = "https://gateway-api-srv.stage.bnayax.com/api/transaction-draft-order"

        config = self.env['ir.config_parameter'].sudo()
        #self.env['api.auth'].search([], order="id desc", limit=1)
        token = get_token(config)

        headers = {
            "Authorization": f"Bearer {token.strip()}",
        }

        try:
            response = requests.get(api_url, headers=headers, timeout=30)
            response.raise_for_status()
            response_data = response.json()
            # print(f"API Response: {response_data}") # Log the full response for debugging
            return {"result": "API call successful", "data": response_data} # Return something other than false

        except requests.exceptions.RequestException as e:
            print(f"API Request Error: {e}")
            return {"error": str(e)}
        except Exception as e:
            print(f"Unexpected Error: {e}")
            return {"error": str(e)}
       
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
            }
        }

    
 
    def export_all_items(self):
        """
        Fetches items and modifiers from the API and creates/updates records in Odoo.
        """
        base_url = "https://gateway-api-srv.stage.bnayax.com/api/export/item"
        config = self.env['ir.config_parameter'].sudo()
        token = get_token(config)

        headers = {
            "Authorization": f"Bearer {token.strip()}",
        }
        # Fetch regular items
        self._fetch_and_process_items(f"{base_url}?showModifier=false&size=20", headers, is_modifier=False)

        # Fetch modifiers
        # self._fetch_and_process_items(f"{base_url}?showModifier=true&size=20", headers, is_modifier=True)
        return self.display_notification('Success', 'Complete Export All Items!', 'success')


    def _fetch_and_process_items(self, api_url, headers, is_modifier):
            try:
                response = requests.post(api_url, headers=headers, timeout=30)
                response.raise_for_status()
                response_data = response.json()
                print(f"API Response for {api_url}: {response_data}")


                for item in response_data.get('data', {}).get('responseList', []):
                    product_name = item.get('shortDisplayName', 'Unnamed Product')
                    prices = item.get('prices', [])

                    sirius_item_id = item.get('id')
                    hierarchy1 = item.get('hierarchy1')
                    hierarchy2 = item.get('hierarchy2')
                    hierarchy3 = item.get('hierarchy3')
                    hierarchy4 = item.get('hierarchy4')
                    hierarchy5 = item.get('hierarchy5')

                    
                    pos_category_id, product_category_id = self._create_or_update_categories(hierarchy1, hierarchy2, hierarchy3, hierarchy4, hierarchy5)
                    
                    if is_modifier:
                        self._create_or_update_modifier(item)
                    else:
                        existing_product = self.env['product.template'].search([('sirius_item_id', '=', sirius_item_id)], limit=1)

                        if not existing_product:
                            
                            # Handle prices by creating an attribute and values
                            price_attribute_id = self._create_price_attribute(prices, product_name)

                            product_values = {
                                'name': product_name,
                                'sirius_item_id': sirius_item_id,
                                'categ_id': product_category_id,
                                'pos_categ_ids': [(6, 0, [pos_category_id])],
                                'available_in_pos': True,
                                'is_modifier': False,  
                                 'prices': prices,
                            }
                             # Add the attribute and its values to the product if it exists
                            if price_attribute_id:
                                product_values['attribute_line_ids'] = [(0, 0, {
                                'attribute_id': price_attribute_id,
                                'value_ids': [(6, 0, [val.id for val in self.env['product.attribute.value'].search([('attribute_id', '=', price_attribute_id)])])],
                            })]
                            self.env['product.template'].create(product_values)
                            print(f"Created product {product_name} with ID {sirius_item_id} and POS Category: {pos_category_id} and product Category: {product_category_id} and price attribute {price_attribute_id}")
                        
                        else:
                            price_attribute_id = self._create_price_attribute(prices, product_name)
                            product_values = {
                                'categ_id': product_category_id,
                                'pos_categ_ids': [(6, 0, [pos_category_id])],
                                'available_in_pos': True,
                                'is_modifier': False,
                                'prices': prices,
                                }
                            if price_attribute_id:
                                product_values['attribute_line_ids'] = [(0, 0, {
                                    'attribute_id': price_attribute_id,
                                    'value_ids': [(6, 0, [val.id for val in self.env['product.attribute.value'].search([('attribute_id', '=', price_attribute_id)])])],
                            })]
                            existing_product.write(product_values)
                            print(f"Product with sirius_item_id {sirius_item_id} already exists. Updating Category to {pos_category_id} and making it available in POS and Price Attribute if not exists {price_attribute_id}")

            except requests.exceptions.RequestException as e:
                print(f"API Request Error: {e}")
                return {"error": str(e)}
            except Exception as e:
                print(f"Unexpected Error: {e}")
                return {"error": str(e)}

    def _create_price_attribute(self, prices, product_name):
            if not prices:
                return False  # No prices, no attribute needed

            attribute_name = f"{product_name} Prices"
            attribute = self.env['product.attribute'].search([('name', '=', attribute_name)], limit=1)

            if not attribute:
                attribute = self.env['product.attribute'].create({
                    'name': attribute_name,
                    'display_type': 'pills',  # Use pills display
                    'create_variant': 'no_variant',
                })

            for price_data in prices:
                price_value = price_data.get('price', 0.0)
                existing_value = self.env['product.attribute.value'].search([('attribute_id', '=', attribute.id), ('name', '=', str(price_value))], limit=1)

                if not existing_value:
                    self.env['product.attribute.value'].create({
                        'attribute_id': attribute.id,
                        'name': str(price_value),
                    })
            return attribute.id

    def _create_or_update_categories(self, hierarchy1, hierarchy2, hierarchy3, hierarchy4, hierarchy5):
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
                    existing_product_category = self.env['product.category'].search([
                        ('nayax_category_code', '=', category_code),
                        ('parent_id', '=', parent_product_category_id or False)], limit=1)

                    if existing_product_category:
                       parent_product_category_id = existing_product_category.id
                    else:
                       new_product_category = self.env['product.category'].create({
                           'name': category_name,
                           'nayax_category_code': category_code,
                            'parent_id': parent_product_category_id or False,
                       })
                       parent_product_category_id = new_product_category.id


                    # POS Category handling
                    existing_pos_category = self.env['pos.category'].search([
                        ('nayax_category_code', '=', category_code),
                        ('parent_id', '=', parent_pos_category_id or False)], limit=1)

                    if existing_pos_category:
                       parent_pos_category_id = existing_pos_category.id
                       print(f"POS Category {category_name} Code: {category_code} already exists. Setting its as Parent for next level")
                    else:
                       new_pos_category = self.env['pos.category'].create({
                            'name': category_name,
                            'nayax_category_code': category_code,
                            'parent_id': parent_pos_category_id or False,
                           
                        })
                       parent_pos_category_id = new_pos_category.id
                       print(f"POS Category {category_name} Code: {category_code} created. Set it as Parent for next level")

        return parent_pos_category_id, parent_product_category_id
    
    def _create_or_update_modifier(self, item):
            """Creates or updates product attributes and values for modifiers."""
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
                    'display_type': 'multi-checkbox',
                    'create_variant': 'no_variant',
                })


            # Create or update the attribute value
            existing_value = self.env['product.attribute.value'].search([
                    ('attribute_id', '=', attribute.id),
                    ('name', '=', modifier_name),
                    ('default_extra_price', '=', price),
                    ('sirius_item_id', '=',sirius_item_id),

            ], limit=1)
            if not existing_value:
                self.env['product.attribute.value'].create({
                    'attribute_id': attribute.id,
                    'name': modifier_name,
                    'default_extra_price': price,
                    'sirius_item_id' :sirius_item_id


                })
                print(f"Created new modifier attribute value: {modifier_name}")

            else:
                print(f"modifier attribute value: {modifier_name} already exists.")




















































        # def export_all_hierarchy(self):
    #     api_url = f"https://gateway-api-srv.stage.bnayax.com/api/item/hierarchy4"
    #     auth_record = self.env['api.auth'].search([], order="id desc", limit=1)

    #     if not auth_record or not auth_record.auth_status:
    #            return self.display_notification('Error', "Please Login first.", 'danger')


    #     headers = {
    #         "Authorization": f"Bearer {auth_record.token.strip()}",
    #     }

    #     try:
    #                 response = requests.get(api_url, headers=headers, timeout=30)
    #                 response.raise_for_status()  # This will raise an error for non-2xx responses
    #                 response_data = response.json()
    #                 print(f"API Response: {response_data}")  # Log the full response for debugging

    #                 # Loop through each item in the response
    #                 for item in response_data['data']['responseList']:
    #                     category_code = item['code']
    #                     category_name = item['displayName']
    #                     category_ID = item['id']
    #                     category_dependency = item['dependency']
    #                     parent_id = None  
    #                     if len(category_dependency) == 1:
    #                         dependency_id = category_dependency.get("1")  # Get the dependency from the dictionary
    #                         # Find the parent category by matching `sirius_category_ID`
    #                         parent_category = self.env['product.category'].search([('sirius_category_ID', '=', dependency_id), ('sirius_category_level', '=', 1)], limit=1)
    #                         if parent_category:
    #                             parent_id = parent_category.id  # Set the parent_id if a matching parent category is found

    #                     if len(category_dependency) == 2:
    #                         dependency_id = category_dependency.get("2")  # Get the dependency from the dictionary
    #                         # Find the parent category by matching `sirius_category_ID`
    #                         parent_category = self.env['product.category'].search([('sirius_category_ID', '=', dependency_id), ('sirius_category_level', '=', 2)], limit=1)
    #                         if parent_category:
    #                             parent_id = parent_category.id  # Set the parent_id if a matching parent category is found

    #                     if len(category_dependency) == 3:
    #                         dependency_id = category_dependency.get("3")  # Get the dependency from the dictionary
    #                         # Find the parent category by matching `sirius_category_ID`
    #                         parent_category = self.env['product.category'].search([('sirius_category_ID', '=', dependency_id), ('sirius_category_level', '=', 3)], limit=1)
    #                         if parent_category:
    #                             parent_id = parent_category.id  # Set the parent_id if a matching parent category is found


    #                         # Create a new product category if it doesn't exist
    #                     self.env['product.category'].create({
    #                             'name': category_name,
    #                             'sirius_category_code': category_code,
    #                             'sirius_category_ID': category_ID,
    #                             'sirius_category_level' :len(category_dependency)+1,
    #                              'parent_id': parent_id,  # Set the parent_id here

    #                         })
    #                     print(f"Created new category: {category_name} with code {category_code}")
           

    #     except requests.exceptions.RequestException as e:
    #         print(f"API Request Error: {e}")
    #         return {"error": str(e)}

       # def export_all_items(self):


    #     api_url = "https://gateway-api-srv.stage.bnayax.com/api/export/item?size=22"
    #     auth_record = self.env['api.auth'].search([], order="id desc", limit=1)

    #     if not auth_record or not auth_record.auth_status:
    #            return self.display_notification('Error', "Please Login first.", 'danger')


    #     headers = {
    #         "Authorization": f"Bearer {auth_record.token.strip()}",
    #     }

    #     try:
    #         response = requests.post(api_url, headers=headers, timeout=30)
    #         response.raise_for_status()  # This will raise an error for non-2xx responses
    #         response_data = response.json()
    #         print(f"API Response: {response_data}")  # Log the full response for debugging

    #         # Loop through the response list and create product.template records
    #         for item in response_data.get('data', {}).get('responseList', []):
    #             product_name = item.get('shortDisplayName', 'Unnamed Product')
    #             prices = item.get('prices', [])
                
    #             # Check if prices exist and select the highest price
    #             if prices:
    #                 # Select the price with the maximum value
    #                 price = max(prices, key=lambda p: p.get('price', 0.0)).get('price', 0.0)
    #             else:
    #                 price = 0.0  # Default price if no price is available

    #             sirius_item_id = item.get('id')
    #             # hierarchy1 = item.get('hierarchy1')
    #             # hierarchy2 = item.get('hierarchy2')
    #             # hierarchy3 = item.get('hierarchy3')
    #             # hierarchy4 = item.get('hierarchy4')
    #             # hierarchy5 = item.get('hierarchy5')

    #             # Create or update the product.template record
    #             existing_product = self.env['product.template'].search([('sirius_item_id', '=', sirius_item_id)], limit=1)

    #             if not existing_product:
    #                 # Create the product.template record
    #                 self.env['product.template'].create({
    #                     'name': product_name,
    #                     'list_price': price,
    #                     'sirius_item_id': sirius_item_id,
    #                     # 'hierarchy1': hierarchy1,
    #                     # 'hierarchy2': hierarchy2,
    #                     # 'hierarchy3': hierarchy3,
    #                     # 'hierarchy4': hierarchy4,
    #                     # 'hierarchy5': hierarchy5,
    #                     'prices': prices  # Store all prices if needed
    #                 })
    #                 print(f"Created product {product_name} with ID {sirius_item_id}")
    #             else:
    #                 print(f"Product with sirius_item_id {sirius_item_id} already exists. Skipping.")

    #     except requests.exceptions.RequestException as e:
    #         print(f"API Request Error: {e}")
    #         return {"error": str(e)}
    #     except Exception as e:
    #         print(f"Unexpected Error: {e}")
    #         return {"error": str(e)}