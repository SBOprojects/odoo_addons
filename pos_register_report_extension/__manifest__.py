{
    "name": "",
    "version": "1.0.0",
    "author": "KAD",
    "category": "Point of Sale",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "data": [
       "views/pos_session.xml"
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_register_report_extension/static/src/xml/close_pos_popup.xml",
            "pos_register_report_extension/static/src/js/close_pos_popup.js",  #Added this line
        ],
    },
    "installable": True,
    "auto_install": False,
}