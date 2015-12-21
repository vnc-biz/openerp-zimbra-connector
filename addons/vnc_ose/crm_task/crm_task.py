# -*- coding: utf-8 -*-
from base_calendar import base_calendar
from openerp.addons.base_status.base_state import base_state
from osv import fields, osv
from tools.translate import _
import logging
from crm import crm
from datetime import datetime, timedelta, date
import time


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


class crm_task(base_state,osv.osv):
    """ CRM task Cases """
    _name = 'crm.task'
    _description = "Task"
    _order = "date asc"
    _inherit = ["calendar.event"]
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

    def write(self, cr, uid, ids, vals, context={}):
        if not isinstance(ids, (list,tuple)):
            ids = [ids]
        old_datas = self.read(cr, uid, ids, ['user_id','date','date_deadline'],\
                    context=context)
        for old_data in old_datas:
            if not old_data['user_id'] or ('user_id' in vals and \
                                    vals['user_id'] != old_data['user_id'][0]):
                vals['user_delegated_id'] = uid
                self.check_fields(cr, uid, old_data['id'], vals, context)
            # Copying date to date_deadline if it is False, calling onchage will return the date_deadline
            if not old_data['date_deadline'] and old_data['date']:
                date = self.browse(cr, uid, ids[0]).date
                data = self.onchange_dates(cr, uid, ids[0], date, duration=2,\
                                            context=context)
                vals.update(data['value'])
        return super(crm_task, self).write(cr, uid, ids, vals, context=context)

    def read_group(self,cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        res = super(osv.osv, self).read_group(cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby, lazy=lazy)
        return res

    def create(self, cr, uid, vals, context={}):
        if vals and 'user_id' in vals and vals['user_id'] != uid:
            vals['user_delegated_id'] = uid

        res = super(crm_task, self).create(cr, uid, vals, context=context)
        if vals and 'user_id' in vals and vals['user_id'] != uid:
            self.check_fields(cr, uid, res, vals, context)
        # Copying date to date_deadline if it is False, calling onchage will return the date_deadline
        if vals.get('date_deadline',False) == False:
            if vals.get('date',False):
                data = self.onchange_dates(cr, uid, [], vals['date'],\
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
        if res and res.has_key('user_id'):
            res['section_id'] = self.pool.get('res.users').browse(cr, uid, \
                                                res['user_id']).section_id.id
        else:
            res['section_id'] = self.pool.get('crm.case.section').search(cr, uid,\
                                         [('name','=','Sales Department')])[0]

        if context and 'default_opportunity_id' in context and \
                                            context['default_opportunity_id']:
            crm_pool = self.pool.get('crm.lead')
            crm_Data = crm_pool.read(cr, uid , \
                                     int(context['default_opportunity_id']),\
                                     ['partner_id','partner_address_id'])
            res['partner_id'] = crm_Data['partner_id'] and \
                                crm_Data['partner_id'][0] or False
            context['default_partner_address_id'] = False
            context['default_partner_id'] = res['partner_id']

        if context and context.get('default_partner_address_id',False):
            read_data = self.pool.get('res.partner').read(cr, uid,\
                        context.get('default_partner_address_id'))
            f_name = self.pool.get('res.partner').read(cr, uid,\
                        context.get('default_partner_address_id'), ['name'])
            res['first_name'] = f_name['name']
            res['partner_id'] = read_data['partner_id'] and \
                                read_data['partner_id'][0] or False
            context['default_partner_id'] = res['partner_id']

        if context and context.get("default_partner_id",False):
            onchange_val = self.onchange_partner_id(cr, uid, [],\
                                            context.get("default_partner_id"))
            res.update(onchange_val['value'])
            addr = self.pool.get('res.partner').address_get(cr, uid,\
                [int(context.get("default_partner_id"))], ['contact','default'])
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

    _columns = {
        # From crm.case
        'crm_id':fields.char('CRM ID',size=256),
        'name': fields.char('Summary', size=124),
        'date': fields.datetime("Date"),
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
        'date_deadline': fields.datetime('Deadline', \
                                         states={'done': [('readonly', True)]}),
        'priority': fields.selection([
                                      ('high','High'),
                                      ('medium','Medium'),
                                      ('low','Low') ], 'Priority'),
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
        'meeting_id':fields.many2one('crm.meeting','Meetings'),
        'owner_changed':fields.boolean('Owner Changed'),
        'short_description': fields.function(_set_short_desc, type='text',\
                            method=True, string='Short Description',),
        'current_datetime':fields.function(_get_current_datetime, method=True,\
                            type='datetime', string='Current DateTime',\
                            readonly=True,help="It represents Current Datetime"),
    }

    def _check_end_date(self, cr, uid, ids, context=None):
        ''' Validating the Task End Date: Task End Date should be greater than Start Date '''
        for task_obj in self.browse(cr, uid, ids, context=context):
            if task_obj.date and task_obj.date_deadline:
                if task_obj.date_deadline.split(' ')[0] \
                    < task_obj.date.split(' ')[0]:
                    return False
        return True

    _constraints = [
        (_check_end_date, '\n"Task End Date" must be greater than\
                         "Task Start Date".',\
                         ['date_deadline']),
    ]

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
            value['date_deadline'] = end.strftime("%Y-%m-%d %H:%M:%S")
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
    }

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
                id=base_calendar.base_calendar_id2real_id(id)
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
                id=base_calendar.base_calendar_id2real_id(id)
                self.log(cr, uid, id, message)

        self.write(cr, uid, ids, {'date_closed': \
                                  time.strftime('%Y-%m-%d %H:%M:%S')})
        cases = self.browse(cr, uid, ids)
        for case in cases:
            data = {'state': 'done', 'active': True}
            if not case.user_id:
                data['user_id'] = uid
            self.write(cr, uid, case.id, data)
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
        self.write(cr, uid, task_ids, {'owner_changed':False})
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

crm_task()


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