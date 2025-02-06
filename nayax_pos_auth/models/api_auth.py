import base64
import datetime
from datetime import timezone
import json
from odoo import models, fields, api
import requests
from odoo.addons.nayax_pos_auth.crypto_utils import decrypt_data, encrypt_data, generate_key, get_token
from odoo.exceptions import UserError
from odoo import _
import logging
_logger = logging.getLogger(__name__)


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
                    _logger.info(f"Access token: {access_token}")
                    _logger.info(f"Refresh token: {refresh_token}")
                    _logger.info(f"Session ID: {session_id}")
                    _logger.info(f"Company names: {company_names}")

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

                    _logger.info(f"Decrypted Tokens: {self.get_decrypted_tokens()}")  # Print decrypted tokens to verify

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
        # self.env['api.auth'].search([], order="id desc", limit=1)
        token = get_token(config)

        exported_product_ids = []
        for product in products:
            if self.export_item(product):
                exported_product_ids.append(product.id)  # Collect exported product IDs

        if exported_product_ids:
            # Update all exported products at once using write on the records
            self.env['product.template'].browse(exported_product_ids).write({'sent_to_api': True})

        return self.display_notification('Success', 'Complete Export All Products!', 'success')

    @api.model
    def export_item(self, template):
        api_url = "https://gateway-api-srv.stage.bnayax.com/api/item"
        config = self.env['ir.config_parameter'].sudo()
        # self.env['api.auth'].search([], order="id desc", limit=1)
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

        _logger.debug(f"Payload for template ID {template.id}: {payload}")

        # Send the POST request
        try:
            _logger.debug(f"Sending request for template ID: {template.id}")

            response = requests.post(api_url, json=payload, headers=headers)
            response.raise_for_status()  # Raise exception for HTTP errors
            _logger.debug(f"Request sent successfully for template ID {template.id}.")
            _logger.debug(f"Response: {response.json()}")

            response_data = response.json()

            if response_data.get("status") == "OK":
                template.sirius_item_id = response_data.get("data", {}).get("id")
                return True  # Indicate success


        except requests.exceptions.RequestException as e:
           _logger.error(f"Failed to send data to the API: {e}")
           raise UserError(f"Failed to send data to the API: {e}")

    def import_transactions(self):
        # Get the current company
        company_id = self.env.company.id
        
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
            
            # Process the data with company filtering
            for item in response_data.get('data', []):
                # Add company_id to the item data
                item['company_id'] = company_id
                
            return {"result": "API call successful", "data": response_data}
            
        except requests.exceptions.RequestException as e:
            _logger.error(f"API Request Error: {e}")
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

    @api.model
    def _store_image_in_attachment_action(self, image_url, product_id):
        """Helper method to store or update an image from a URL as attachments with different resolutions."""
        try:
            if not image_url:
                _logger.warning("No image URL provided.")
                return

            # Download the image
            image_response = requests.get(image_url, timeout=10)
            image_response.raise_for_status()
            image_data = base64.b64encode(image_response.content)

            # Ensure image data exists
            if not image_data:
                _logger.warning("No image data retrieved from the URL.")
                return

            # Define the resolutions and their corresponding names
            resolutions = ['image_1920', 'image_1024', 'image_512', 'image_256', 'image_128']

            for resolution in resolutions:
                # Check if the attachment already exists
                existing_attachment = self.env['ir.attachment'].search([
                    ('res_model', '=', 'product.template'),
                    ('res_id', '=', product_id),
                    ('res_field', '=', resolution),
                ], limit=1)

                if existing_attachment:
                    # Update the existing attachment
                    existing_attachment.write({
                        'datas': image_data,
                        'mimetype': 'image/png',  # Adjust if the format is different
                    })
                    _logger.info(f"Updated image in ir.attachment for product ID {product_id} with resolution {resolution}")
                else:
                    # Create a new attachment if not found
                    self.env['ir.attachment'].create({
                        'name': resolution,
                        'type': 'binary',
                        'datas': image_data,
                        'res_model': 'product.template',
                        'res_id': product_id,
                        'res_field': resolution,  # Field matches the resolution name
                        'mimetype': 'image/png',  # Adjust if the format is different
                    })
                    _logger.info(f"Image stored in ir.attachment for product ID {product_id} with resolution {resolution}")

        except requests.exceptions.RequestException as e:
            _logger.error(f"Error downloading image: {e}")
        except TypeError as e:
            _logger.error(f"TypeError: {e} - Check if all objects are iterable.")
        except Exception as e:
           _logger.error(f"Unexpected error while storing image: {e}")

    @api.model
    def _create_or_update_categories_action(self, hierarchy1, hierarchy2, hierarchy3, hierarchy4, hierarchy5, company_id):
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
                            'company_id': company_id,  # Set company_id on product category
                        })
                        parent_product_category_id = new_product_category.id

                    # POS Category handling
                    existing_pos_category = self.env['pos.category'].search([
                        ('nayax_category_code', '=', category_code),
                        ('parent_id', '=', parent_pos_category_id or False)], limit=1)

                    if existing_pos_category:
                        parent_pos_category_id = existing_pos_category.id
                        _logger.info(
                            f"POS Category {category_name} Code: {category_code} already exists. Setting its as Parent for next level")
                    else:
                        new_pos_category = self.env['pos.category'].create({
                            'name': category_name,
                            'nayax_category_code': category_code,
                            'parent_id': parent_pos_category_id or False,
                            'company_id': company_id, #Set company_id on POS Category
                        })
                        parent_pos_category_id = new_pos_category.id
                        _logger.info(
                            f"POS Category {category_name} Code: {category_code} created. Set it as Parent for next level")

        return parent_pos_category_id, parent_product_category_id

    @api.model
    def _create_or_update_modifier_action(self, item, list_price):
        """Creates or updates product attributes and values for modifiers."""
        modifier_name = item.get('shortDisplayName', 'Unnamed Modifier')
        sirius_item_id = item.get('id')
        _logger.info('***********************')

        # Create or update the attribute
        attribute = self.env['product.attribute'].search([('name', '=', 'Sirius Attributes')], limit=1)
        if not attribute:
            attribute = self.env['product.attribute'].create({
                'name': 'Sirius Attributes',
                'display_type': 'multi',
                'create_variant': 'no_variant',
            })

        # Create or update the attribute value
        existing_value = self.env['product.attribute.value'].search([
            ('attribute_id', '=', attribute.id),
            ('name', '=', modifier_name),
            ('default_extra_price', '=', list_price),
            ('sirius_item_id', '=', sirius_item_id),

        ], limit=1)
        if not existing_value:
            self.env['product.attribute.value'].create({
                'attribute_id': attribute.id,
                'name': modifier_name,
                'default_extra_price': list_price,
                'sirius_item_id': sirius_item_id

            })
            _logger.info(f"Created new modifier attribute value: {modifier_name}")

        else:
            _logger.info(f"modifier attribute value: {modifier_name} already exists.")

    @api.model
    def _create_or_update_modifier_group_action(self, modifier_group_data, company_id):
        """
        Creates or updates product attributes and values for modifiers groups.
        """
        _logger.debug(modifier_group_data)
        group_name = modifier_group_data.get('displayName')
        group_id = modifier_group_data.get('id')
        is_single_selection = modifier_group_data.get('isAllowOnlyOneSelection', False)
        display_type = 'pills' if is_single_selection else 'multi'

        _logger.info(f'Processing Modifier Group: {group_name}')

        # Create or update the attribute
        attribute = self.env['product.attribute'].search([('name', '=', group_name)], limit=1)
        if not attribute:
            attribute = self.env['product.attribute'].create({
                'name': group_name,
                'display_type': display_type,
                'create_variant': 'no_variant',
                'sirius_group_id': group_id
            })
        else:
            # Update the attribute if it already exists
            attribute.write({
                'sirius_group_id': group_id,
                'display_type': display_type
            })
        sirius_item_id = modifier_group_data.get('itemId')
    
        product = self.env['product.template'].search([('sirius_item_id', '=', sirius_item_id)], limit=1)
        _logger.info('*****************************************************')

        _logger.info(sirius_item_id)
        
        attribute_value_ids = [] # Initialize a list to store all attribute value ids for this group
        for item_modifier in modifier_group_data.get('itemModifiers', []):
            modifier_name = item_modifier.get('itemName')
            sirius_item_id_line = item_modifier.get('itemId')
            line_product = self.env['product.template'].search([('sirius_item_id', '=', sirius_item_id_line)], limit=1)
            # print('*****************************************************')

            _logger.info(line_product.list_price)
            # Create or update attribute values for the modifiers
            
            existing_value = self.env['product.attribute.value'].search([
                ('attribute_id', '=', attribute.id),
                ('name', '=', modifier_name),
                ('default_extra_price', '=', line_product.list_price),
                ('sirius_item_id', '=', sirius_item_id_line)
            ], limit=1)

            if not existing_value:
                new_value = self.env['product.attribute.value'].create({
                    'attribute_id': attribute.id,
                    'name': modifier_name,
                    'default_extra_price': line_product.list_price,
                    'sirius_item_id': sirius_item_id_line
                })
                attribute_value_ids.append(new_value.id)  #Add new attribute value id to the list
                _logger.info(f"Created new modifier attribute value: {modifier_name} for group: {group_name}")
            else:
                attribute_value_ids.append(existing_value.id) # Add existing attribute value id to the list
                _logger.info(f"Modifier attribute value: {modifier_name} for group: {group_name} already exists.")

        if product:
              # Check if the attribute line already exists
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
                   _logger.info(f"Added attribute {group_name} to product: {product.name}")
                else:
                    # Update existing line's value_ids to include all available values
                    existing_line.write({'value_ids': [(6, 0, attribute_value_ids)]})
                    _logger.info(f"Attribute {group_name} already exists for product: {product.name}. Updated values")

    def export_all_items(self):
        """
        Fetches items and modifiers from the API and creates/updates records in Odoo.
        """
        # Get the current company
        company_id = self.env.company.id

        base_url = "https://gateway-api-srv.stage.bnayax.com/api/export/item"
        config = self.env['ir.config_parameter'].sudo()
        token = get_token(config)

        headers = {
            "Authorization": f"Bearer {token.strip()}",
        }

        # Get the last update date from the config
        last_update_date_str = config.get_param('bnayax_api.items_last_update', default=False)

        if not last_update_date_str:
            # First time fetching items
            self._fetch_and_process_items(f"{base_url}", headers, is_modifier=False, company_id=company_id)
            # Set the last update time
            now = datetime.datetime.now(timezone.utc)
            config.set_param('bnayax_api.items_last_update', now.strftime("%Y-%m-%dT%H:%M:%S%z"))
            _logger.info("First time items update finished")
        else:
            # Fetch updated items incrementally by day
            last_update_date = datetime.datetime.strptime(last_update_date_str, "%Y-%m-%dT%H:%M:%S%z")
            now = datetime.datetime.now(timezone.utc)
            current_date = last_update_date.date()
            while current_date <= now.date():
                # Construct a datetime object for the start of the current day
                update_date = datetime.datetime.combine(current_date, datetime.time.min).replace(tzinfo=timezone.utc)
                update_date_str = update_date.strftime("%Y-%m-%d") + 'T00%3A00%3A00%2B03%3A00'    
                _logger.info(f"Fetching items updated on: {update_date_str}")
                self._fetch_and_process_items(f"{base_url}?updateDate={update_date_str}", headers, is_modifier=False, company_id=company_id)
                current_date += datetime.timedelta(days=1)
            
            # Set the last update time
            config.set_param('bnayax_api.items_last_update', now.strftime("%Y-%m-%dT%H:%M:%S%z"))
            _logger.info("Regular items update finished")
        
        return self.display_notification('Success', 'Complete Export All Items!', 'success')
#mariel - updated here to check if there is image to call the _store_image_in_attachment method
    def _fetch_and_process_items(self, api_url, headers, is_modifier, company_id):
        try:
            # API Request
            response = requests.post(api_url, headers=headers, timeout=30)
            response.raise_for_status()
            response_data = response.json()
            _logger.debug(f"API Response for {api_url}: {response_data}")

            if response_data and response_data.get('data') and response_data.get('data').get('responseList'):
                # Get the list of Sirius IDs we want to keep
                wanted_sirius_ids = set(self.env['product.template'].search([('sirius_item_id', '!=', False)]).mapped('sirius_item_id'))

                # Filter the API response *before* processing
                filtered_items = [item for item in response_data['data']['responseList']
                                if item.get('id') in wanted_sirius_ids]

                for item in filtered_items:
                    # Extract product details
                    product_name = item.get('shortDisplayName', 'Unnamed Product')
                    sirius_item_id = item.get('id')
                    siriues_item_code = item.get('code')
                    hierarchy1 = item.get('hierarchy1')
                    hierarchy2 = item.get('hierarchy2')
                    hierarchy3 = item.get('hierarchy3')
                    hierarchy4 = item.get('hierarchy4')
                    hierarchy5 = item.get('hierarchy5')

                    # Check hierarchy condition and create categories
                    if hierarchy1.get('id') != 6:
                        pos_category_id, product_category_id = self._create_or_update_categories_action(
                            hierarchy1, hierarchy2, hierarchy3, hierarchy4, hierarchy5, company_id
                        )

                    # Process modifiers
                    if is_modifier:
                        self._create_or_update_modifier_action(item, 0.0)  # Use the modifier price

                    # Handle product pricing
                    else:
                        prices = item.get('prices', [])
                        list_price = 0.0 # Set a default list_price if all price are null or no prices

                        if prices:
                            # Get the maximum price, default to 0 if prices are empty or invalid
                            max_price_item = max(prices, key=lambda p: p.get('price', 0.0))
                            max_price = max_price_item.get('price', 0.0)
                            if max_price > 0.0:
                                    list_price =max_price

                    # Fetch the first image URL if available
                    image_url = None
                    images = item.get('images')
                    if images and isinstance(images, list) and len(images) > 0:
                        image_url = images[0].get('cdnResourceUrl')

                    # Check if the product already exists
                    existing_product = self.env['product.template'].search(
                        [('sirius_item_id', '=', sirius_item_id)], limit=1
                    )
                    isModifier = item.get('isModifier')

                    if not existing_product:
                        # Create a new product
                        product_values = {
                            'name': product_name,
                            'sirius_item_id': sirius_item_id,
                            'siriues_item_code':siriues_item_code,

                            'categ_id': product_category_id,
                            'pos_categ_ids': [(6, 0, [pos_category_id])],
                            'available_in_pos': not isModifier,
                            'self_order_available': not isModifier,

                            'is_modifier': False,
                            'prices': prices,
                            'list_price': list_price,
                            'taxes_id': [(6, 0, [])],  # No taxes applied
                            'company_id': company_id,  # Assign the current company
                        }
                        new_product = self.env['product.template'].create(product_values)
                        _logger.info(f"Created product {product_name} with ID {sirius_item_id}")

                        # Attach the image if available
                        if image_url:
                            self._store_image_in_attachment_action(image_url, new_product.id)
                    else:
                        # Update the existing product
                        product_values = {
                            'categ_id': product_category_id,
                            'pos_categ_ids': [(6, 0, [pos_category_id])],
                            'available_in_pos': not isModifier,
                            'self_order_available': not isModifier,
                            'siriues_item_code':siriues_item_code,

                            'is_modifier': False,
                            'prices': prices,
                            'list_price': list_price,
                            'taxes_id': [(6, 0, [])],  # No taxes applied
                            'company_id': company_id,  # Assign the current company
                        }
                        existing_product.write(product_values)
                        _logger.info(f"Updated product {product_name} with ID {sirius_item_id}")

                        # Attach the image if available
                        if image_url:
                            self._store_image_in_attachment_action(image_url, existing_product.id)
        except requests.exceptions.RequestException as e:
            _logger.error(f"API Request Error: {e}")
            return {"error": str(e)}
        except Exception as e:
            _logger.error(f"Unexpected Error: {e}")
            return {"error": str(e)}

    @api.model
    def _fetch_and_process_modifiers_full(self, headers, company_id):
        api_url = "https://gateway-api-srv.stage.bnayax.com/api/item/modifier/full"

        try:
            response = requests.get(api_url, headers=headers, timeout=30)
            response.raise_for_status()
            response_data = response.json()
            _logger.debug(f"API Response for Modifier Full: {response_data}")

            if response_data and response_data.get('data') and response_data.get('data').get('responseList'):
                # Iterate through the responseList
                for response_item in response_data.get('data').get('responseList'):
                    # Iterate through the groups array within each response item
                    for modifier_group in response_item.get('groups', []):
                         _logger.debug(modifier_group)
                         self._create_or_update_modifier_group_action(modifier_group, company_id)


        except requests.exceptions.RequestException as e:
           _logger.error(f"API Request Error: {e}")
           return {"error": str(e)}
        except Exception as e:
            _logger.error(f"Unexpected Error: {e}")
            return {"error": str(e)}

    def export_all_modifiers(self):
        """
        Fetches modifiers from the API and creates/updates records in Odoo.
        """
        # Get the current company
        company_id = self.env.company.id
        config = self.env['ir.config_parameter'].sudo()
        token = get_token(config)

        headers = {
            "Authorization": f"Bearer {token.strip()}",
        }
        # Fetch modifiers
        self._fetch_and_process_modifiers_full(headers, company_id)

        return self.display_notification('Success', 'Complete Export All Modifiers!', 'success')
    
    @api.model
    def _scheduler_export_all_items(self):
        """Scheduled method to print a statement every day ."""
        _logger.info("Scheduled job: starting export all items.")
        self.export_all_items()
        _logger.info("Scheduled job: finished export all items.")