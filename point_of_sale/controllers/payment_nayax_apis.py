from odoo import http
from odoo.http import request
import requests
import json

class MyController(http.Controller):
    @http.route('/call-http-api', type='http', auth='public', csrf=False)
    def call_http_api(self):
        print("Call Nayax API")
        
        api_url = "https://193.227.237.248:8443/SPICy"
        
        # Define the payload
        payload = {
            "jsonrpc": "2.0",
            "method": "doTransaction",
            "id": "123454352",
            "params": [
                "ashrait", {
                    "vuid": "{{$guid}}",
                    "originalUID": "24033113105408833297721",
                    "tranType": 1,  # 53=refund
                    "tranCode": 1,
                    "creditTerms": 1,
                    "externalAuthNum": "0883012",
                    "hideAnimation": True,
                    "petrol": True,
                    "amount": 200,
                    "cashBackAmount": 100,
                    "cardless": True,
                    "currency": "376"
                }
            ]
        }

        # Send the POST request with JSON payload
        headers = {"Content-Type": "application/json"}
        response = requests.post(api_url, data=json.dumps(payload), headers=headers)
        
        print(response.json())  # Log the API response

        # Return the response to the caller
        return request.make_response(
            response.content,
            headers={"Content-Type": "application/json"}
        )
