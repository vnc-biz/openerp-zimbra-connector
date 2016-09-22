# -*- coding: utf-8 -*-
import werkzeug
import functools
from openerp import http, SUPERUSER_ID
from openerp.http import request, Response

from icalendar import Calendar, Event, Todo
import datetime as DT
from datetime import date
import hashlib
import pytz
import urllib2
import time

def webservice(f):
    @functools.wraps(f)
    def wrap(*args, **kw):
        try:
            return f(*args, **kw)
        except Exception, e:
            return Response(response=str(e), status=500)
    return wrap

class ZimbraVNCController(http.Controller):

    @http.route('/calendar', type='http', auth='none')
    def zimbra_sync_calendar(self, **post):
        environ = request.httprequest.environ
        auth = environ.get('HTTP_AUTHORIZATION')
        if auth:
            scheme, data = auth.split(None, 1)
            assert scheme.lower() == 'basic'
            username, password = data.decode('base64').split(':', 1)
            username = urllib2.unquote(username)
            password = urllib2.unquote(password)
            query_str = environ.get('QUERY_STRING')
            para_final = query_str.split('=')
            uid = request.session.authenticate(para_final[1], username, password)
        if not request.session.uid:
            url = request.httprequest.url_root + "web/login" + "?redirect=" + "/calendar"
            redirect = werkzeug.utils.redirect(url, 303)
            redirect.autocorrect_location_header = True
            return redirect  
        cal_data = self.make_service_call('calendar')
        headers = [('cache-control', 'no-cache'), \
                        ('Pragma', 'no-cache'), \
                        ('Content-Type', 'text/calendar'), \
                        ('Content-length', len(cal_data)), \
                        ('Content-Disposition', 'attachment; filename='+\
                         'task_calender'+'.ics')]
        return request.make_response(cal_data, headers=headers)
    
    
    @http.route('/task', type='http', auth='none')
    def zimbra_sync_task(self, **post):
        environ = request.httprequest.environ
        auth = environ.get('HTTP_AUTHORIZATION')
        if auth:
            scheme, data = auth.split(None, 1)
            assert scheme.lower() == 'basic'
            username, password = data.decode('base64').split(':', 1)
            username = urllib2.unquote(username)
            password = urllib2.unquote(password)
            query_str = environ.get('QUERY_STRING')
            para_final = query_str.split('=')
            uid = request.session.authenticate(para_final[1], username, password)
        
        if not request.session.uid:
            url = request.httprequest.url_root + "web/login" + "?redirect=" + "/task"
            redirect = werkzeug.utils.redirect(url, 303)
            redirect.autocorrect_location_header = True
            return redirect
        cal_data = self.make_service_call('task')
        headers = [('cache-control', 'no-cache'), \
                        ('Pragma', 'no-cache'), \
                        ('Content-Type', 'text/calendar'), \
                        ('Content-length', len(cal_data)), \
                        ('Content-Disposition', 'attachment; filename='+\
                         'task_calender'+'.ics')]
        return request.make_response(cal_data, headers=headers)
        
    
    
    @http.route('/birthdaycalendar', type='http', auth='none')
    def zimbra_sync_birthday_calendar(self, **post):
        environ = request.httprequest.environ
        auth = environ.get('HTTP_AUTHORIZATION')
        if auth:
            scheme, data = auth.split(None, 1)
            assert scheme.lower() == 'basic'
            username, password = data.decode('base64').split(':', 1)
            username = urllib2.unquote(username)
            password = urllib2.unquote(password)
            query_str = environ.get('QUERY_STRING')
            para_final = query_str.split('=')
            uid = request.session.authenticate(para_final[1], username, password)
        if not request.session.uid:
            url = request.httprequest.url_root + "web/login" + "?redirect=" + "/birthdaycalendar"
            redirect = werkzeug.utils.redirect(url, 303)
            redirect.autocorrect_location_header = True
            return redirect  
        cal_data = self.make_service_call('birthdaycalendar')
        headers = [('cache-control', 'no-cache'), \
                        ('Pragma', 'no-cache'), \
                        ('Content-Type', 'text/calendar'), \
                        ('Content-length', len(cal_data)), \
                        ('Content-Disposition', 'attachment; filename='+\
                         'birthday_calendar'+'.ics')]
        return request.make_response(cal_data, headers=headers)
    
    
    @http.route(['/leavecalendar','/leavecalendar/<string:dbname>/<string:company_code>/','/leavecalendar/<string:db_name>/<string:company_code>/<string:employee_function>'], type='http', auth='none')
    def zimbra_sync_leave_calendar(self, dbname=None, company_code=None, employee_function=None, calendar_name=None):
        
        environ = request.httprequest.environ
        auth = environ.get('HTTP_AUTHORIZATION')
        if auth:
            scheme, data = auth.split(None, 1)
            assert scheme.lower() == 'basic'
            username, password = data.decode('base64').split(':', 1)            
            username = urllib2.unquote(username)
            password = urllib2.unquote(password)
            query_str = environ.get('QUERY_STRING')
            para_final = query_str.split('=')
            uid = request.session.authenticate(dbname, username, password)
            
        vals={}
        vals['company_code']= company_code or ''
        vals['employee_function'] = employee_function or ''
        vals['is_leave'] = True
#         if post.get('company_code'):
#             vals['company_code'] = post.get('company_code')
#         if post.get('calendar_name'):
#             calendar_name = post.get('calendar_name')
#         else:
#             calendar_name = 'leave_calendar'
#         if post.get('employee_function'):
#             vals['employee_function'] = post.get('employee_function')
#         if post.get('is_leave'):
#             vals['is_leave'] = post.get('is_leave')
#         else:
#             vals['is_leave'] = True
#         if post.get('is_allocation'):
#             vals['is_allocation'] = post.get('is_allocation')
                
        if not request.session.uid:
            url = request.httprequest.url_root + "web/login" + "?redirect=" + "/leavecalendar"
            redirect = werkzeug.utils.redirect(url, 303)
            redirect.autocorrect_location_header = True
            return redirect  
        cal_data = self.make_service_call('leavecalendar', vals)
        calendar_name = calendar_name or 'leavecalendar'
        headers = [('cache-control', 'no-cache'), \
                        ('Pragma', 'no-cache'), \
                        ('Content-Type', 'text/calendar'), \
                        ('Content-length', len(cal_data)), \
                        ('Content-Disposition', 'attachment; filename='+\
                         calendar_name+'.ics')]
        return request.make_response(cal_data, headers=headers)
    
    def get_lead_name(self, lead_id):
        lead_osv = request.registry.get('crm.lead')
        lead_data = lead_osv.read(request.cr, SUPERUSER_ID, lead_id, ['name', 'partner_id', 'contact_name'])        
        name= ''
        if lead_data['partner_id']:
            name = lead_data['partner_id'][1]
        elif lead_data['contact_name']:
            name = lead_data['contact_name']
        else:
            name = lead_data['name']
        
        return name


    def get_employee_data(self, employee_id, holiday_status_id):
        employee_osv = request.registry.get('hr.employee')
        employee_data = employee_osv.read(request.cr, SUPERUSER_ID, employee_id, ['name', 'job_id', 'first_name', 'last_name'])        
        name= ''
        if employee_data :
            employee_data =  employee_data[0]
            if employee_data['name']:
                name = employee_data['name']
            if holiday_status_id and holiday_status_id[1]:
                name = name + ' - ' + '(' + holiday_status_id[1] + ')'
            if employee_data['job_id']:
                name = name + ' - ' + employee_data['job_id'][1]       
        
        return name

    
    def make_service_call(self, option, vals=None):
        def uid_generat(data):# UID generat
            sha_obj = hashlib.sha1(data)
            return sha_obj.hexdigest()
        
        if vals is None:
            vals={}        
        if option == 'leavecalendar':
            employee_osv = request.registry.get('hr.employee')
            leave_osv = request.registry.get('hr.holidays')   
            domain = []         
            if vals.get('company_code'):
                domain += [('employee_id.company_id.code', '=', vals.get('company_code'))]
            if vals.get('is_leave') and vals.get('is_allocation'):
                domain += [('type', 'in', ('add', 'remove'))]
            else:
                if vals.get('is_leave'):
                    domain += [('type', '=', 'remove')]
                elif vals.get('is_allocation'):
                    domain += [('type', '=', 'add')]
            start_date = time.strftime('%Y-01-01 00:00:00')
            end_date = time.strftime('%Y-12-31 23:59:59')
            domain+= [('date_from', '>=', start_date), ('date_from', '<=', end_date), ('date_to', '>=', start_date), ('date_to', '<=', end_date), ('employee_id.active', '=', True)]
            leave_ids = leave_osv.search(request.cr, SUPERUSER_ID, domain)
            leave_data = leave_osv.read(request.cr, SUPERUSER_ID, leave_ids, ['id', 'employee_id', 'date_from', 'date_to', 'write_date', 'holiday_status_id', 'state'])

            def ics_datetime(idate):
                if idate:
                    #returns the datetime as UTC, because it is stored as it in the database
                    idate = idate.split('.', 1)[0]
                    return DT.datetime.strptime(idate,\
                         '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.timezone('UTC'))
                return False
    
            cal = Calendar()
            cal.add('PRODID', 'Zimbra-Calendar-Provider')
            cal.add('VERSION', '2.0')
            cal.add('METHOD', 'PUBLISH')
    
            for data in leave_data:
                name =""
                if 'employee_id' in data and data['employee_id']:
                    name = self.get_employee_data(data['employee_id'][0], data['holiday_status_id'])
                
                event = Event()
                event.add('summary', name)
                event.add('description', '')
                if data['date_from']:
                    event.add('DTSTART', ics_datetime(data['date_from']))
                if data['date_to']:
                    event.add('DTEND', ics_datetime(data['date_to']))
                if data['write_date']:
                    event.add('DTSTAMP', DT.datetime.strptime(data['write_date'],\
                                                              '%Y-%m-%d %H:%M:%S'))
                    event.add('LAST-MODIFIED', \
                    DT.datetime.strptime(data['write_date'], '%Y-%m-%d %H:%M:%S'))
                event['uid'] = uid_generat('employeeLeave'+str(data['id']))    
               
    
#                 if data['state'] == 'done':
#                     event.add('status', 'COMPLETED')
#                     event.add('PERCENT-COMPLETE', 100)
#                 elif data['state'] == 'cancel':
#                     event.add('status', 'DEFERRED')
#                 elif data['state'] == 'open':
#                     event.add('status', 'IN-PROCESS')
#                 else:
#                     event.add('status', 'NEEDS-ACTION')
#                     event.add('PERCENT-COMPLETE', 0) 
                cal.add_component(event)
            return cal.to_ical()
            
        if option == 'birthdaycalendar':
            emp_osv = request.registry.get('hr.employee')
            emp_ids = emp_osv.search(request.cr, SUPERUSER_ID, [])
            emp_data = emp_osv.read(request.cr, SUPERUSER_ID, emp_ids, ['id', 'first_name', 'last_name', 'birthday', 'write_date', 'started_career_vnc_on'])
            
            def ics_datetime(idate):
                if idate:
                    #returns the datetime as UTC, because it is stored as it in the database
                    idate = idate.split('.', 1)[0]
                    return DT.datetime.strptime(idate,\
                         '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.timezone('UTC'))
                return False
            
            cal = Calendar()
            cal.add('PRODID', 'Zimbra-Calendar-Provider')
            cal.add('VERSION', '2.0')
            cal.add('METHOD', 'PUBLISH')
            cal.add('RRULE', {'FREQ':'YEARLY', 'BYMONTH': 11, 'BYDAY': '1su'})
    
            for data in emp_data:                
                if 'birthday' in data and data['birthday']:
                    event = Event()
                    event.add('CREATED', date.today())
                    event.add('DTSTART', DT.datetime.combine(DT.datetime.strptime(data['birthday'], '%Y-%m-%d'), DT.time.min))
                    event.add('DTEND', DT.datetime.combine(DT.datetime.strptime(data['birthday'], '%Y-%m-%d'), DT.time.min))
                    event.add('X-MICROSOFT-CDO-ALLDAYEVENT', 'TRUE')
                    if data['write_date']:
                        event.add('DTSTAMP', DT.datetime.strptime(data['write_date'],\
                                                                   '%Y-%m-%d %H:%M:%S'))
                        event.add('LAST-MODIFIED', \
                        DT.datetime.strptime(data['write_date'], '%Y-%m-%d %H:%M:%S'))
#                     if data['show_as']:
#                         event.add('X-MICROSOFT-CDO-INTENDEDSTATUS', data['show_as'])
                    event.add('UID', uid_generat('crmBirthdayCalendar'+str(data['id'])))
                    event.add('RRULE', {'FREQ':'YEARLY', 'INTERVAL': 1}) 
                    name = data['first_name'] + " " + data['last_name']+"'s Birthday"
                    event.add('SUMMARY', name)
#                     if data['description']:
#                         event.add('DESCRIPTION', data['description'])
#                     if data['location']:
#                         event.add('LOCATION', data['location'])
                    cal.add_component(event)
                    
                if 'started_career_vnc_on' in data and data['started_career_vnc_on']:
                    event = Event()
                    event.add('CREATED', date.today())
                    event.add('DTSTART', DT.datetime.combine(DT.datetime.strptime(data['started_career_vnc_on'], '%Y-%m-%d'), DT.time.min))
                    event.add('DTEND', DT.datetime.combine(DT.datetime.strptime(data['started_career_vnc_on'], '%Y-%m-%d'), DT.time.max))
                    event.add('X-MICROSOFT-CDO-ALLDAYEVENT', 'TRUE')
                    if data['write_date']:
                        event.add('DTSTAMP', DT.datetime.strptime(data['write_date'],\
                                                                   '%Y-%m-%d %H:%M:%S'))
                        event.add('LAST-MODIFIED', \
                        DT.datetime.strptime(data['write_date'], '%Y-%m-%d %H:%M:%S'))
#                     if data['show_as']:
#                         event.add('X-MICROSOFT-CDO-INTENDEDSTATUS', data['show_as'])
                    event.add('UID', uid_generat('crmAnniversaryCalendar'+str(data['id'])))
                    event.add('RRULE', {'FREQ':'YEARLY', 'INTERVAL': 1}) 
                    name = data['first_name'] + " " + data['last_name']+"'s Anniversary at VNC"
                    event.add('SUMMARY', name)
#                     if data['description']:
#                         event.add('DESCRIPTION', data['description'])
#                     if data['location']:
#                         event.add('LOCATION', data['location'])
                    cal.add_component(event)
            return cal.to_ical()
        
            
        if option == 'task':
            task_osv = request.registry.get('crm.task')
            task_ids = task_osv.search(request.cr, SUPERUSER_ID, [('task_type', '=', 't'), ('user_id', '=', request.session.uid), ('state', '!=', 'cancel')])
#             task_ids = sock.execute(dbname, uid, pwd, 'crm.task', 'search',\
#                              [('task_type', '=', 't'), ('user_id', '=', uid), ('state', '!=', 'cancel')])
            task_data = task_osv.read(request.cr, SUPERUSER_ID, task_ids, ['name','description','start_datetime','stop_datetime',\
                         'priority','state','location','write_date'])
#             task_data = sock.execute(dbname, uid, pwd, 'crm.task', 'read', task_ids,\
#                         ['name','description','start_datetime','stop_datetime',\
#                          'priority','state','location','write_date'])
    
            def ics_datetime(idate):
                if idate:
                    #returns the datetime as UTC, because it is stored as it in the database
                    idate = idate.split('.', 1)[0]
                    return DT.datetime.strptime(idate,\
                         '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.timezone('UTC'))
                return False
    
            cal = Calendar()
            cal.add('PRODID', 'Zimbra-Calendar-Provider')
            cal.add('VERSION', '2.0')
            cal.add('METHOD', 'PUBLISH')
    
            for data in task_data:
                todo = Todo()
                todo.add('summary', data['name'])
                todo.add('description', data['description'])
                if data['start_datetime']:
                    todo.add('DTSTART', ics_datetime(data['start_datetime']))
                else:
                    todo.add('DTSTART', ics_datetime(data['stop_datetime']))
                if data['stop_datetime']:
                    todo.add('DUE', ics_datetime(data['stop_datetime']))
                else:
                    todo.add('DUE', ics_datetime(data['start_datetime']))
                if data['write_date']:
                    todo.add('DTSTAMP', DT.datetime.strptime(data['write_date'],\
                                                              '%Y-%m-%d %H:%M:%S'))
                    todo.add('LAST-MODIFIED', \
                    DT.datetime.strptime(data['write_date'], '%Y-%m-%d %H:%M:%S'))
                todo['uid'] = uid_generat('crmTask'+str(data['id']))
    
                if data['priority'] == 'low':
                    todo.add('priority', 9)
                elif data['priority'] == 'medium':
                    todo.add('priority', 5)
                elif data['priority'] == 'high':
                    todo.add('priority', 1)
                else:
                    todo.add('priority', 5)
    
                if data['state'] == 'done':
                    todo.add('status', 'COMPLETED')
                    todo.add('PERCENT-COMPLETE', 100)
                elif data['state'] == 'cancel':
                    todo.add('status', 'DEFERRED')
                elif data['state'] == 'open':
                    todo.add('status', 'IN-PROCESS')
                else:
                    todo.add('status', 'NEEDS-ACTION')
                    todo.add('PERCENT-COMPLETE', 0)
                cal.add_component(todo)
            return cal.to_ical()
        else:
            calendar_osv = request.registry.get('calendar.event')
            event_ids = calendar_osv.search(request.cr, SUPERUSER_ID, [('user_id','=',request.session.uid)])
            
    #         event_ids = sock.execute(dbname, uid, pwd, 'calendar.event', 'search',\
    #                                  [('user_id','=',uid)])
            
            event_data = calendar_osv.read(request.cr, SUPERUSER_ID, event_ids, ['show_as','allday','name','description',\
                                    'start_datetime','stop_datetime','location','write_date','start_date','stop_date'])
            
            transition_osv = request.registry.get('crm.activity.transition')
            transition_ids = transition_osv.search(request.cr, SUPERUSER_ID, [('user_id','=',request.session.uid)])
            
    #         event_ids = sock.execute(dbname, uid, pwd, 'calendar.event', 'search',\
    #                                  [('user_id','=',uid)])
            
            transition_data = transition_osv.read(request.cr, SUPERUSER_ID, transition_ids, ['show_as','allday','name','description',\
                                    'start_datetime','stop_datetime','location','write_date','start_date','stop_date', 'lead_id'])
            
            event_data.extend(transition_data)
            
    #         event_data = sock.execute(dbname, uid, pwd, 'calendar.event', 'read',\
    #                      event_ids,['show_as','allday','name','description',\
    #                                 'start_datetime','stop_datetime','location','write_date','start_date','stop_date'])
    #                             'start','stop','location','write_date'])
            def ics_datetime(idate):
                if idate:
                    #returns the datetime as UTC, because it is stored as it in the database
                    return DT.datetime.strptime(idate,\
                         '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.timezone('UTC'))
                return False
    
            cal = Calendar()
            cal.add('PRODID', 'Zimbra-Calendar-Provider')
            cal.add('VERSION', '2.0')
            cal.add('METHOD', 'PUBLISH')
            for data in event_data:
                name =""
                lead_link = ""
                if 'lead_id' in data and data['lead_id']:
                    name = self.get_lead_name(data['lead_id'][0])
                    lead_link = "Goto Lead / Opportunity : " +request.registry.get('crm.lead').get_signup_url_reminder_1(request.cr, SUPERUSER_ID, data['lead_id'][0]) +"\n\n"
                event = Event()                
                if data['allday']:
                    event.add('CREATED', date.today())
                    if data['start_date']:
                        data['start_date'] = data['start_date'].split(" ")[0]                        
                        event.add('DTSTART', DT.datetime.combine(DT.datetime.strptime(data['start_date'], '%Y-%m-%d'), DT.time.min))
                    if data['stop_date']:
                        data['stop_date'] = data['stop_date'].split(" ")[0]
                        event.add('DTEND', DT.datetime.combine(DT.datetime.strptime(data['stop_date'], '%Y-%m-%d'), DT.time.max))
                    event.add('X-MICROSOFT-CDO-ALLDAYEVENT', 'TRUE')
                else:
                    event.add('CREATED', date.today())
                    if data['start_datetime']:
                        event.add('DTSTART', ics_datetime(data['start_datetime']))
                    if data['stop_datetime']:
                        event.add('DTEND', ics_datetime(data['stop_datetime']))
                    event.add('X-MICROSOFT-CDO-ALLDAYEVENT', 'FALSE')
                if data['write_date']:
                    event.add('DTSTAMP', DT.datetime.strptime(data['write_date'],\
                                                               '%Y-%m-%d %H:%M:%S'))
                    event.add('LAST-MODIFIED', \
                    DT.datetime.strptime(data['write_date'], '%Y-%m-%d %H:%M:%S'))
                if data['show_as']:
                    event.add('X-MICROSOFT-CDO-INTENDEDSTATUS', data['show_as'])
                event.add('UID', uid_generat('crmCalendar'+str(data['id'])))
                name = name+', '+data['name'] if name else data['name']
                event.add('SUMMARY', name)
                if data['description'] or lead_link:
                    desc = data['description'] or ""
                    event.add('DESCRIPTION', lead_link +desc)
                if data['location']:
                    event.add('LOCATION', data['location'])
                cal.add_component(event)
            
            return cal.to_ical()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
