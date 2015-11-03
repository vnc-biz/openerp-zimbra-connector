{
    "name" : "Zimbra Interface",
    "version" : "1.1.0",
    "author" : "VNC",
    "website" : "http://www.vnc.biz/",
    "depends" : ["base", "crm", "vnc_ose", "project", 'hr'],
    "category" : "Generic Modules/Zimbra interface",
    "description": """
      This module is required for the zimbra openerp plug-in to work
      properly.
      The Plugin allows you archive email and its attachments to the selected
      OpenERP objects. You can select a partner, a task, a project, an analytical
      account,or any other object and attach selected mail as eml file in
      attachment of selected record. You can create Documents for crm Lead,
      HR Applicant and project issue from selected mails.
      """,
    "data" : [
        'security/ir.model.access.csv',
        'crm_view.xml',
        'partner/partner_view.xml',
        'hr/hr_view.xml',
        'views/vnc_zimbra_connector.xml'
    ],
    'js':[
        'static/src/js/vnc_zimbra_connector.js',
          ],
    'qweb': [
             'static/src/xml/vnc_zimbra_connector.xml',
             ],
    "active": False,
    'application': True,
    'sequence':3,
    "installable": True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: