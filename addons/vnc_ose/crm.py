# -*- coding: utf-8 -*-
from openerp.tools.translate import _
from datetime import datetime, timedelta, date
from openerp.osv import fields, osv
from openerp import tools
import time
import pytz


class crm_lead(osv.osv):
    _inherit="crm.lead"

    _columns = {
        'contact_last_name':fields.char('Last Name',size=128),
                
        # CRM Actions
        'last_activity_id': fields.many2one("crm.activity", "Last Activity", select=True),
        'next_activity_id': fields.many2one("crm.activity", "Next Activity", select=True),
        'next_activity_1': fields.related("last_activity_id", "activity_1_id", "name", type="char", string="Next Activity 1"),
        'next_activity_2': fields.related("last_activity_id", "activity_2_id", "name", type="char", string="Next Activity 2"),
        'next_activity_3': fields.related("last_activity_id", "activity_3_id", "name", type="char", string="Next Activity 3"),
        'date_action': fields.date('Next Activity Date', select=True),
        'title_action': fields.char('Next Activity Summary'),
    }

    
    def log_next_activity_1(self, cr, uid, ids, context=None):
        return self.set_next_activity(cr, uid, ids, next_activity_name='activity_1_id', context=context)

    def log_next_activity_2(self, cr, uid, ids, context=None):
        return self.set_next_activity(cr, uid, ids, next_activity_name='activity_2_id', context=context)

    def log_next_activity_3(self, cr, uid, ids, context=None):
        return self.set_next_activity(cr, uid, ids, next_activity_name='activity_3_id', context=context)

    def set_next_activity(self, cr, uid, ids, next_activity_name, context=None):
        for lead in self.browse(cr, uid, ids, context=context):
            if not lead.last_activity_id:
                continue
            next_activity = next_activity_name and getattr(lead.last_activity_id, next_activity_name, False) or False
            if next_activity:
                date_action = False
                if next_activity.days:
                    date_action = (datetime.now() + timedelta(days=next_activity.days)).strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT),
                lead.write({
                    'next_activity_id': next_activity.id,
                    'date_action': date_action,
                    'title_action': next_activity.description,
                })
        return True

    def log_next_activity_done(self, cr, uid, ids, context=None, next_activity_name=False):
        to_clear_ids = []
        for lead in self.browse(cr, uid, ids, context=context):
            if not lead.next_activity_id:
                continue
            body_html = """<div><b>${object.next_activity_id.name}</b></div>
%if object.title_action:
<div>${object.title_action}</div>
%endif"""
            body_html = self.pool['email.template'].render_template(cr, uid, body_html, 'crm.lead', lead.id, context=context)
            msg_id = lead.message_post(body_html, subtype_id=lead.next_activity_id.subtype_id.id)
            to_clear_ids.append(lead.id)
            self.write(cr, uid, [lead.id], {'last_activity_id': lead.next_activity_id.id}, context=context)

        if to_clear_ids:
            self.cancel_next_activity(cr, uid, to_clear_ids, context=context)
        return True

    def cancel_next_activity(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids,  {
            'next_activity_id': False,
            'date_action': False,
            'title_action': False,
        }, context=context)

    def onchange_next_activity_id(self, cr, uid, ids, next_activity_id, context=None):
        if not next_activity_id:
            return {'value': {
                'next_action1': False,
                'next_action2': False,
                'next_action3': False,
                'title_action': False,
                'date_action': False,
            }}
        activity = self.pool['crm.activity'].browse(cr, uid, next_activity_id, context=context)
        date_action = False
        if activity.days:
            date_action = (datetime.now() + timedelta(days=activity.days)).strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
        return {'value': {
            'next_activity_1': activity.activity_1_id and activity.activity_1_id.name or False,
            'next_activity_2': activity.activity_2_id and activity.activity_2_id.name or False,
            'next_activity_3': activity.activity_3_id and activity.activity_3_id.name or False,
            'title_action': activity.description,
            'date_action': date_action,
            'last_activity_id': False,
        }}
        
    
    def on_change_partner_id(self, cr, uid, ids, partner_id, context={}):
        lead_addrs = []
        values = {'lead_add_line': False, 'partner_name' : False,\
           'contact_name' : False, 'contact_last_name':False,\
           'street' : False, 'street2' : False, 'city' : False, \
           'state_id' : False, 'country_id' : False, 'email_from' : False, \
           'phone' : False, 'mobile' : False, 'fax' : False,
           'partner_address_id': False}
        if partner_id:
            values = super(crm_lead, self).on_change_partner_id(cr, uid, ids, \
                                partner_id=partner_id, context=context)['value']
            partner = self.pool.get('res.partner').browse(cr, uid, \
                                                    partner_id, context=context)
            if partner.child_ids:
                for child in partner.child_ids:
                    child_data = {
                                  'partner_address_id': child.id or False,
                                  'phone': child.phone or False,
                                  'fax': child.fax or False,
                                  'email': child.email or False,
                                  'mobile': child.mobile or False,
                                  'lead_id': ids and ids[0] or False,
                                  }
                    lead_addrs.append([0,0,child_data])
                values.update({'lead_add_line': lead_addrs,\
                               'partner_address_id': \
                        partner.child_ids and partner.child_ids[0].id or False})
            if partner.parent_id:
                values.update({'partner_name' : partner.parent_id.name,
                               'contact_name' : partner.first_name,
                               'contact_last_name' : partner.last_name,
                               'function' : partner.function,
                              });
            else:
                values.update({'partner_name' : False,
                              'contact_name' : partner.first_name,
                                'contact_last_name' : partner.last_name,
                               'function' : False,
                               });
        return {'value' : values}

    def _lead_create_contact(self, cr, uid, lead, name, is_company, \
                             parent_id=False, context=None):
        partner = self.pool.get('res.partner')
        if type(name) == dict:
            vals = {
                'first_name': name['first_name'] or '',
                'last_name': name['last_name'] or '',
                'user_id': lead.user_id.id,
                'comment': lead.description,
                'section_id': lead.section_id.id or False,
                'parent_id': parent_id,
                'phone': lead.phone,
                'mobile': lead.mobile,
                'email': tools.email_split(lead.email_from) and \
                        tools.email_split(lead.email_from)[0] or False,
                'fax': lead.fax,
                'title': lead.title and lead.title.id or False,
                'function': lead.function,
                'street': lead.street,
                'street2': lead.street2,
                'zip': lead.zip,
                'city': lead.city,
                'country_id': lead.country_id and lead.country_id.id or False,
                'state_id': lead.state_id and lead.state_id.id or False,
                'is_company': is_company,
                'type': 'contact'
            }
        else:
            vals = {'name': name,
                'first_name': name,
                'user_id': lead.user_id.id,
                'comment': lead.description,
                'section_id': lead.section_id.id or False,
                'parent_id': parent_id,
                'phone': lead.phone,
                'mobile': lead.mobile,
                'email': tools.email_split(lead.email_from) and \
                        tools.email_split(lead.email_from)[0] or False,
                'fax': lead.fax,
                'title': lead.title and lead.title.id or False,
                'function': lead.function,
                'street': lead.street,
                'street2': lead.street2,
                'zip': lead.zip,
                'city': lead.city,
                'country_id': lead.country_id and lead.country_id.id or False,
                'state_id': lead.state_id and lead.state_id.id or False,
                'is_company': is_company,
                'type': 'contact'
            }
        partner = partner.create(cr, uid, vals, context=context)
        return partner

    def _create_lead_partner(self, cr, uid, lead, context=None):
        partner_id = False
        if lead.partner_name and lead.contact_name:
            partner_id = self._lead_create_contact(cr, uid, lead, \
                                    lead.partner_name, True, context=context)
            full_name = {'first_name': lead.contact_name, \
                         'last_name': lead.contact_last_name or ''}
            partner_id = self._lead_create_contact(cr, uid, lead,\
                                full_name, False, partner_id, context=context)
        elif lead.partner_name and not lead.contact_name:
            partner_id = self._lead_create_contact(cr, uid, lead, \
                                    lead.partner_name, True, context=context)
        elif not lead.partner_name and lead.contact_name:
            full_name = {'first_name': lead.contact_name,\
                         'last_name': lead.contact_last_name or ''}
            partner_id = self._lead_create_contact(cr, uid, lead,\
                                        full_name, False, context=context)
        elif lead.email_from and self.pool.get('res.partner').\
                    _parse_partner_name(lead.email_from, context=context)[0]:
            contact_name = self.pool.get('res.partner').\
                    _parse_partner_name(lead.email_from, context=context)[0]
            full_name = {'first_name': lead.contact_name, 'last_name': ''}
            partner_id = self._lead_create_contact(cr, uid, lead, \
                                            full_name, False, context=context)
        else:
            raise osv.except_osv(
                _('Warning!'),
                _('No customer name defined. \
                  Please fill one of the following fields: Company Name,\
                  Contact Name or Email ("Name <email@address>")')
            )
        return partner_id

crm_lead()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: