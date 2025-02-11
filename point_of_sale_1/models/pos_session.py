from odoo import models, fields, api, _
from odoo.exceptions import AccessError

class PosSession(models.Model):
    _inherit = 'pos.session'

    def get_closing_control_data(self):
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessError(_("You don't have the access rights to get the point of sale closing control data."))
        self.ensure_one()
        orders = self._get_closed_orders()
        payments = orders.payment_ids.filtered(lambda p: p.payment_method_id.type != "pay_later")
        cash_payment_method_ids = self.payment_method_ids.filtered(lambda pm: pm.type == 'cash')
        default_cash_payment_method_id = cash_payment_method_ids[0] if cash_payment_method_ids else None
        default_cash_payments = payments.filtered(lambda p: p.payment_method_id == default_cash_payment_method_id) if default_cash_payment_method_id else []
        total_default_cash_payment_amount = sum(default_cash_payments.mapped('amount')) if default_cash_payment_method_id else 0
        non_cash_payment_method_ids = self.payment_method_ids - default_cash_payment_method_id if default_cash_payment_method_id else self.payment_method_ids
        non_cash_payments_grouped_by_method_id = {pm: orders.payment_ids.filtered(lambda p: p.payment_method_id == pm) for pm in non_cash_payment_method_ids}

        cash_in_count = 0
        cash_out_count = 0
        cash_in_out_list = []
        for cash_move in self.sudo().statement_line_ids.sorted('create_date'):
            if cash_move.amount > 0:
                cash_in_count += 1
                name = f'Cash in {cash_in_count}'
            else:
                cash_out_count += 1
                name = f'Cash out {cash_out_count}'
            cash_in_out_list.append({
                'name': cash_move.payment_ref if cash_move.payment_ref else name,
                'amount': cash_move.amount
            })

        #Add order lines
        products_info = {
            'qty': 0,
            'total': 0
        }
        category_map = {}
        for order in orders:
            products_info['total'] += order.amount_total
            for line in order.lines:
                categoryName = line.product_id.product_tmpl_id.categ_id.name if line.product_id.product_tmpl_id.categ_id else "Uncategorized"

                if categoryName not in category_map:
                    category_map[categoryName] = {
                        'name': categoryName,
                        'qty': 0,
                        'total': 0,
                        'products':[],
                    }
                category_map[categoryName]['qty'] += line.qty
                category_map[categoryName]['total'] += line.price_subtotal_incl
                category_map[categoryName]['products'].append({
                        'product_id': line.product_id.display_name,
                        'qty': line.qty,
                        'uom_id': [line.product_uom_id.id, line.product_uom_id.name],
                        'price_subtotal_incl':line.price_subtotal_incl,
                        'discount':line.discount
                    })

        current_company = self.env.company  # Get the current company
        total_card_payment_amount = sum(
            sum(payments.mapped('amount')) for payments in non_cash_payments_grouped_by_method_id.values()
        ) if non_cash_payments_grouped_by_method_id else 0

        company_tax = current_company.account_sale_tax_id.amount if current_company.account_sale_tax_id else 0

        data = {
            'orders_details': {
                'orders': list(category_map.values()),
                'products_info': products_info,
                'company': company_tax,
                'company_name': current_company.name,
                'company_vat': current_company.vat,
                'total_cash_payment': total_default_cash_payment_amount + total_card_payment_amount,
                'quantity': len(orders),
                'amount': sum(orders.mapped('amount_total')),
            },
            'opening_notes': self.opening_notes,
            'default_cash_details': {
                'name': default_cash_payment_method_id.name,
                'amount': self.cash_register_balance_start
                          + total_default_cash_payment_amount
                          + sum(self.sudo().statement_line_ids.mapped('amount')),
                'opening': self.cash_register_balance_start,
                'payment_amount': total_default_cash_payment_amount,
                'moves': cash_in_out_list,
                'id': default_cash_payment_method_id.id
            } if default_cash_payment_method_id else {},
            'non_cash_payment_methods': [{
                'name': pm.name,
                'amount': sum(non_cash_payments_grouped_by_method_id[pm].mapped('amount')),
                'number': len(non_cash_payments_grouped_by_method_id[pm]),
                'id': pm.id,
                'type': pm.type,
            } for pm in non_cash_payment_method_ids],
            'is_manager': self.env.user.has_group("point_of_sale.group_pos_manager"),
            'amount_authorized_diff': self.config_id.amount_authorized_diff if self.config_id.set_maximum_difference else None,
        }
        print(data)
        return data