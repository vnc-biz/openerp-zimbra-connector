# -*- encoding: utf-8 -*-
{
    "name" : "Zimbra Interface for Standard odoo",
    "version" : "1.1.0",
    "author" : "VNC",
    "website" : "http://www.vnc.biz/",
    "depends" : ["base", "vnc_zimbra_connector"],
    "category" : "Generic Modules/Zimbra interface",
    "description": """
      This module is extra addon for zimbra connector.
      It contains changes of module or view, needed in standard odoo.
      """,
    "data" : [
        'vnc_zimbra_connector_extra_view.xml',
    ],
    'js':[
          ],
    'qweb': [
             ],
    "active": False,
    'application': True,
    'sequence':3,
    "installable": True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: