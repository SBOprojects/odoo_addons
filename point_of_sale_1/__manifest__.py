# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'report x and z',
    'version': '1.0.1',
    'category': 'Sales/Point of Sale',
    'sequence': 40,
    "author": "KAD",
    'summary': 'report x and z & online payment by nayax',
    'depends': ['base', 'point_of_sale'],
    'data': [
        'views/res_config_settings_view.xml',
        'views/pos_payment_method_views.xml',
    ],

    'installable': True,
'assets': {
    'point_of_sale._assets_pos': [
                "point_of_sale_1/static/src/app/navbar/closing_popup/closing_popup.xml",
                "point_of_sale_1/static/src/app/navbar/closing_popup/closing_popup.js",
                "point_of_sale_1/static/src/app/screens/payment_screen/payment_screen.js",
                "point_of_sale_1/static/src/app/screens/payment_screen/payment_screen.xml",
                "point_of_sale_1/static/src/app/screens/payment_screen/payment_lines/payment_lines.js",
                "point_of_sale_1/static/src/app/screens/payment_screen/payment_functions.js",


    ],
},
    'license': 'LGPL-3',
}
