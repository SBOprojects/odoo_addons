{
    'name': 'Custom Nayax Settings',
    'summary': 'Adds Nayax settings to PoS configuration.',
    'version': '1.0',
    "license": "LGPL-3",

    'depends': ['base', 'point_of_sale'],
    "author": "KAD",
    'data': [
        'views/res_config_settings_view.xml',
        'views/pos_payment_method_views.xml',

    ],
}
