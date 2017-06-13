# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
import pytz
import re
import time
import hashlib
from openerp import tools
from urlparse import urljoin
import werkzeug


class crm_meeting(osv.osv):
    """ CRM Meeting Cases """
    _order = "start_datetime asc"
    _inherit = 'calendar.event'
    
    def do_create(self, cr, uid, vals, context=None):
        if vals.get('data', False):
            data = eval(vals.pop('data'))
            for data_key in data.keys():
                vals.update({'partner_ids' : [], 'opportunity_id' : False})
                if data_key == 'res.partner':
                    for partner in data.get('res.partner', []):
                        vals.update({'partner_ids' : [(4, partner)]})
                        self.create(cr, uid, vals, context=context)
                elif data_key == 'crm.lead':
                    for lead in data.get('crm.lead', []):
                        vals.update({'opportunity_id' : lead})
                        self.create(cr, uid, vals, context=context)
                elif data.get(data_key, []):
                    self.create(cr, uid, vals, context=context)
        return True

    def _tz_get(self, cr, uid, context=None):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user ID for security checks,
        @param context: A standard dictionary for contextual values
        """
        return [(x, x) for x in pytz.all_timezones]

    _columns = {
        'vtimezone': fields.selection(_tz_get, size=64, string='Timezone'),
    }

    _defaults = {
        'vtimezone': lambda s, cr, uid, c: s.pool.get('res.users').browse(cr, \
                                                        uid, uid, context=c).tz,
    }

crm_meeting()


class crm_lead(osv.osv):
    _inherit = 'crm.lead'
    _columns = {
                'lead_add_line': fields.one2many('lead.address.line', 'lead_id',\
                                                 'Lead Address Line'),
                'zimbra_msg_id': fields.char('Zimbra Messege ID', size=256),
                }

    def create_quick_lead(self, cr, uid, vals, context={}):
        crm_lead_pool = self.pool.get('crm.lead')
        vals.update({'type': 'lead'})
        if vals['zimbra_msg_id']:
            cr.execute("select id from crm_lead where zimbra_msg_id='%s'"%(\
                                                    vals['zimbra_msg_id']))
            existing_lead_ids = map(lambda x: x, cr.fetchall())
            if not existing_lead_ids:
                crm_id = crm_lead_pool.create(cr, uid, vals, context=context)
                return True
        return {'created': False}
    
    def get_signup_url_reminder_1(self, cr, uid, id, context=None):
        rec = self.browse(cr, uid, id, context=context)
        query = dict(db=cr.dbname)
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        route = 'login'
        fragment = dict()
        if rec.type == 'lead':
            fragment['action'] = self.pool.get('ir.model.data').xmlid_to_res_id(cr, uid, 'crm.crm_case_category_act_leads_all')
        elif rec.type == 'opportunity':
            fragment['action'] = self.pool.get('ir.model.data').xmlid_to_res_id(cr, uid, 'crm.crm_case_category_act_oppor11')
        fragment['model'] = self._name
        fragment['id'] = rec.id
        fragment['view_type'] = 'form'
        query['redirect'] = '/web#' + werkzeug.url_encode(fragment)
        return urljoin(base_url, "/web/%s?%s" % (route, werkzeug.url_encode(query)))
    
    def search_read(self, cr, uid, domain=None, fields=None, offset=0, limit=None, order=None, context=None):
        ret_val = super(crm_lead, self).search_read(cr, uid, domain=domain, fields=fields, offset=offset, limit=limit, order=order, context=context)
        for rec in ret_val:
            id = rec.get('id')
            rec['view_url'] = tools.ustr(self.get_signup_url_reminder_1(cr, uid, id))
        return ret_val

crm_lead()


class lead_address_line(osv.osv):
    _description = "Contact"
    _name = "lead.address.line"
    _rec_name='partner_address_id'
    _columns = {
                'lead_id':fields.many2one("crm.lead",'Lead'),
                'partner_address_id':fields.many2one('res.partner',\
                                                      'Contact Adress'),
                'phone': fields.char('Phone', size=32),
                'fax': fields.char('Fax', size=32),
                'email': fields.char('E-mail', size=32),
                'mobile': fields.char('Mobile', size=32),
                'responsibility': fields.many2one('partner.responsibility',\
                                                  'Responsibility'),
                }

    def onchange_partner_address_id(self,cr,uid,ids,partner_address_id,
                                    context=None):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user ID for security checks,
        @param ids: list of object ids,
        @param partner_address_id: specific partner id,
        @param context: A standard dictionary for contextual values
        """
        res={}
        if partner_address_id:
            address_pool = self.pool.get('res.partner')
            address_obj = address_pool.browse(cr,uid,partner_address_id,\
                                              context=context)
            res['phone']=address_obj.phone
            res['fax']= address_obj.fax
            res['email']= address_obj.email
            res['mobile']= address_obj.mobile
        return {'value':res}

#     def search_read(self, cr, uid, domain, fields=[], context={}):
#         """
#         @param self: The object pointer
#         @param cr: the current row, from the database cursor,
#         @param uid: the current user ID for security checks,
#         @param domain: Condition to filter on
#         @param fields: list of fields to read
#         @param context: A standard dictionary for contextual values
#         """
#         ids = self.search(cr, uid, domain, context=context)
#         read_data = lead_data = []
#         lead_pool = self.pool.get('crm.lead')
#         if ids:
#             read_data = self.read(cr, uid, ids, fields=fields, context=context)
#             lead_ids = [data['lead_id'][0] for data in read_data if \
#                         data['lead_id']]
#             if lead_ids:
#                 lead_data = lead_pool.read(cr,uid,lead_ids)
#         return lead_data

lead_address_line()


# def search_read(self, cr, uid, domain, fields=[], context={}):
#     """
#         @param self: The object pointer
#         @param cr: the current row, from the database cursor,
#         @param uid: the current user ID for security checks,
#         @param domain: Condition to filter on
#         @param fields: list of fields to read
#         @param context: A standard dictionary for contextual values
#     """
#     ids = self.search(cr, uid, domain, context=context)
#     read_data = []
#     if ids:
#         read_data = self.read(cr, uid, ids, fields=fields, context=context)
#     return read_data
# 
# osv.osv.search_read = search_read


class calendar_event(osv.osv):
    _inherit = 'calendar.event'

    _columns = {
                'create_date': fields.datetime('Creation Date'),
                'write_date': fields.datetime('Write Date'),
                }

calendar_event()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: