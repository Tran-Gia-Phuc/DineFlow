# -*- coding: utf-8 -*-
{
    "name": "DineFlow",
    "version": "17.0.1.0.0",
    "summary": """Dining management system""",
    "description": """Building my own dining management system""",
    "author": "DineFlow",
    "maintainer": "phuc.info",
    "website": "https://phuc.info",
    "category": "Restaurant",  # https://github.com/odoo/odoo/blob/17.0/odoo/addons/base/data/ir_module_category_data.xml
    "depends": ["base", "mail", "hr"],
    "data": [
        "security/groups.xml",  
        "security/ir.model.access.csv",
        "data/restaurant_data.xml",
        "views/menu_items.xml",
        "views/menu_views.xml",
        "views/table_views.xml",
        "views/booking_views.xml",
        "views/leave_views.xml",
        "views/order_views.xml",
        "views/employee_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "dineflow/static/src/css/dineflow.css"
            #     "zoo/static/src/components/counter/*",  # <-- khai báo widget sắp hiện thực
            #     "zoo/static/src/components/mytable/*",
            #     "zoo/static/src/components/myheader/*",
        ]
    },
    "demo": [],
    "css": [],
    # 'qweb': [
    #     'static/src/xml/counter.xml'    # register qweb template
    # ],
    "installable": True,
    "auto_install": False,
    "application": True,
    "license": "LGPL-3",
}
