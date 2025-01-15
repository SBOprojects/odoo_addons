import json
from requests import request
import requests
from odoo import http
from odoo.http import request


class Home(http.Controller):

            @http.route('/external_login', type='http', auth='none', methods=['POST'], csrf=False)
            def external_login(self, **kw):
                login_url = "https://gateway-api-srv.stage.bnayax.com/api/login"
                payload = {
                    'username': kw.get('username'),
                    'password': kw.get('password')
                }
                headers = {
                    'Content-Type': 'application/json'
                }
                response = requests.post(login_url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    token = response.json().get('token')
                    if token:
                        request.session['external_token'] = token
                        return request.make_response(json.dumps({'status': 'success', 'token': token}), [('Content-Type', 'application/json')])
                    else:
                        return request.make_response(json.dumps({'status': 'error', 'message': 'Token not found'}), [('Content-Type', 'application/json')], status=400)
                else:
                    return request.make_response(json.dumps({'status': 'error', 'message': 'Login failed'}), [('Content-Type', 'application/json')], status=response.status_code)

