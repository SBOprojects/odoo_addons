
from datetime import datetime
import json
from odoo import models, fields, api, _
from odoo.addons.PCN_model.models import custom_tax_config
from odoo.exceptions import UserError
import logging
import base64
from io import BytesIO
import xlsxwriter

_logger = logging.getLogger(__name__)

class InvoiceReportWizard(models.TransientModel):
    _name = 'invoice.report.wizard'
    _description = 'Wizard to get invoices between two dates'

    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    file_data = fields.Binary("File", readonly=True)
    file_name = fields.Char("File Name", readonly=True)

    def get_invoices_between_dates(self, start_date, end_date):
        """
        Returns all invoices, bills, and credit notes between two dates.
        :param start_date: Start date (date field)
        :param end_date: End date (date field)
        :return: recordset of invoices, bills, and their credit notes
        """
        try:
            # Include customer invoices, vendor bills, and their respective credit notes
            invoices_and_bills = self.env['account.move'].search([
                ('move_type', 'in', ['out_invoice', 'in_invoice', 'out_refund', 'in_refund' ,'entry']),
                ('invoice_date', '>=', start_date),
                ('invoice_date', '<=', end_date)
            ])

            if not invoices_and_bills:
                _logger.info(f"No invoices or credit notes found between {start_date} and {end_date}")
                return invoices_and_bills

            # Log all details of each record if accessible
            for record in invoices_and_bills:
                try:
                    record_data = record.read()  # Read all fields
                    _logger.info(f"Record Details: {record_data}")
                except Exception as inner_e:
                    _logger.warning(f"Could not retrieve full details for Record ID {record.id}: {inner_e}")

            return invoices_and_bills
        except Exception as e:
            _logger.error(f"Error fetching invoices and credit notes: {e}")
            raise UserError(_("An error occurred while fetching invoices and credit notes: %s") % str(e))



    def get_invoices(self):
        if self.start_date > self.end_date:
            raise UserError(_("Start date must be before or equal to end date."))

        invoices = self.get_invoices_between_dates(self.start_date, self.end_date)

        # If no invoices were found, close the window and provide a context with a warning
        if not invoices:
            return {
                'type': 'ir.actions.act_window_close',
                'context': {'default_warning': {
                    'title': _('No Invoices Found'),
                    'message': _('No invoices were found for the selected date range.')
                }},
            }

        # Export invoices to Excel
        self.export_to_excel(invoices)

    def export_to_excel(self, invoices):
        """Exports the given invoices to an Excel file with all fields."""
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Invoices')

        # Set column headers and widths
        headers = self._get_invoice_fields()
        for col_idx, header in enumerate(headers):
            worksheet.set_column(col_idx, col_idx, 25)  # Set a standard width for all columns
            worksheet.write(0, col_idx, header)  # Write the header row

        # Write invoice data
        for row_idx, invoice in enumerate(invoices, start=1):
            for col_idx, field_name in enumerate(headers):
                value = self._get_field_value(invoice, field_name)
                worksheet.write(row_idx, col_idx, value)

        workbook.close()
        output.seek(0)

        # Encode the output file in base64
        self.file_data = base64.b64encode(output.read())
        output.close()

        # Set the file name for download
        self.file_name = 'invoices_report.xlsx'

    def _get_invoice_fields(self):
        """Returns a list of all fields to include in the invoice report."""
        return [
            'id',
            'invoice_date',
            'amount_total',
            'amount_untaxed',
            'name',
            'partner_id',  # The relation to partner record
            'move_type',
            'state',
            'invoice_line_ids',  # You can handle line items separately if needed
            # Add any other fields from the account.move model as needed
        ]
    def _get_field_value(self, invoice, field_name):
        if field_name == 'invoice_line_names':
            line_names = []
            for line in invoice.invoice_line_ids:
                if isinstance(line.name, str):
                    line_names.append(line.name)
                else:
                    line_names.append(str(line.name))  # Convert to string
            return ', '.join(line_names)

        elif field_name == 'partner_id':
            return invoice.partner_id.name if invoice.partner_id else ''
        elif field_name == 'invoice_date':
          return invoice.invoice_date.strftime("%Y-%m-%d") if invoice.invoice_date else ''
        elif field_name == 'move_type':
          return invoice.move_type
        elif field_name == 'state':
            return invoice.state
        elif field_name == 'invoice_payment_state':
            return invoice.invoice_payment_state
        elif field_name == 'amount_total':
            return invoice.amount_total
        elif field_name == 'amount_residual':
          return invoice.amount_residual
        elif field_name == 'name':
          return invoice.name if invoice.name else ''
        elif field_name == 'reference':
          return invoice.reference if invoice.reference else ''
        return ''
    def action_download_excel(self):
        """Triggers the download of the generated Excel file."""
        if not self.file_data:
            raise UserError(_("No invoices found to export."))

        return {
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=invoice.report.wizard&id=%s&field=file_data&download=true&filename=%s' % (self.id, self.file_name),
            'target': 'self',
        }
    
    def action_export_json(self):
        """Triggers the export of invoices to JSON format."""
        invoices = self.get_invoices_between_dates(self.start_date, self.end_date)
        if not invoices:
            raise UserError(_("No invoices found to export."))

        self.export_to_json(invoices)

        return {
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=invoice.report.wizard&id=%s&field=file_data&download=true&filename=%s' % (self.id, self.file_name),
            'target': 'self',
        }

    def action_export_txt(self):
        """Triggers the export of invoices to text format."""
        invoices = self.get_invoices_between_dates(self.start_date, self.end_date)
        if not invoices:
            raise UserError(_("No invoices found to export."))

        self.export_to_txt(invoices)

        return {
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=invoice.report.wizard&id=%s&field=file_data&download=true&filename=%s' % (self.id, self.file_name),
            'target': 'self',
        }
    
    def export_to_json(self, invoices):
        """Exports the given invoices to a JSON file with all fields."""
        output = BytesIO()
        invoice_data = [invoice.read() for invoice in invoices]  # Read all fields for each invoice
        output.write(json.dumps(invoice_data, default=str).encode('utf-8'))  # Convert to JSON and write to output
        output.seek(0)

        # Encode the output file in base64
        self.file_data = base64.b64encode(output.read())
        output.close()

        # Set the file name for download
        self.file_name = 'invoices_report.json'

    def export_to_txt(self, invoices):
        """Exports the given invoices to a text file with all fields."""
        output = BytesIO()
        
        for invoice in invoices:
            # Each invoice is a record, so read its fields
            invoice_details = invoice.read()[0]  # Get the first (and only) dictionary from the list
            _logger.info(f"Invoice Details: {invoice_details}")  # Log the details for debugging
            
            # Format details as a string
            invoice_text = "\n".join([f"{key}: {invoice_details[key]}" for key in invoice_details]) + "\n\n"
            output.write(invoice_text.encode('utf-8'))  # Write formatted string to output

        output.seek(0)

        # Encode the output file in base64
        self.file_data = base64.b64encode(output.read())
        output.close()

        # Set the file name for download
        self.file_name = 'invoices_report.txt'


#############################################################################################################
    def action_download_PCN_file(self):
        """Handles custom actions for invoice TXT file generation based on VAT ID and total amount."""
        invoices = self.get_invoices_between_dates(self.start_date, self.end_date)
        invoices_over_max = [inv for inv in invoices if inv.move_type == 'out_invoice' and not inv.partner_id.vat and inv.amount_total > custom_tax_config.MAX_AMOUNT]
        invoices_under_max = [inv for inv in invoices if inv.move_type == 'out_invoice' and not inv.partner_id.vat and inv.amount_total <= custom_tax_config.MAX_AMOUNT]

        # Show confirmation for invoices over max amount (without the download button)
        if invoices_over_max:
            invoice_details = self.generate_invoice_table(invoices_over_max)

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'invoice.over.max.wizard',
                'view_mode': 'form',
                'target': 'self',
                'context': {
                    'default_invoices_details': invoice_details,
                    'default_invoice_ids': [(6, 0, [inv.id for inv in invoices_over_max])],
                }
            }


            # Create a custom message with each invoice's details as a clickable link in a table similar to Odoo's invoice table
        if invoices_under_max:
            invoice_details = self.generate_invoice_table(invoices_under_max)
            # Return confirmation wizard with detailed message and invoice IDs
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'invoice.confirmation.wizard',
                'view_mode': 'form',
                'target': 'self',
                'context': {
                    'default_missing_vat_count': len(invoices_under_max),
                    'default_invoices_details': invoice_details,  # Pass the detailed invoice message as invoices_details
                    'default_invoice_ids': [(6, 0, [inv.id for inv in invoices_under_max])],  # Pass invoice ids explicitly
                    'default_invoice_report_id': self.id,

                }
            }



        # Generate TXT file if no conditions are triggered
        self.create_custom_pcn_txt()
        return self.download_file()






    def download_file(self):
        """Downloads the generated TXT file if available."""
        invoices =  self.get_invoices_between_dates(self.start_date, self.end_date)
        if not invoices:
            raise UserError(_("No invoices found to export between the dates: {} and {}.".format(self.start_date, self.end_date)))
        if not self.file_data:
            raise UserError(_("No file data found to export."))
        return {
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=invoice.report.wizard&id=%s&field=file_data&download=true&filename=%s' % (self.id, self.file_name),
            'target': 'self',
        }  
    
   
    
    
    def create_custom_pcn_txt(self):
        """Creates a custom TXT file starting with 'O', then company registry, year and month without spaces,
        followed by today's date in yyyymmdd format, and total untaxed amount with a sign (+/-).
        Includes a character for each invoice based on location and type.
        """
        output = BytesIO()
        
        # Fetch invoices between selected dates
        invoices = self.get_invoices_between_dates(self.start_date, self.end_date)
        
        # Separate counts for invoices, credit notes, bills, and bill credit notes
        invoice_credit_note_count = sum(1 for inv in invoices if inv.move_type in ['out_refund', 'out_invoice'])
        bill_credit_note_count = sum(1 for inv in invoices if inv.move_type in ['in_invoice', 'in_refund'])

        # Fetch and format other details
        current_company = self.env.company

        company_registry_1 = current_company.company_registry
         
        year_month_2 = datetime.today().strftime('%Y%m')
        today_date_3 = datetime.today().strftime('%Y%m%d')

        # Calculate the total untaxed amount for all invoices
        total_untaxed_amount_4 = self.calculate_total_untaxed_amount(invoices)
        total_vat_amount_5 = self.calculate_total_tax_amount(invoices)
        formatted_invoice_credit_note_count_6 = f"{invoice_credit_note_count:09}"
        total_amount_no_tax_7 = self.calculate_total_amount_no_tax(invoices)
        total_vat_bills_8 = self.calculate_total_vat_bills(invoices)
        formatted_bill_credit_note_count_9 = f"{bill_credit_note_count:09}"
        total_10 = self.calculate_vat_invoices_vs_bills(invoices)

        # Prepare invoice lines using the new function
        invoices_content = self.prepare_invoice_lines(invoices)

        # Initial header content
        content = (
            f"O{company_registry_1}{year_month_2}1{today_date_3}"
            f"{total_untaxed_amount_4}{total_vat_amount_5}"
            f"+{custom_tax_config.TOTAL_OF_SALES_TAXABLE}"
            f"+{custom_tax_config.NINE_ZEROS}{formatted_invoice_credit_note_count_6}"
            f"{total_amount_no_tax_7}{total_vat_bills_8}"
            f"+{custom_tax_config.NINE_ZEROS}{formatted_bill_credit_note_count_9}"
            f"{total_10}\n"
        )

        # Combine the content with the invoice lines
        full_content = f"{content}{invoices_content}\nX{company_registry_1}"

        # Write content to the output file
        output.write(full_content.encode('utf-8'))
        output.seek(0)

        # Encode the output file in base64
        self.file_data = base64.b64encode(output.read())
        output.close()

        # Set the file name for download
        self.file_name = 'PCN874.txt'

    def calculate_total_untaxed_amount(self, invoices):
        """
        Calculates the net total untaxed amount as a floored integer by subtracting credit note totals from invoice totals.
        :param invoices: Recordset of invoices and credit notes.
        :return: A string with the net total amount as a floored integer, formatted with a sign.
        """
        # Separate totals for invoices and credit notes
        invoice_total = sum(inv.amount_untaxed for inv in invoices if inv.move_type == 'out_invoice')
        credit_note_total = sum(inv.amount_untaxed for inv in invoices if inv.move_type == 'out_refund')

        # Calculate the net total (invoices - credit notes) and floor it to an integer
        net_total = int(invoice_total - credit_note_total)

        # Determine the sign based on the net total
        sign = "+" if net_total >= 0 else "-"

        # Format net total to 11 digits without decimal places
        formatted_net_total = f"{abs(net_total):011}"

        # Return the formatted net total with sign
        return sign + formatted_net_total


    def calculate_total_vat(self, invoices,n):
        """Calculates the total VAT for a set of invoices based on customer location."""
        total_vat_amount = 0.0

        for invoice in invoices:
            # Determine VAT rate based on customer's country
            country = invoice.partner_id.country_id.name
            vat_rate = custom_tax_config.ZERO_VAT_RATE  # Default to 0% if conditions aren't met
            
            if country == "Israel":
                vat_rate = custom_tax_config.ISRAEL_VAT_RATE
            elif country == "Palestine":
                vat_rate = custom_tax_config.PALESTINE_VAT_RATE
                if invoice.some_custom_field == "special_case":  # Replace with the actual condition for 0% VAT if applicable
                    vat_rate = custom_tax_config.ZERO_VAT_RATE
            
            # Calculate VAT for the invoice and add to total
            total_vat_amount += invoice.amount_untaxed * vat_rate

        # Determine the sign for total VAT amount
        sign = "+" if total_vat_amount >= 0 else "-"
        
        # Format VAT total to 9 digits with 2 decimal places
        if total_vat_amount.is_integer():
            formatted_total_vat_amount = f"{int(abs(total_vat_amount)):0{n}}.00"  # Format as integer with 9 digits and 2 decimals
        else:
            integer_part, decimal_part = f"{abs(total_vat_amount):.2f}".split(".")
            formatted_total_vat_amount = f"{integer_part.zfill(n)}.{decimal_part}"  # Prepare formatted total
            
        return sign + formatted_total_vat_amount


    def calculate_total_amount_no_tax(self, invoices):
        """
        Calculates the total amount for invoices and credit notes where the tax is zero.
        :param invoices: Recordset of invoices and credit notes.
        :return: A tuple containing formatted totals for invoices and credit notes with signs.
        """
        # Separate totals for invoices and credit notes
        invoice_amount_no_tax = sum(inv.amount_total for inv in invoices if inv.move_type == 'out_invoice' and inv.amount_tax == 0.0)
        credit_note_amount_no_tax = sum(inv.amount_total for inv in invoices if inv.move_type == 'out_refund' and inv.amount_tax == 0.0)
        net_total = int(invoice_amount_no_tax - credit_note_amount_no_tax)

        sign = "+" if net_total >= 0 else "-"

        formatted_net_total = f"{abs(net_total):011}"

        # Return formatted totals with signs
        return sign + formatted_net_total

    def get_invoice_character(self, invoice):
        """
        Returns a character based on the type and location of the invoice:
        - 'S' for sales to Israel
        - 'I' for sales to Palestine
        - 'P' for purchases from suppliers in Palestine
        - 'T' for purchases from suppliers in Israel
        """
        # Retrieve country and determine if the invoice is a sale or purchase
        country = invoice.partner_id.country_id.name

        is_sale = invoice.move_type in ['out_invoice', 'out_refund']  # Outgoing invoice indicates a sale
        is_purchase = invoice.move_type in ['in_invoice', 'in_refund']  # Incoming invoice indicates a purchase

        if  invoice.move_type == 'entry':
            return "K"
        if not country : 
            return "Y"  # Return 'L' if the sale doesn't have a VAT ID
        if (is_sale or is_purchase) and not invoice.partner_id.vat and country == "Israel":
            return "L"  # Return 'L' if the sale doesn't have a VAT ID
       # Determine character based on the type and location of the invoice
        if is_sale:
            if country == "Israel":
                return "S"
            elif country == "State of Palestine":
                return "I"
        elif is_purchase:
            if country == "State of Palestine":
                return "P"
            elif country == "Israel":
                return "T"
            


    def prepare_invoice_lines(self, invoices):
        """Prepares formatted lines for each invoice, sorted by date and time, including location-based character and details."""
        
        # Sort invoices by invoice_date and then by creation time
        sorted_invoices = sorted(invoices, key=lambda inv: (inv.invoice_date or datetime.min, inv.create_date or datetime.min))
        
        # Prepare formatted lines
        return "\n".join(
            f"{self.get_invoice_character(inv)}{inv.partner_id.vat or custom_tax_config.NINE_ZEROS}"
            f"{inv.invoice_date.strftime('%Y%m%d') if inv.invoice_date else 'N/A'}{custom_tax_config.REFERENCE_GROUP}"
            f"{str(inv.sequence_number).zfill(9) if inv.sequence_number else '000000000'}"
            f"{round(abs(inv.amount_tax)):09}{self.get_document_sign(inv.move_type)}"
            f"{round(abs(inv.amount_untaxed)):010d}{custom_tax_config.NINE_ZEROS}"
            for inv in sorted_invoices
        )

    def get_customers_without_vat_id(self, invoices):
        """Check for sales invoices without VAT IDs and return the list of customer names."""
        customers_without_vat_id = []
        for invoice in invoices:
            if invoice.move_type == 'out_invoice' and not invoice.partner_id.vat:
                customers_without_vat_id.append(invoice.partner_id.name)
        return customers_without_vat_id
    

    def calculate_total_tax_amount(self, invoices):
        """
        Calculates the total tax amount for invoices and credit notes separately.
        :param invoices: Recordset of invoices and credit notes.
        :param n: Total number of digits for formatting (excluding the sign).
        :return: A tuple containing formatted totals for invoices and credit notes with signs.
        """
        # Separate totals for invoices and credit notes
        invoice_tax_total = sum(inv.amount_tax for inv in invoices if inv.move_type == 'out_invoice')
        credit_note_tax_total = sum(inv.amount_tax for inv in invoices if inv.move_type == 'out_refund')
        net_total = round(invoice_tax_total - credit_note_tax_total)

        sign = "+" if net_total >= 0 else "-"

        # Format net total to 11 digits without decimal places
        formatted_net_total = f"{abs(net_total):09}"


        # Return formatted totals with signs
        return sign + formatted_net_total


    def get_document_sign(self, move_type):
        """
        Returns the sign based on the document type.
        :param move_type: The type of the document (e.g., 'out_invoice', 'in_invoice', 'out_refund', 'in_refund')
        :return: '+' if invoice or bill, '-' if credit note
        """
        if move_type in ['out_invoice', 'in_invoice']:
            return "+"
        elif move_type in ['out_refund', 'in_refund']:
            return "-"
        else:
            return "-"


    def calculate_total_vat_bills(self, invoices):
        """
        Calculates the total VAT amount for bills and credit notes for bills separately.
        :param invoices: Recordset of invoices and credit notes.
        :param n: Total number of digits for formatting (excluding the sign).
        :return: A tuple containing formatted totals for bills and credit notes with signs.
        """
        # Separate totals for bills and credit notes for bills
        bill_vat_total = sum(inv.amount_tax for inv in invoices if inv.move_type == 'in_invoice')
        credit_note_vat_total = sum(inv.amount_tax for inv in invoices if inv.move_type == 'in_refund')
        net_total = int(bill_vat_total - credit_note_vat_total)

        sign = "+" if net_total >= 0 else "-"

        # Format net total to 11 digits without decimal places
        formatted_net_total = f"{abs(net_total):09}"


        # Return formatted totals with signs
        return sign + formatted_net_total
    
    def calculate_vat_invoices_vs_bills(self, invoices):
        """Calculates the difference in VAT between invoices and bills."""
        invoice_vat_total = sum(inv.amount_tax for inv in invoices if inv.move_type in ['out_invoice']) - \
                            sum(inv.amount_tax for inv in invoices if inv.move_type in ['out_refund'])
        bill_vat_total = sum(inv.amount_tax for inv in invoices if inv.move_type in ['in_invoice']) - \
                        sum(inv.amount_tax for inv in invoices if inv.move_type in ['in_refund'])
        net_total = invoice_vat_total - bill_vat_total
        return f"{'+' if net_total >= 0 else '-'}{abs(round(net_total)):011}"
 


    def generate_invoice_table(self, invoices):
        # Define table headers and styles with enforced row height
        table_html = """
        <table style="width: 100%; border-collapse: collapse; font-size: 15px; background-color: #ffffff; margin-top: 10px;">
            <thead>
                <tr style="background-color: #f7f7f7; color: #3c3c3c; border-bottom: 2px solid #e5e5e5; height: 15px !important; line-height: 15px !important;">
                    <th style="padding: 2px 6px; text-align: left; font-weight: 600; border-right: 1px solid #e5e5e5; width: 120px; max-width: 120px;">Invoice ID</th>
                    <th style="padding: 2px 6px; text-align: left; font-weight: 600; border-right: 1px solid #e5e5e5; width: 160px; max-width: 160px;">Customer</th>
                    <th style="padding: 2px 6px; text-align: left; font-weight: 600; border-right: 1px solid #e5e5e5; width: 150px; max-width: 150px;">Invoice Date</th>
                    <th style="padding: 2px 6px; text-align: left; font-weight: 600; border-right: 1px solid #e5e5e5; width: 150px; max-width: 150px;">Due Date</th>
                    <th style="padding: 2px 6px; text-align: right; font-weight: 600; border-right: 1px solid #e5e5e5; width: 120px; max-width: 120px;">Amount Without Tax</th>
                    <th style="padding: 2px 6px; text-align: right; font-weight: 600; border-right: 1px solid #e5e5e5; width: 120px; max-width: 120px;">Tax Amount</th>
                    <th style="padding: 2px 6px; text-align: right; font-weight: 600; border-right: 1px solid #e5e5e5; width: 120px; max-width: 120px;">Total Amount</th>
                </tr>
            </thead>
            <tbody>
        """

        # Add each invoice as a clickable row with enforced row height
        for i, inv in enumerate(invoices):
            row_color = "#f9f9f9" if i % 2 == 0 else "#ffffff"
            table_html += f'''
                <tr style="background-color: {row_color}; color: #3c3c3c; cursor: pointer; border-bottom: 1px solid #f5f5f5; height: 5px !important; line-height: 5px !important;">
                    <td style="padding: 2px 6px; text-align: left; vertical-align: middle; border-right: 1px solid #f5f5f5;">
                        <a href="/web?#id={inv.id}&model=account.move" target="_blank" style="text-decoration: none; color: #3c3c3c;">
                            {inv.name}
                        </a>
                    </td>
                    <td style="padding: 2px 6px; text-align: left; vertical-align: middle; border-right: 1px solid #f5f5f5;">
                        <a href="/web?#id={inv.id}&model=account.move" target="_blank" style="text-decoration: none; color: #3c3c3c;">
                            {inv.partner_id.name}
                        </a>
                    </td>
                    <td style="padding: 2px 6px; text-align: left; vertical-align: middle; border-right: 1px solid #f5f5f5;">
                        <a href="/web?#id={inv.id}&model=account.move" target="_blank" style="text-decoration: none; color: #3c3c3c;">
                            {inv.invoice_date}
                        </a>
                    </td>
                    <td style="padding: 2px 6px; text-align: left; vertical-align: middle; border-right: 1px solid #f5f5f5;">
                        <a href="/web?#id={inv.id}&model=account.move" target="_blank" style="text-decoration: none; color: #3c3c3c;">
                            {inv.create_date.date()}
                        </a>
                    </td>
                    <td style="padding: 2px 6px; text-align: right; vertical-align: middle; border-right: 1px solid #f5f5f5;">
                        <a href="/web?#id={inv.id}&model=account.move" target="_blank" style="text-decoration: none; color: #3c3c3c;">
                            {inv.amount_untaxed}
                        </a>
                    </td>
                    <td style="padding: 2px 6px; text-align: right; vertical-align: middle; border-right: 1px solid #f5f5f5;">
                        <a href="/web?#id={inv.id}&model=account.move" target="_blank" style="text-decoration: none; color: #3c3c3c;">
                            {inv.amount_tax}
                        </a>
                    </td>
                    <td style="padding: 2px 6px; text-align: right; vertical-align: middle; border-right: 1px solid #f5f5f5;">
                        <a href="/web?#id={inv.id}&model=account.move" target="_blank" style="text-decoration: none; color: #3c3c3c;">
                            {inv.amount_total}
                        </a>
                    </td>
                </tr>
            '''
        # Close the table
        table_html += "</tbody></table>"
        return table_html
