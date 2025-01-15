{
    'name': "Sirius",
    'version': '1.0',
   'depends': ['base', 'product' ,'point_of_sale','web'],
    'data': [
        'views/res_config_settings.xml',
         'views/pos.order.xml',

        'security/ir.model.access.csv'
    ],
     "assets": {
 
        'web.assets_backend': [
    'nayax_pos_auth/static/src/style/overwritecss.scss'
        ],},
    'installable': True,
    'application': True,
}
