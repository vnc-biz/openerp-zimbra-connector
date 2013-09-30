# -*- coding: utf-8 -*-
{
    "name": "Project VNC OSE",
    "version": "7.0",
    "author": "VNC",
    "website": "http://www.vnc.biz",
    "category": "Generic Modules/",
    "depends": ['event'],
    "description": """Customized module for CRM AND Zimbra Connector
    Openerp Version 7
    """,
    "init_xml": [],
    "update_xml": [
           'partner_view.xml',
           'crm_task/crm_task_view.xml',
           'crm_task/crm_task_menu.xml',
           'security/ir.model.access.csv',
    ],
    'js':[
          ],
    'qweb': [
             ],
    'demo_xml': [
    ],
    'test': [
    ],
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: