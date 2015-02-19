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
                }

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