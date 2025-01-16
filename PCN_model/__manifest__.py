{
    "name":"PCN MODEL",
    "summary":"Test module",
    "version":"18.0.0.0.0",
    "license":"LGPL-3",
    "author": "KAD",
    'depends': ['account'],
    'category': 'Accounting',

     'data': [
        'views/pcn_view.xml',
        'views/account_move_view.xml',
        'security/ir.model.access.csv',

        ],
    'installable': True,
    'application': True,

} 