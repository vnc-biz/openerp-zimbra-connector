# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from functools import partial
from datetime import datetime, timedelta, date
from dateutil import parser
import pytz
import re
import time
import hashlib

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
        for event_obj in self.pool.get('calendar.event').browse(cr, uid, event_ids):
            event = cal.add('vevent')
            if not event_obj.date_deadline or not event_obj.date:
                raise osv.except_osv(_('Warning!'),_("First you have to specify the date of the invitation."))
            event.add('CREATED').value = ics_datetime(time.strftime('%Y-%m-%d %H:%M:%S'))
            event.add('DTSTART').value = ics_datetime(event_obj.date)
            event.add('DTEND').value = ics_datetime(event_obj.date_deadline)
            if event_obj.write_date:
                event.add('DTSTAMP').value = ics_datetime(event_obj.write_date)
                event.add('LAST-MODIFIED').value = ics_datetime(event_obj.write_date)
            if event_obj.allday == True:
                event.add('X-MICROSOFT-CDO-ALLDAYEVENT').value = 'TRUE'
            else:
                event.add('X-MICROSOFT-CDO-ALLDAYEVENT').value = 'FALSE'
                
            if event_obj.show_as:
                event.add('X-MICROSOFT-CDO-INTENDEDSTATUS').value = event_obj.show_as
                
            event.add('UID').value = uid_generat('crmCalendar'+str(event_obj.id))
            event.add('SUMMARY').value = event_obj.name
            if  event_obj.description:
                event.add('DESCRIPTION').value = event_obj.description
            if event_obj.location:
                event.add('LOCATION').value = event_obj.location
                
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

class calendar_event(osv.osv):
    _inherit = 'calendar.event'
    _columns = {
                'create_date': fields.datetime('Creation Date'),
                'write_date': fields.datetime('Write Date'),
                }
calendar_event()