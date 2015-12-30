# -*- coding: utf-8 -*-
{
    "name": "Project VNC OSE",
    "version": "8.0",
    "author": "VNC",
    "website": "http://www.vnc.biz",
    "category": "Generic Modules/",
    "depends": ['event','crm', 'auth_signup'],
    "description": """Customized module for CRM AND Zimbra Connector
    Odoo Version 8.0
    """,
    "data": [
           'crm_activity/crm_action_data.xml',
           'security/ir.model.access.csv',
           "partner_view.xml",
           "crm_task/crm_task_view.xml",
           "crm_task/crm_task_menu.xml",
           "crm_view.xml",
           "common_view.xml",
           "crm_task/email_data.xml",
           'crm_activity/crm_action_views.xml',
           'crm_activity/crm_activity_report_view.xml'
    ],
    "demo": [
           'crm_activity/crm_action_demo.xml',
    ],
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
