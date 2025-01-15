# crypto_utils.py
from cryptography.fernet import Fernet
import json
import requests

from odoo.exceptions import UserError
from odoo.tools import _

def generate_key():
    return b'2Hsc0AT-lFRLc-PjQVyrBFvxfjBAzGp7YCZOBi9VK0s='

def display_notification(title, message, notification_type='info'):
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

    
def encrypt_data(data: str, secret_key: str) -> str:
    f = Fernet(secret_key)
    encrypted_data = f.encrypt(data.encode())

    return encrypted_data.decode()

def decrypt_data(encrypted_data: str, secret_key: str) -> str:
    f = Fernet(secret_key)
    decrypted_data = f.decrypt(encrypted_data.encode())

    return decrypted_data.decode()

def get_token(config):
    secret_key = generate_key()  # Generate the key for decryption
    encrypted_access_token = config.get_param('external_access_token')
    if not encrypted_access_token or encrypted_access_token == '':
        # Raise UserError with message instead of display_notification
        raise UserError(
            _('Login Required: Access token is missing. Please log in to proceed.')
        )    
    access_token = decrypt_data(encrypted_access_token, secret_key)
    print(f"Decrypted access token: {access_token}")
    return access_token


def send_request_and_check_jwt(api_url, payload=None, endpoint_type="GET", headers=None):
    """
    Sends a request to the specified URL and checks if the response contains a JWT expiration error.
    """
    try:
        # Send the request based on the endpoint type
        if endpoint_type.upper() == "GET":
            response = requests.get(api_url, headers=headers, params=payload)
        elif endpoint_type.upper() == "POST":
            response = requests.post(api_url, headers=headers, json=payload)
        elif endpoint_type.upper() == "PUT":
            response = requests.put(api_url, headers=headers, json=payload)
        elif endpoint_type.upper() == "PATCH":
            response = requests.patch(api_url, headers=headers, json=payload)
        elif endpoint_type.upper() == "DELETE":
            response = requests.delete(api_url, headers=headers, json=payload)
        else:
            raise ValueError(f"Unsupported endpoint type: {endpoint_type}")

        response.raise_for_status()
        response_json = response.json()

        # Check for JWT expiration
        if (
            response_json.get("status") == "Forbidden" and
            "errors" in response_json and
            any("Jwt expired" in error.get("message", "") for error in response_json["errors"])
        ):
            return True, response_json  # JWT expired

        return False, response_json

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return False, None

def relogin_and_save_tokens(login_url, login, password, secret_key, config):
    """
    Attempts to relogin and save encrypted tokens to the configuration.
    """
    try:
        payload = {
            "login": login,
            "password": password,
            "extraClaims": {
                "additionalProp1": "string",
                "additionalProp2": "string",
                "additionalProp3": "string"
            }
        }
        headers = {'Content-Type': 'application/json'}
        response = requests.post(login_url, json=payload, headers=headers)
        response.raise_for_status()

        response_data = response.json()
        if response_data.get('status') == 'OK' and response_data.get('data'):
            data = response_data['data']
            access_token = data.get('accessToken')
            refresh_token = data.get('refreshToken')
            session_id = data.get('sessionId')
            companies = data.get('companies', [])
            company_names = [company.get('name') for company in companies]

            # Encrypt tokens and save them
            encrypted_access_token = encrypt_data(access_token, secret_key)
            encrypted_refresh_token = encrypt_data(refresh_token, secret_key)
            encrypted_session_id = encrypt_data(session_id, secret_key)
            encrypted_companies = encrypt_data(json.dumps(company_names), secret_key)
            encrypted_username = encrypt_data(login, secret_key)
            encrypted_password = encrypt_data(password, secret_key)

            config.set_param('external_access_token', encrypted_access_token)
            config.set_param('external_refresh_token', encrypted_refresh_token)
            config.set_param('external_session_id', encrypted_session_id)
            config.set_param('external_companies', encrypted_companies)
            config.set_param('external_username', encrypted_username)
            config.set_param('external_password', encrypted_password)

            return access_token
    except requests.exceptions.RequestException as e:
        print(f"Relogin failed: {e}")
        return None

def handle_request_with_relogin(api_url, payload=None, endpoint_type="GET", headers=None, config=None, secret_key=None):
    """
    Handles a request, relogging in if the JWT is expired and retrying the request.
    """
    is_expired, response_json = send_request_and_check_jwt(api_url, payload, endpoint_type, headers)

    if is_expired:
        print("JWT expired. Attempting to relogin...")
        # Decrypt credentials
        login = decrypt_data(config.get_param('external_username'), secret_key)
        password = decrypt_data(config.get_param('external_password'), secret_key)

        # Relogin and retrieve a new access token
        new_access_token = relogin_and_save_tokens(
            login_url="https://gateway-api-srv.stage.bnayax.com/api/login",
            login=login,
            password=password,
            secret_key=secret_key,
            config=config
        )

        if new_access_token:
            # Update headers with the new token
            headers['Authorization'] = f"Bearer {new_access_token}"
            print("Retrying the request with the new token...")
            return send_request_and_check_jwt(api_url, payload, endpoint_type, headers)

    return is_expired, response_json