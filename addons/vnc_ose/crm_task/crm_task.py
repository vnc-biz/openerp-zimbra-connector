# -*- coding: utf-8 -*-
import openerp
from openerp.addons.calendar import calendar
# from openerp.addons.base_status.base_state import base_state
from openerp.osv import fields, osv
from openerp.tools.translate import _
import logging
from openerp.addons.crm import crm
from datetime import datetime, timedelta, date
import time
import logging
import werkzeug
from urlparse import urljoin

_logger = logging.getLogger(__name__)

class crm_field_history(osv.osv):
    _name = 'crm.field.history'
    _description = 'CRM Fields History'
    _rec_name = 'value_after'
    _order = 'create_date desc'
    _columns = {
        'value_after':fields.char('Value After', size=256),
        'value_before':fields.char('Value Before', size=256),
        'create_date': fields.datetime('Creation Date' , readonly=True),
        'lead_id':fields.many2one('crm.lead','Lead/Opportunity'),
        'task_id':fields.many2one('crm.task', 'Task'),
        'user_id':fields.many2one('res.users','User'),
        'field_name':fields.char('Field name',size=256),
    }

crm_field_history()



class calendar_event(osv.Model):
    """ Model for Calendar Event """
    _inherit = 'calendar.event'
    
    def get_search_fields(self, browse_event, order_fields, r_date=None):
        sort_fields = {}
        for ord in order_fields:
            if ord == 'id' and r_date:
                sort_fields[ord] = '%s-%s' % (browse_event[ord], r_date.strftime("%Y%m%d%H%M%S"))
            else:
                sort_fields[ord] = browse_event[ord]
                if type(browse_event[ord]) is openerp.osv.orm.browse_record:
                    name_get = browse_event[ord].name_get()
                    if len(name_get) and len(name_get[0]) >= 2:
                        sort_fields[ord] = name_get[0][1]
        if r_date:
            sort_fields['sort_start'] = r_date.strftime("%Y%m%d%H%M%S")
        else:
            if 'display_start' in browse_event and browse_event['display_start']:
                sort_fields['sort_start'] = browse_event['display_start'].replace(' ', '').replace('-', '')
        return sort_fields
    
    def create_attendees(self, cr, uid, ids, context):
        user_obj = self.pool['res.users']
        current_user = user_obj.browse(cr, uid, uid, context=context)
        res = {}
        if (context.has_key('crm_task') and context.get('crm_task')) or (context.has_key('crm_activity') and context.get('crm_activity')):
            return res
        for event in self.browse(cr, uid, ids, context):
            attendees = {}
            for att in event.attendee_ids:
                attendees[att.partner_id.id] = True
            new_attendees = []
            new_att_partner_ids = []
            for partner in event.partner_ids:
                if partner.id in attendees:
                    continue
                access_token = self.new_invitation_token(cr, uid, event, partner.id)
                values = {
                    'partner_id': partner.id,
                    'event_id': event.id,
                    'access_token': access_token,
                    'email': partner.email,
                }

                if partner.id == current_user.partner_id.id:
                    values['state'] = 'accepted'

                att_id = self.pool['calendar.attendee'].create(cr, uid, values, context=context)
                new_attendees.append(att_id)
                new_att_partner_ids.append(partner.id)

                if not current_user.email or current_user.email != partner.email:
                    mail_from = current_user.email or tools.config.get('email_from', False)
                    if not context.get('no_email', False):
                        if self.pool['calendar.attendee']._send_mail_to_attendees(cr, uid, att_id, email_from=mail_from, context=context):
                            self.message_post(cr, uid, event.id, body=_("An invitation email has been sent to attendee %s") % (partner.name,), subtype="calendar.subtype_invitation", context=context)

            if new_attendees:
                self.write(cr, uid, [event.id], {'attendee_ids': [(4, att) for att in new_attendees]}, context=context)
            if new_att_partner_ids:
                self.message_subscribe(cr, uid, [event.id], new_att_partner_ids, context=context)

            # We remove old attendees who are not in partner_ids now.
            all_partner_ids = [part.id for part in event.partner_ids]
            all_part_attendee_ids = [att.partner_id.id for att in event.attendee_ids]
            all_attendee_ids = [att.id for att in event.attendee_ids]
            partner_ids_to_remove = map(lambda x: x, set(all_part_attendee_ids + new_att_partner_ids) - set(all_partner_ids))

            attendee_ids_to_remove = []

            if partner_ids_to_remove:
                attendee_ids_to_remove = self.pool["calendar.attendee"].search(cr, uid, [('partner_id.id', 'in', partner_ids_to_remove), ('event_id.id', '=', event.id)], context=context)
                if attendee_ids_to_remove:
                    self.pool['calendar.attendee'].unlink(cr, uid, attendee_ids_to_remove, context)

            res[event.id] = {
                'new_attendee_ids': new_attendees,
                'old_attendee_ids': all_attendee_ids,
                'removed_attendee_ids': attendee_ids_to_remove
            }
        return res
calendar_event()

class crm_task(osv.osv):
    """ CRM task Cases """
    _name = 'crm.task'
    _description = "Task"
    _order = "priority desc"
    _inherit = "calendar.event"
    _check_fields = ['user_id']

    def check_fields(self, cr, uid, ids, vals, context={}):
        result = {}
        if not isinstance(ids,(list,tuple)):
            ids = [ids]
        for self_obj in self.read(cr, uid, ids, self._check_fields, \
                                  context=context):
            for field_check in self._check_fields:
                if vals and field_check in vals and self_obj[field_check] != \
                                                            vals[field_check]:
                    if  vals[field_check]:
                        f_val = self.pool.get('res.users').read(cr, uid, \
                                            vals[field_check], ['name'])['name']
                    else:
                        f_val = ''
                    self.pool.get('crm.field.history').create(cr, uid, {
                                'value_after':f_val,
                                'value_before':self_obj[field_check] and \
                                                self_obj[field_check][-1] or '',
                                'task_id':self_obj['id'],
                                'user_id':uid,
                                'field_name':field_check,
                    })
        return result
    
    def get_signup_url_reminder_task(self, cr, uid, id, context=None):
        rec = self.browse(cr, uid, id, context=context)
        query = dict(db=cr.dbname)
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        route = 'login'
        fragment = dict()
        fragment['action'] = self.pool.get('ir.model.data').xmlid_to_res_id(cr, uid, 'vnc_ose.crm_case_categ_meet')
        fragment['model'] = self._name
        fragment['id'] = rec.id
        fragment['view_type'] = 'form'
        query['redirect'] = '/web#' + werkzeug.url_encode(fragment)
        return "/web/%s?%s" % (route, werkzeug.url_encode(query))

    def write(self, cr, uid, ids, vals, context={}):
        if not isinstance(ids, (list,tuple)):
            ids = [ids]
        old_datas = self.read(cr, uid, ids, ['user_id','start_datetime','stop_datetime'],\
                    context=context)
        for old_data in old_datas:
            if not old_data['user_id'] or ('user_id' in vals and \
                                    vals['user_id'] != old_data['user_id'][0]):
                vals['user_delegated_id'] = uid
                self.check_fields(cr, uid, old_data['id'], vals, context)
            # Copying date to stop_datetime if it is False, calling onchage will return the stop_datetime
            if not old_data['stop_datetime'] and old_data['start_datetime']:
                date = self.browse(cr, uid, ids[0]).start
                data = self.onchange_dates(cr, uid, ids[0], 'start', date, context=context)
                vals.update(data['value'])
        ret_val = super(crm_task, self).write(cr, uid, ids, vals, context=context)
        for rec in self.browse(cr, uid, ids, context=context):
            if rec.task_type == 't' and rec.meeting_id:
                event_val = {}
                if vals.get('name', False):
                    event_name = ''
                    if rec.categ_id:
                        event_name += rec.categ_id.name +' : '
                    event_name += vals.get('name', False)
                    event_val.update({'name' : event_name})
                if vals.get('start_datetime', False):
                    event_val.update({'start_datetime' : vals.get('start_datetime', False)})
                if vals.get('stop_datetime', False):
                    event_val.update({'stop_datetime' : vals.get('stop_datetime', False)})
                if vals.get('user_id', False) and rec.user_id:
                    event_val.update({'user_id' : rec.user_id.id, 'partner_ids' : [(6, 0, [rec.user_id.partner_id.id])]})
                if vals.get('partner_id', False) or vals.get('opportunity_id', False):
                    description = ""
                    if rec.opportunity_id:
                        description += "Lead / Opportunity : " +rec.opportunity_id.name +"\n\n"
                    if rec.partner_id:
                        partner_name = rec.partner_id.parent_id and rec.partner_id.parent_id.name or rec.partner_id.name
                        description += "Partner Name : " +partner_name +"\n\n"
                        description += "Contact Name : " +rec.partner_id.name +"\n\n"
                    event_val.update({'description' : description})
                self.pool.get('calendar.event').write(cr, uid, [rec.meeting_id.id], event_val, context=context)
        return ret_val

    def read_group(self,cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        res = super(osv.osv, self).read_group(cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby, lazy=lazy)
        return res

    def create(self, cr, uid, vals, context={}):
        context.update({'crm_task':True})
        if vals and 'user_id' in vals and vals['user_id'] != uid:
            vals['user_delegated_id'] = uid
        if vals.get('task_type', '') == 't':
            event_name = ''
            if vals.get('categ_id', False):
                categ_rec = self.pool.get('crm.case.categ').browse(cr, uid, vals.get('categ_id', False), context=context)
                event_name += categ_rec.name +' : '
            event_name += vals.get('name', False)
            event_val = {'name' : event_name, 'start_datetime' : vals.get('start_datetime', ''), 'stop_datetime' : vals.get('stop_datetime', '')}
            if vals.get('user_id', False):
                user_rec = self.pool.get('res.users').browse(cr, uid, vals.get('user_id', False), context=context)
                event_val.update({'user_id' : user_rec.id, 'partner_ids' : [(6, 0, [user_rec.partner_id.id])]})
            description = ""
            if vals.get('opportunity_id', False):
                opportunity_rec = self.pool.get('crm.lead').browse(cr, uid, vals.get('opportunity_id', False), context=context)
                description += "Lead / Opportunity : " +opportunity_rec.name +"\n\n"
            if vals.get('partner_id', False):
                partner_rec = self.pool.get('res.partner').browse(cr, uid, vals.get('partner_id', False), context=context)
                partner_name = partner_rec.parent_id and partner_rec.parent_id.name or partner_rec.name
                description += "Partner Name: " +partner_name +"\n\n"
                description += "Contact Name : " +partner_rec.name +"\n\n"
            event_val.update({'description' : description})
            meet_id = self.pool.get('calendar.event').create(cr, uid, event_val, context=context)
            vals.update({'meeting_id' : meet_id})
        res = super(crm_task, self).create(cr, uid, vals, context=context)
        if vals and 'user_id' in vals and vals['user_id'] != uid:
            self.check_fields(cr, uid, res, vals, context)
        # Copying date to stop_datetime if it is False, calling onchage will return the stop_datetime
        if vals.get('stop_datetime',False) == False:
            if vals.get('start_datetime',False):
                data = self.onchange_dates(cr, uid, [], vals['start_datetime'],\
                                            duration=2, context=context)
                vals.update(data['value'])
        return res

    def default_get(self, cr, uid, fields, context=None):
        """
        calling default method (Default fields) for the object crm_task.
        Returns Dictionary of default fields.
        """
        res = super(crm_task,self).default_get( cr, uid, fields, \
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
            f_name = self.pool.get('res.partner').read(cr, uid,\
                        default_partner_address_id, ['name'])
            res['first_name'] = f_name['name']
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
            if res.get('partner_address_id',False) and 'first_name' not in res:
                f_name = self.pool.get('res.partner').read(cr, uid, \
                                        res.get('partner_address_id'), ['name'])
                res['first_name'] = f_name['name']
        return res

    def onchange_partner_id(self, cr, uid, ids, part, email=False):
        res = {}
        if not part:
            return {'value' : {'email_from':False, 'phone':False,\
                                'mobile':False}}
        res = self.pool.get('res.partner').read(cr, uid, part, \
                                            ['name','phone','mobile','email'])
        return {'value' : {'email_from':res['email'], 'phone':res['phone'],\
                                            'mobile':res['mobile']}}

    def _set_short_desc(self, cr, uid, ids, name, arg, context=None):
        res = {}
        short_desc = ''
        for self_obj in self.browse(cr, uid, ids, context=context):
            if self_obj.description:
                res[self_obj.id] = self_obj.description[:100]
            else:
                res[self_obj.id] = short_desc
        return res

    def _get_current_datetime(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for self_obj in self.browse(cr, uid, ids, context=context):
            res[self_obj.id] = time.strftime('%Y-%m-%d %H:%M:%S')
        return res
    
    def get_related_attachments(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            attachment_ids = []
            if rec.opportunity_id:
                attachment_ids += self.pool.get('ir.attachment').search(cr, uid, [('res_model','=','crm.lead'),('res_id','=',rec.opportunity_id.id)], context=context)
            attachment_ids += self.pool.get('ir.attachment').search(cr, uid, [('res_model','=','crm.task'),('res_id','=',rec.id)], context=context)
            res[rec.id] = attachment_ids
        return res
    
    _columns = {
        # From crm.case
        'crm_id':fields.char('CRM ID',size=256),
        'name': fields.char('Summary', size=124),
        'date': fields.datetime("Date"),
        'start_datetime': fields.datetime("Date"),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'company_id': fields.many2one('res.company', 'Company'),
        'partner_address_id': fields.many2one('res.partner', 'Partner Contact'),
        'phone':fields.related('partner_id','phone',type="char", size=64, \
                               string="Phone"),
        'mobile':fields.related('partner_id','mobile',type="char", size=64,\
                                string="Mobile"),
        'description':fields.text('Description'),
        'section_id': fields.many2one('crm.case.section', 'Sales Team',\
                     states={'done': [('readonly', True)]}, \
                     select=True, help='Sales team to which Case belongs to.'),
        'id': fields.integer('ID'),
        'opportunity_id': fields.many2one ('crm.lead', 'Opportunity',\
                                     domain="[('type', '=', 'opportunity')]"),
        'email_from': fields.related('partner_id','email',type="char", \
                                     size=64, string="Email"),
        'create_date': fields.datetime('Creation Date'),
        'write_date': fields.datetime('Write Date'),
        'user_delegated_id':fields.many2one('res.users','Delegated By',\
                                             readonly=True),
        'stage_id': fields.many2one('crm.case.stage', 'Stage',\
                                     domain="[('type','=','task')]"),
        'categ_id': fields.many2one('crm.case.categ', 'task Type', \
                        domain="[('object_id.model', '=', 'crm.task')]", \
            ),
        'duration': fields.float('Duration', digits=(16,2)),
        'date_closed': fields.datetime('Closed'),
        'stop_datetime': fields.datetime('End Datetime', states={'done': [('readonly', True)]}, \
                                         track_visibility='onchange'),
        'priority': fields.selection([('0','Very Low'),
                                      ('1','Low'),
                                      ('2','Medium'),
                                      ('3','High'),
                                      ('4','Very High')], 'Priority'),
        'message_ids': fields.one2many('mail.message', 'res_id', 'Messages',\
                                        domain=[('model','=',_name)]),
        'history_crm_fields_ids': fields.one2many('crm.field.history', \
                                            'task_id', 'Fields History', ),
        'state': fields.selection([('open', 'Confirmed'),
                                     ('draft', 'Unconfirmed'),
                                     ('cancel', 'Cancelled'),
                                     ('done', 'Done')], 'State', \
                                     size=16, readonly=True),
        'user_id': fields.many2one('res.users', 'User'),
        'file_name':fields.char('File Name',size=256),
        'file_mime_type':fields.char('File Mine Type',size=256),
        'first_name':fields.char('First Name',size=256),
        'last_name':fields.char('Last Name',size=256),
        'task_type':fields.selection([('t','Task'),('n','Note')],'Task Type'),
        'meeting_id':fields.many2one('calendar.event','Meetings'),
        'meeting_ids': fields.many2many('crm.task', 'calendar_event_res_partner_rel1','res_partner_id', 'crm_task_id',
            'Meetings'),
        'owner_changed':fields.boolean('Owner Changed'),
        'short_description': fields.function(_set_short_desc, type='text',\
                            method=True, string='Short Description',),
        'current_datetime':fields.function(_get_current_datetime, method=True,\
                            type='datetime', string='Current DateTime',\
                            readonly=True,help="It represents Current Datetime"),
        'partner_ids': fields.many2many('res.partner', 'calendar_event_res_partner_rel1', string='Attendees', states={'done': [('readonly', True)]}),
        'related_attachment_ids' : fields.function(get_related_attachments, relation="ir.attachment", type="many2many", string="Attachments")
    }
    
    def _check_end_date(self, cr, uid, ids, context=None):
        ''' Validating the Task End Date: Task End Date should be greater than Start Date '''
        for task_obj in self.browse(cr, uid, ids, context=context):
            if task_obj.date and task_obj.stop_datetime:
                if task_obj.stop_datetime.split(' ')[0] \
                    < task_obj.date.split(' ')[0]:
                    return False
        return True

    _constraints = [
        (_check_end_date, '\n"Task End Date" must be greater than\
                         "Task Start Date".',\
                         ['stop_datetime']),
    ]
    
    def onchange_end_dates(self, cr, uid, ids, stop_datetime, context=None):
        if context is None:
            context = {}
        value = {'duration' : 0, 'start_datetime' : ''}
        if stop_datetime:
            value = {'duration' : 1, 'start_datetime' : (datetime.strptime(stop_datetime, '%Y-%m-%d %H:%M:%S') - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')}
        return {'value': value}

    def onchange_dates(self, cr, uid, ids, start_date, duration=False, \
                       end_date=False, allday=False, context=None):
        """Returns duration and/or end date based on values passed
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of calendar event’s IDs.
        @param start_date: Starting date
        @param duration: Duration between start date and end date
        @param end_date: Ending Datee
        @param context: A standard dictionary for contextual values
        """
        if context is None:
            context = {}
 
        value = {}
        if not start_date:
            return value
        if not end_date and not duration:
            duration = 1.00
            value['duration'] = duration
        if allday:# For all day event
            value = {'duration': 24}
            duration = 24.0
 
        start_date = start_date and start_date.split('.')[0]
        end_date = end_date and end_date.split('.')[0]
        start = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
        if end_date and not duration:
            end = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
            diff = end - start
            duration = float(diff.days)* 24 + (float(diff.seconds) / 3600)
            value['duration'] = round(duration, 2)
        elif not end_date:
            end = start + timedelta(hours=duration)
            value['stop_datetime'] = end.strftime("%Y-%m-%d %H:%M:%S")
        elif end_date and duration and not allday:
            # we have both, keep them synchronized:
            #test_theraline set duration based on end_date (arbitrary decision: this avoid
            # getting dates like 06:31:48 instead of 06:32:00)
            end = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
            diff = end - start
            duration = float(diff.days)* 24 + (float(diff.seconds) / 3600)
            value['duration'] = round(duration, 2)
        return {'value': value}

    def _get_stage(self, cr, uid, context={}):
        ids = self.pool.get('crm.case.stage').search(cr, uid, 
                                    [('type','=','task')] ,order='sequence')
        return ids and ids[0] or False

    _defaults = {
        'state': 'draft',
        'active': 1,
        'user_id': lambda self, cr, uid, ctx: uid,
        'stage_id': _get_stage,
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company').\
                            _company_default_get(cr, uid, s._name, context=c),
        'description': " ",
        'priority' : '0'
    }

    def log(self, cr, uid, id, message, secondary=False, context=None):
        if context is None: context = {}
        if not context.has_key('default_date'):
            context.update({'default_date': time.strftime("%Y-%m-%d")})
        self.message_post(cr, uid, [id], message, context=context)

    def case_open(self, cr, uid, ids, *args):
        """Confirms task
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of task Ids
        @param *args: Tuple Value for additional Params
        """
        if ids:
            for (id, name) in self.name_get(cr, uid, ids):
                message = _("The task '%s' has been confirmed.") % name
                id=calendar.calendar_id2real_id(id)
                self.log(cr, uid, id, message)
            cases = self.browse(cr, uid, ids)
            for case in cases:
                data = {'state': 'open', 'active': True}
                if not case.user_id:
                    data['user_id'] = uid
                self.write(cr, uid, case.id, data)
        return True

    def case_close(self, cr, uid, ids, *args):
        for (id, name) in self.name_get(cr, uid, ids):
                message = _("The task '%s' has been closed.") % name
                id=calendar.calendar_id2real_id(id)
                self.log(cr, uid, id, message)

        self.write(cr, uid, ids, {'date_closed': \
                                  time.strftime('%Y-%m-%d %H:%M:%S')})
        cases = self.browse(cr, uid, ids)
        for case in cases:
            data = {'state': 'done', 'active': True}
            if not case.user_id:
                data['user_id'] = uid
            self.write(cr, uid, case.id, data)
            self.task_done_mail_notification(cr, uid, [case.id])
        return True

    def case_reset(self, cr, uid, ids, *args):
        """Resets case as draft
        :param ids: List of case Ids
        """
        cases = self.browse(cr, uid, ids)
        cases[0].state # to fill the browse record cache
        self.write(cr, uid, ids, {'state': 'draft', 'active': True})
        return True

    def onchange_user_id(self,cr,uid,ids,user_id,context={}):
        if not user_id:
            return {'value':{}}
        else:
            user_section = False
            user_obj = self.pool.get('res.users').browse(cr, uid, user_id)
            if user_id != uid :
                    return {'value':{'owner_changed':1}}
            else:
                return {'value':{'owner_changed':0}}
        return

    
    def task_done_mail_notification(self, cr, uid, ids, context=None):
        if not ids:
            return True
        if context is None:
            context={}

        template_obj=self.pool.get('email.template')
        task = self.browse(cr, uid, ids[0])
        template_id = self.pool.get('ir.model.data').get_object_reference(cr, \
                                      uid, 'vnc_ose', 'email_template_task_done')
        if not template_id:
            raise osv.except_osv(_('Invalid Template !'),
                        _('No Template Found for the name email_template_task_done !'))
        template = template_obj.browse(cr, uid, template_id[1])
        if task.user_delegated_id and task.user_delegated_id.id!= task.user_id.id:
            context.update({'user_email': task.user_delegated_id.email, 'user_name': task.user_delegated_id.name})
        context['login_url'] = self.get_signup_url_reminder_task(cr, uid, task.id, context=context)
        action = self.pool.get('email.template').send_mail(cr, uid, \
                                   template_id[1], ids[0], context=context)
        
        return True
    
    def salesman_change_mail_notification_task(self, cr, uid, automatic=False, \
                                        template=False,type='t', context=None,):
        task_ids = self.search(cr, uid, \
                        [('owner_changed','=',True),('task_type','=',type)])
        if not task_ids :
            return True
        if not template:
            raise osv.except_osv(_('Invalid Template !'),
                        _('No Template Found for the given name %s!')%template)
        template_obj=self.pool.get('email.template')
        so_template = template_obj.search(cr,uid,[('name','=',template)])
        if not so_template:
            raise osv.except_osv(_('Invalid Template !'),
                        _('No Template Found for the given name %s!')%template)
        for task_id in task_ids:
            action=template_obj.send_mail(cr,uid,so_template[0],task_id,context)
            self.write(cr, uid, [task_id], {'owner_changed':False})
        return True

    def task_idel_reminder(self, cr, uid, automatic=False, template=False, \
                        no_of_days=0, type='t',no_of_reminder=1, context=None):
        d1 = date.today()
        d2 = str(d1 - timedelta(days=no_of_days))
        task_ids = self.search(cr, uid, [('state','not in',('done','cancel')),\
                                ('create_date','<',d2),('task_type','=',type)])
        cr.execute("SELECT count(res_id),res_id from cron_mail_sent where"\
        "res_model='%s' and cron_name='%s' group by res_id "%(self._name,\
                                                        'task_idel_reminder'))
        line_ids = map(lambda x: x, cr.fetchall())
        line_ids = [x[1] for x in line_ids if x[0] >= no_of_reminder]
        task_ids = list( set(task_ids) - set(line_ids))

        if not task_ids :
            return True
        if not template:
            raise osv.except_osv(_('Invalid Template !'),
                        _('No Template Found for the given name %s!')%template)
        template_obj=self.pool.get('email.template')
        so_template = template_obj.search(cr,uid,[('name','=',template)])
        if not so_template:
            raise osv.except_osv(_('Invalid Template !'),
                        _('No Template Found for the given name %s!')%template)

        for task_id in task_ids:
            action = template_obj.send_mail(cr,uid,so_template[0], \
                                            task_id,context)
            self.pool.get('cron.mail.sent').create(cr, uid, {
                    'res_model':'%s'%(self._name),
                    'res_id':task_id,
                    'cron_name':'task_idel_reminder',
                    })
        return True
    
    def get_signup_url(self, cr, uid, ids, context=None):
        assert len(ids) == 1
        task = self.browse(cr, uid, ids[0], context=context)
        partner_id = task.user_id.partner_id.id
        contex_signup = dict(context)
        partner_obj = self.pool.get('res.partner')
        return partner_obj._get_signup_url_for_action(cr, uid, [partner_id],
                                                                action='mail.action_mail_redirect',
                                                                model=self._name, res_id=task.id,
                                                                context=contex_signup)[partner_id]

crm_task()

class ir_attachment(osv.osv):
    
    _inherit = 'ir.attachment'
    
    def get_download_url(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = '/web/binary/saveas?model=ir.attachment&field=datas&filename_field=name&id=%s' %(str(rec.id),)
        return res
    
    _columns = {
        'download_url' : fields.function(get_download_url, type="char", string="Download URL")
    }
    
    def create(self, cr, uid, vals, context=None):
        ret_val = super(ir_attachment, self).create(cr, uid, vals, context=context)
        if vals.get('res_model', '') == 'crm.lead' and vals.get('res_id', False):
            user_rec = self.pool.get('res.users').browse(cr, uid, uid, context=context)
            msg_id = self.pool.get('crm.lead').message_post(cr, uid, vals.get('res_id', False), body='New Attachment added.', context=context)
            self.pool.get('mail.message').write(cr, uid, msg_id, {'attachment_ids' : [(4, ret_val)]}, context=context)
        return ret_val
    
ir_attachment()


class crm_case_stage(osv.osv):
    _inherit = "crm.case.stage"

    def _get_type_value(self, cr, user, context):
        return [('lead','Lead'),('opportunity','Opportunity'),('task','Task'),
                ('call','Call'),('meeting','Meeting')]

    _columns = {
            'type': fields.selection(_get_type_value, 'Type'),
    }

crm_case_stage()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: