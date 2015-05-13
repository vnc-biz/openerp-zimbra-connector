# -*- coding: utf-8 -*-
{
    "name": "Project VNC OSE",
    "version": "8.0",
    "author": "VNC",
    "website": "http://www.vnc.biz",
    "category": "Generic Modules/",
    "depends": ['event','crm'],
    "description": """Customized module for CRM AND Zimbra Connector
    Odoo Version 8.0
    """,
    "data": [
           'security/ir.model.access.csv',
           "partner_view.xml",
           "crm_task/crm_task_view.xml",
           "crm_task/crm_task_menu.xml",
           "crm_view.xml",
           "common_view.xml",
    ],
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
