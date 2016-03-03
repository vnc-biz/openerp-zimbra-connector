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
        'show_action': fields.boolean('Show action', readonly=False),
        'activity_transition_ids': fields.one2many('crm.activity.transition', 'lead_id', 'Activity Transitions')
    }

    def log_activity_transitions(self, cr, uid, ids, vals, context=None):
        transition_id= None
        transition_obj = self.pool.get('crm.activity.transition')
        if ('lead_id' in vals and vals['lead_id']) and ('start_date' in vals and vals['start_date']):
            transition_id = transition_obj.search(cr, uid, [('lead_id', '=', vals['lead_id']), ('start_date', '=', vals['start_date'])])
        if transition_id:
            transition_obj.write(cr, uid, transition_id[0], vals)
            transition_id = transition_id[0]
        else:
            transition_id = transition_obj.create(cr, uid, vals)
        return transition_id
        
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
                    date_action = (datetime.now() + timedelta(days=next_activity.days)).strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
                    
                    date_action = date_action.split(' ')[0] if date_action else False
                transition_id = self.pool.get('crm.activity.transition').search(cr, uid, [('start', '=', date_action), ('lead_id', '=', ids[0])])
                
                if transition_id:
                    show_action = False
                else:           
                    show_action = True
                lead.write({
                    'next_activity_id': next_activity.id,
                    'date_action': date_action,
                    'title_action': next_activity.description,
                    'show_action': show_action
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
            if lead.next_activity_id and lead.next_activity_id.is_call:
                phone_vals = {'name' : lead.next_activity_id.name, 'opportunity_id' : lead.id, 'partner_id' : lead.partner_id and lead.partner_id.id or False,
                              'partner_phone' : lead.phone or '', 'date' : time.strftime('%Y-%m-%d %H:%M:%S'), 'date_start' : time.strftime('%Y-%m-%d %H:%M:%S'), 
                              'user_id' : lead.user_id and lead.user_id.id or False, 'priority' : str(3), 'partner_mobile' : lead.mobile or '', 
                              'categ_id' : self.pool.get('ir.model.data').xmlid_to_res_id(cr, uid, 'crm.categ_phone1')
                }
                self.pool.get('crm.phonecall').create(cr, uid, phone_vals, context=context)
            to_clear_ids.append(lead.id)
            self.write(cr, uid, [lead.id], {'last_activity_id': lead.next_activity_id.id, 'show_action': False}, context=context)
            #self.log_activity_transitions(cr, uid, ids, {'attendee_ids': [], 'activity_id': lead.next_activity_id.id, 'lead_id': lead.id, 'start': lead.date_action, 'stop': lead.date_action, 'start_date': lead.date_action, 'name': lead.title_action})

        if to_clear_ids:
            self.cancel_next_activity(cr, uid, to_clear_ids, context=context)
        return True
    
    def cancel_next_activity(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids,  {
            'next_activity_id': False,
            'date_action': False,
            'title_action': False,
        }, context=context)

    def add_to_activity_calendar(self, cr, uid, ids, context=None):
        for lead in self.browse(cr, uid, ids, context=context):
            if not lead.date_action or not lead.title_action:
                raise osv.except_osv(_('Error!'), _('You have to define date and title of activity to add it in calendar'))        
            
            start = datetime.combine(datetime.strptime(lead.date_action , '%Y-%m-%d'), datetime.min.time()).strftime('%Y%m%d %H:%M:%S')
            transition_id = self.log_activity_transitions(cr, uid, ids, {'allday' :True, 'activity_id': lead.next_activity_id.id, 'lead_id': lead.id, 'start':  lead.date_action, 'stop': lead.date_action, 'name': lead.title_action})
            if transition_id:
                self.write(cr, uid, lead.id, {'show_action': False})
        return True
    
    
    def add_more_details(self, cr, uid, ids, context=None):
        for lead in self.browse(cr, uid, ids, context=context):
            domain = []
            if context is None:
                context={}
            if lead.next_activity_id:
                domain.append(('activity_id', '=', lead.next_activity_id.id))
            if lead.date_action:
                domain.append(('start_date', '=', lead.date_action))
            domain.append(('lead_id', '=', lead.id))
            transition_ids = self.pool.get('crm.activity.transition').search(cr, uid, domain)
            context.update({'from_lead': 'yes'})
            return {
                      'name': _('Activity Transition Form'),
                      'view_type': 'form',
                      'view_mode': 'form',
                      'res_model': 'crm.activity.transition',
                      'type': 'ir.actions.act_window',
                      'res_id': transition_ids[0],
                      'context': context,
                      'view_id': self.pool.get('ir.model.data').xmlid_to_res_id(cr, uid, 'crm_activity_transition_view_form'),
                      'target': 'new',
                      'flags': {'form': {'action_buttons': True}}
                      }
        return True
        
        
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
        lead_id = ids and ids[0] or None
        if lead_id:
            transition_id = self.pool.get('crm.activity.transition').search(cr, uid, [('activity_id', '=', next_activity_id), ('start_date', '=', date_action), ('lead_id', '=', lead_id)])
            if transition_id:
                show_action = False
            else:           
                show_action = True
        else :
            show_action = True
        
        return {'value': {
            'next_activity_1': activity.activity_1_id and activity.activity_1_id.name or False,
            'next_activity_2': activity.activity_2_id and activity.activity_2_id.name or False,
            'next_activity_3': activity.activity_3_id and activity.activity_3_id.name or False,
            'title_action': activity.description,
            'date_action': date_action,
            'last_activity_id': False,
            'show_action': show_action
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

    
    def convert_opportunity(self, cr, uid, ids, partner_id, user_ids=False, section_id=False, context=None):
        if context is None:
            context = {}
        context.update({'convert_from_lead': 1})
        return super(crm_lead, self).convert_opportunity(cr, uid, ids, partner_id, user_ids, section_id, context=context)
        
    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        transition_pool = self.pool['crm.activity.transition']
        lead_id = super(crm_lead, self).create(cr, uid, vals, context)
        if 'next_activity_id' in vals and vals['next_activity_id'] :
            if not vals['date_action']:
                raise osv.except_osv(_('Error!'), _('You have to define date of activity to add it in transition'))
           # start = datetime.combine(datetime.strptime(vals['date_action'] , '%Y-%m-%d'), datetime.min.time()).strftime('%Y%m%d %H:%M:%S')
            activity_name = self.pool.get('crm.activity').read(cr, uid, vals['next_activity_id'], ['name'])
            res = {'allday' :True, 'activity_id': vals['next_activity_id'], 'lead_id': lead_id, 'start':  vals['date_action'], \
                                'start_date': vals['date_action'], 'stop': vals['date_action'], 'name': vals['title_action'] or activity_name['name']}
            if 'partner_id' in vals and vals['partner_id']:
                res.update({'partner_id': vals['partner_id']})           
                onchange_val = transition_pool.onchange_partner_id(cr, uid, [], vals['partner_id'])
                res.update(onchange_val['value'])
            
            transition_id = self.log_activity_transitions(cr, uid, [], res)
            if transition_id:
                self.write(cr, uid, lead_id, {'show_action': False})
        return lead_id
    
    def write(self, cr , uid, ids, vals, context=None):
        if context is None:
            context = {}
        transition_pool = self.pool['crm.activity.transition']
        vals['show_action'] = False
        result = super(crm_lead, self).write(cr, uid, ids, vals, context)
        if not ('convert_from_lead' in context and context['convert_from_lead'] or 'from_lead' in context and context['from_lead']) and (('next_activity_id' in vals and vals['next_activity_id']) or ('date_action' in vals and vals['date_action']) or ('title_action' in vals and vals['title_action'])) :
            write_rec = self.browse(cr, uid, ids[0])
            if not write_rec.next_activity_id:
                return True
            if not write_rec.date_action:
                raise osv.except_osv(_('Error!'), _('You have to define date of activity to add it in transition'))
        #    start = datetime.combine(datetime.strptime(write_rec.date_action , '%Y-%m-%d'), datetime.min.time()).strftime('%Y%m%d %H:%M:%S')
            
            res = {'allday' :True, 'activity_id': write_rec.next_activity_id.id, 'lead_id': write_rec.id, 'start':  write_rec.date_action, 'start_date': write_rec.date_action, 'stop': write_rec.date_action, 'name': write_rec.title_action or write_rec.next_activity_id.name}
            if write_rec.partner_id:
                res.update({'partner_id': write_rec.partner_id.id})
                onchange_val = transition_pool.onchange_partner_id(cr, uid, [], write_rec.partner_id.id)
                res.update(onchange_val['value'])
            transition_id = self.log_activity_transitions(cr, uid, [], res)
        return result
    
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

class crm_activity_transition(osv.osv):
    _name = 'crm.activity.transition'
    _inherit = "calendar.event"
    
    _columns = {
        'activity_id': fields.many2one('crm.activity', 'Activity'),
        'lead_id': fields.many2one('crm.lead', 'Lead'),
        'activity_date': fields.date('Activity Date'),
        'title_action': fields.char('Activity Title'),
        'partner_ids': fields.many2many('res.partner', 'calendar_event_res_partner_rel2', string='Attendees'),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'partner_address_id': fields.many2one('res.partner', 'Partner Contact'),
        'phone':fields.related('partner_id','phone',type="char", size=64, \
                               string="Phone"),
        'mobile':fields.related('partner_id','mobile',type="char", size=64,\
                                string="Mobile"),
        'email_from': fields.related('partner_id','email',type="char", \
                                     size=64, string="Email"),
        'description':fields.text('Description'),
        'user_delegated_id':fields.many2one('res.users','Delegated By',\
                                             readonly=True),
        'delegated_on': fields.date('Delegate on', readonly=True),
        'state': fields.selection([('open', 'Confirmed'),
                                     ('draft', 'Unconfirmed'),
                                     ('cancel', 'Cancelled'),
                                     ('done', 'Done')], 'State', \
                                     size=16, readonly=True),
    }
    
    
    def default_get(self, cr, uid, fields, context=None):
        """
        calling default method (Default fields) for the object crm_activity_transition.
        Returns Dictionary of default fields.
        """
        res = super(crm_activity_transition,self).default_get( cr, uid, fields, \
                                                context=context)
        
        user_id = uid
        if res and res.has_key('user_id') and res['user_id'] != False:
            user_id = res['user_id']
        user = self.pool.get('res.users').browse(cr, uid, user_id, context)
        user_section = user.section_id and user.section_id.id or False
        res['section_id'] = user_section
        
        default_partner_address_id = False
        default_partner_id =  False
        if context and 'default_opportunity_id' in context and \
                                            context['default_opportunity_id']:
            crm_pool = self.pool.get('crm.lead')
            crm_Data = crm_pool.read(cr, uid , \
                                     int(context['default_opportunity_id']),\
                                     ['partner_id','partner_address_id'])
            res['partner_id'] = crm_Data['partner_id'] and \
                                crm_Data['partner_id'][0] or False
            if 'partner_id' in crm_Data and crm_Data.get('partner_id'):
                default_partner_address_id = False
                default_partner_id =  res['partner_id']

        if default_partner_address_id:
            read_data = self.pool.get('res.partner').read(cr, uid,\
                        default_partner_address_id)            
            res['partner_id'] = read_data['partner_id'] and \
                                read_data['partner_id'][0] or False
            default_partner_id = res['partner_id']

        if default_partner_id:
            onchange_val = self.onchange_partner_id(cr, uid, [],\
                                            default_partner_id)
            res.update(onchange_val['value'])
            addr = self.pool.get('res.partner').address_get(cr, uid,\
                [int(default_partner_id)], ['contact','default'])
            res['partner_address_id'] = addr['contact']            
        return res
    
    
    def onchange_partner_id(self, cr, uid, ids, partner_id, email=False):
        res = {}
        if not partner_id:
            return {'value' : {'email_from':False, 'phone':False,\
                                'mobile':False}}
        res = self.pool.get('res.partner').read(cr, uid, partner_id, \
                                            ['name','phone','mobile','email'])
        return {'value' : {'email_from':res['email'], 'phone':res['phone'],\
                                            'mobile':res['mobile']}}
    
    def onchange_user_id(self,cr,uid,ids,user_id,context={}):
        if not user_id:
            return {'value':{}}
        else:
            user_section = False
            user_obj = self.pool.get('res.users').browse(cr, uid, user_id)
            if user_id != uid :
                    return {'value':{'user_delegated_id': uid, 'delegated_on': time.strftime('%Y-%m-%d')}}
            else:
                return {'value':{}}
        return {}
    
    def create(self, cr, uid, vals, context={}):
        context.update({'crm_activity':True})
        if vals and 'user_id' in vals and vals['user_id'] != uid:
            vals['user_delegated_id'] = uid
            vals['delegated_on'] = time.strftime('%Y-%m-%d')
        return super(crm_activity_transition, self).create(cr, uid, vals, context=context)
    
    def write(self, cr, uid, ids, vals, context={}):        
        if not isinstance(ids, (list,tuple)):
            ids = [ids]
        old_datas = self.read(cr, uid, ids, ['user_id','start_datetime','stop_datetime', 'lead_id'],\
                    context=context)
        for old_data in old_datas:
            if not old_data['user_id'] or ('user_id' in vals and \
                                    vals['user_id'] != old_data['user_id'][0]):
                vals['user_delegated_id'] = uid
                vals['delegated_on'] = time.strftime('%Y-%m-%d')
                
            if 'from_lead' in context and context['from_lead']=='yes' and old_data['lead_id'] :
                lead_vals={}
                if 'name' in vals:
                    lead_vals['title_action']=vals['name']
                if 'activity_id' in vals:
                    lead_vals['next_activity_id']=vals['activity_id']
                if 'start_date' in vals:
                    lead_vals['date_action']=vals['start_date']
                self.pool.get('crm.lead').write(cr, uid, [old_data['lead_id'][0]], lead_vals, context=context)    
        return super(crm_activity_transition, self).write(cr, uid, ids, vals, context=context)
    
    def do_delete(self, cr, uid, ids, context=None, *args):
        if context is None:
            context = {}
        for item in self.browse(cr, uid, ids, context=context):            
            if item.activity_id and item.lead_id and item.lead_id.next_activity_id:
                if item.activity_id.id==item.lead_id.next_activity_id.id:
                    value = {
                            'name': _('Activity Transition Unlink'),
                            'view_type': 'form',
                            'view_mode': 'form',
                            'res_model': 'crm.activity.do.unlink',
                            'res_id': False,
                            'view_id': False,
                            'type': 'ir.actions.act_window',
                            'target': 'new'
                        }
                    return value
                else:
                   self.pool.get('crm.lead').write(cr, uid, [item.lead_id.id], {'activity_transition_ids': [(2, item.id, False)]})
            else:
                self.pool.get('crm.lead').write(cr, uid, [item.lead_id.id], {'activity_transition_ids': [(2, item.id, False)]})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
            }
             
    
crm_activity_transition()

class crm_activity_do_unlink(osv.osv_memory):
    _name = 'crm.activity.do.unlink'
    
    
    
    def do_delete(self, cr, uid, ids, context=None, *args):
        if context is None:
            context = {}
        activity_trans_obj = self.pool.get('crm.activity.transition')
        data = context and context.get('active_ids', []) or []
        for item in activity_trans_obj.browse(cr, uid, data):
            if item.lead_id:
                self.pool.get('crm.lead').write(cr, uid, [item.lead_id.id], {'activity_transition_ids': [(2, item.id, False)]})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
            }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: