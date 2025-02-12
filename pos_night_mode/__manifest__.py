{
    'name': 'POS Night Mode Theme',
    'version': '18.0.1.0.0',
    'category': 'Themes/Backend',
    'summary': """This module facilitates the transformation of color theme
    of odoo to fit nayax theme .""",
    'description':"""This module facilitates the transformation of color theme
    of odoo to fit nayax theme .""",
    'author': 'KAD Solutions',
    'company': 'KAD Solutions',
    'maintainer': 'KAD Solutions',
    'website': 'https://www.kad.is',
    'depends': ['base', 'point_of_sale','web','sale_management'],
    'assets': {
        'point_of_sale._assets_pos': [
            "pos_night_mode/static/src/scss/overwritecss.scss",


        ],
        'web.assets_backend': [
            "pos_night_mode/static/src/scss/overwritecss.scss",
        ], 
    },
    'images': [
        'static/description/banner-1.png',
        'static/description/banner-2.png',
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
