# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from functools import partial
from datetime import datetime, timedelta, date
from dateutil import parser
import pytz
import re
import time
import hashlib

class partner_responsibility(osv.osv):
    _name='partner.responsibility'
    _columns={
              'name':fields.char('Name',size=256, required=True),
              'description':fields.char('Description',size=256),
              }

partner_responsibility()

class crm_meeting(osv.osv):
    """ CRM Meeting Cases """
    _order = 'date asc'

    _inherit = 'crm.meeting'

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
        'vtimezone': lambda s, cr, uid, c: s.pool.get('res.users').browse(cr, uid, uid, context=c).tz,
    }

crm_meeting()

class crm_lead(osv.osv):
    _inherit = 'crm.lead'
    _columns = {
                'lead_add_line': fields.one2many('lead.address.line', 'lead_id',
                                                 'Lead Address Line'),
                }

crm_lead()

class lead_address_line(osv.osv):
    _description = "Contact"
    _name = "lead.address.line"
    _rec_name='partner_address_id'
    _columns = {
                'lead_id':fields.many2one("crm.lead",'Lead'),
                'partner_address_id':fields.many2one('res.partner', 'Contact Adress'),
                'phone': fields.char('Phone', size=32),
                'fax': fields.char('Fax', size=32),
                'email': fields.char('E-mail', size=32),
                'mobile': fields.char('Mobile', size=32),
                'responsibility': fields.many2one('partner.responsibility','Responsibility'),
                }

    def onchange_partner_address_id(self,cr,uid,ids,partner_address_id,context=None):
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
            address_obj = address_pool.browse(cr,uid,partner_address_id,context=context)
            res['phone']=address_obj.phone
            res['fax']= address_obj.fax
            res['email']= address_obj.email
            res['mobile']= address_obj.mobile
        return {'value':res}

    def search_read(self, cr, uid, domain, fields=[], context={}):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user ID for security checks,
        @param domain: Condition to filter on
        @param fields: list of fields to read
        @param context: A standard dictionary for contextual values
        """
        ids = self.search(cr, uid, domain, context=context)
        read_data = lead_data = []
        lead_pool = self.pool.get('crm.lead')
        if ids:
            read_data = self.read(cr, uid, ids, fields=fields, context=context)
            lead_ids = [data['lead_id'][0] for data in read_data if data['lead_id']]
            if lead_ids:
                lead_data = lead_pool.read(cr,uid,lead_ids)
        return lead_data

lead_address_line()

def search_read(self, cr, uid, domain, fields=[], context={}):
    """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user ID for security checks,
        @param domain: Condition to filter on
        @param fields: list of fields to read
        @param context: A standard dictionary for contextual values
    """
    ids = self.search(cr, uid, domain, context=context)
    read_data = []
    if ids:
        read_data = self.read(cr, uid, ids, fields=fields, context=context)
    return read_data

osv.osv.search_read = search_read

class res_users(osv.osv):
    """ Base User Class is inherited for Region Management """

    _inherit = 'res.users'
    
    
    def get_ics_file(self, cr, uid, event_ids, context=None):
        """
        Returns iCalendar file for the event invitation.
        @param self: the object pointer
        @param cr: the current row, from the database cursor
        @param uid: the current user's id for security checks
        @param event_obj: event object (browse record)
        @param context: a standard dictionary for contextual values
        @return: .ics file content
        """
        res = None
        def uid_generat(data):  #UID generat
            sha_obj = hashlib.sha1(data)
            return sha_obj.hexdigest()
    
        def ics_datetime(idate, short=False):
            if idate:
                #returns the datetime as UTC, because it is stored as it in the database
                return datetime.strptime(idate, '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.timezone('UTC'))
            return False
        try:
            # FIXME: why isn't this in CalDAV?
            import vobject
        except ImportError:
            return res

        cal = vobject.iCalendar()
        for event_obj in self.pool.get('crm.meeting').browse(cr, uid, event_ids):
            event = cal.add('vevent')
            if not event_obj.date_deadline or not event_obj.date:
                raise osv.except_osv(_('Warning!'),_("First you have to specify the date of the invitation."))
            event.add('created').value = ics_datetime(time.strftime('%Y-%m-%d %H:%M:%S'))
            event.add('dtstart').value = ics_datetime(event_obj.date)
            event.add('dtend').value = ics_datetime(event_obj.date_deadline)
            event.add('uid').value = uid_generat('crmCalendar'+str(event_obj.id))
            event.add('summary').value = event_obj.name
            if  event_obj.description:
                event.add('description').value = event_obj.description
            if event_obj.location:
                event.add('location').value = event_obj.location
                
            if event_obj.alarm_id:
                # computes alarm data
                valarm = event.add('valarm')
                alarm_object = self.pool.get('res.alarm')
                alarm_data = alarm_object.read(cr, uid, event_obj.alarm_id.id, context=context)
                # Compute trigger data
                interval = alarm_data['trigger_interval']
                occurs = alarm_data['trigger_occurs']
                duration = (occurs == 'after' and alarm_data['trigger_duration']) \
                                                or -(alarm_data['trigger_duration'])
                related = alarm_data['trigger_related']
                trigger = valarm.add('TRIGGER')
                trigger.params['related'] = [related.upper()]
                if interval == 'days':
                    delta = timedelta(days=duration)
                if interval == 'hours':
                    delta = timedelta(hours=duration)
                if interval == 'minutes':
                    delta = timedelta(minutes=duration)
                trigger.value = delta
                # Compute other details
                valarm.add('DESCRIPTION').value = alarm_data['name'] or 'OpenERP'
    
        res = cal.serialize()
        return res
res_users()