from odoo import api, models
import json

class CompanyFields(models.Model):
    _inherit = 'res.company'

    @api.model
    def get_company_registry_json(self):
        companies = self.env['res.company'].search([])
        company_data = []

        for company in companies:
            # Get the 'company_registry' field value
            values = {'company_registry': company.company_registry}
            company_data.append(values)

        # Convert to JSON and print
        json_data = json.dumps(company_data, default=str, indent=4)
        print(json_data)
        # return json_data
