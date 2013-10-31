# -*- coding: utf-8 -*-
from openerp.service import wsgi_server
import xmlrpclib
from icalendar import Calendar, Event, Todo
import datetime as DT
from datetime import date
import hashlib
import openerp
import pytz
import urllib2


def xmlrpc_return(start_response, service, method, params, legacy_exceptions=False):
    """
    Helper to call a service's method with some params, using a wsgi-supplied
    ``start_response`` callback.

    This is the place to look at to see the mapping between core exceptions
    and XML-RPC fault codes.
    """
    # Map OpenERP core exceptions to XML-RPC fault codes. Specific exceptions
    # defined in ``openerp.exceptions`` are mapped to specific fault codes;
    # all the other exceptions are mapped to the generic
    # RPC_FAULT_CODE_APPLICATION_ERROR value.
    # This also mimics SimpleXMLRPCDispatcher._marshaled_dispatch() for
    # exception handling.
    
    try:
        result = openerp.netsvc.dispatch_rpc(service, method, params)
        if service == 'db':
            import re
            r = openerp.tools.config['dbfilter']
            result = [i for i in result if re.match(r, i)]
        response = xmlrpclib.dumps((result,), methodresponse=1, allow_none=False, encoding=None)
    except Exception, e:
        if legacy_exceptions:
            response = wsgi_server.xmlrpc_handle_exception_legacy(e)
        else:
            response = wsgi_server.xmlrpc_handle_exception(e)
    start_response("200 OK", [('Content-Type','text/xml'), ('Content-Length', str(len(response)))])
    return [response]

def application(environ, start_response):
    if environ.get('PATH_INFO') in ['/task', '/calendar']:
        if not environ.get('HTTP_AUTHORIZATION'):
            start_response("401 Authorization required",
                           [('WWW-Authenticate', 'Basic realm="OpenERP"'),
                            ('cache-control', 'no-cache'),
                            ('Pragma', 'no-cache'),
                            ('Expires', 0),
                            ('Content-Type', 'text/html'),
                            ('Content-Length', 4),  # len(self.auth_required_msg)
                            ])
            return environ
        auth = environ.get('HTTP_AUTHORIZATION')
        if auth:
            scheme, data = auth.split(None, 1)
            assert scheme.lower() == 'basic'
            username, password = data.decode('base64').split(':', 1)
            username = urllib2.unquote(username)
            password = urllib2.unquote(password)
            query_str = environ.get('QUERY_STRING')
            para_final = query_str.split('=')
            cal_data = ''
            try:
                if environ.get('PATH_INFO') == '/task':
                    cal_data = make_service_call(environ.get('SERVER_NAME'), environ.get('SERVER_PORT'), username, password, para_final[1], 'task')
                elif environ.get('PATH_INFO') == '/calendar':
                    cal_data = make_service_call(environ.get('SERVER_NAME'), environ.get('SERVER_PORT'), username, password, para_final[1], 'calendar')
                else:
                    body = 'Invalid URL'
                    headers = [
                               ('content-type', 'text/plain'),
                               ('content-length', str(len(body))),
                               ('WWW-Authenticate', 'Basic realm="OpenERP"')
                               ]
                    start_response('400 BAD REQUEST', headers)
                    return [body]
            except:
                body = 'Please authenticate'
                headers = [
                    ('content-type', 'text/plain'),
                    ('content-length', str(len(body))),
                    ('WWW-Authenticate', 'Basic realm="OpenERP"')]
                start_response('401 Unauthorized', headers)
                return [body]
            
            environ['REMOTE_USER'] = username
            del environ['HTTP_AUTHORIZATION']
        start_response("200 OK", [('cache-control', 'no-cache'), ('Pragma', 'no-cache'), ('Expires', 0), ('Content-Type', 'text/calendar'), ('Content-length', len(cal_data)), ('Content-Disposition', 'attachment; filename='+'task_calender'+'.ics')])
        return cal_data
    if wsgi_server.config['proxy_mode'] and 'HTTP_X_FORWARDED_HOST' in environ:
        return wsgi_server.werkzeug.contrib.fixers.ProxyFix(wsgi_server.application_unproxied)(environ, start_response)
    else:
        return wsgi_server.application_unproxied(environ, start_response)


def make_service_call(host, port, username, pwd, dbname, option):
    
    def uid_generat(data):  # UID generat
        sha_obj = hashlib.sha1(data)
        return sha_obj.hexdigest()
    
    sock_common = xmlrpclib.ServerProxy('http://'+host+':'+port+'/xmlrpc/common')
    uid = sock_common.login(dbname, username, pwd)
    sock = xmlrpclib.ServerProxy('http://'+host+':'+port+'/xmlrpc/object')
    if option == "task":
        task_ids = sock.execute(dbname, uid, pwd, 'crm.task', 'search', [('task_type', '=', 't'), ('user_id', '=', uid)])
        task_data = sock.execute(dbname, uid, pwd, 'crm.task', 'read', task_ids,['name','description','date','date_deadline','priority','state','location','write_date'])
        
        cal = Calendar()
        cal.add('PRODID', 'Zimbra-Calendar-Provider')
        cal.add('VERSION', '2.0')
        cal.add('METHOD', 'PUBLISH')
        
        for data in task_data:
            todo = Todo()
            todo.add('summary', data['name'])
            todo.add('description', data['description'])
            if data['date']:
                todo.add('DTSTART', DT.datetime.strptime(data['date'], '%Y-%m-%d %H:%M:%S').date())
            if data['date_deadline']:
                todo.add('DUE', DT.datetime.strptime(data['date_deadline'], '%Y-%m-%d %H:%M:%S').date())
            if data['write_date']:
                todo.add('DTSTAMP', DT.datetime.strptime(data['write_date'], '%Y-%m-%d %H:%M:%S'))
                todo.add('LAST-MODIFIED', DT.datetime.strptime(data['write_date'], '%Y-%m-%d %H:%M:%S'))
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
                todo.add('status', 'Deffered')
            elif data['state'] == 'open':
                todo.add('status', 'In Progress')
            else:
                todo.add('status', 'NEEDS-ACTION')
                todo.add('PERCENT-COMPLETE', 0)
            cal.add_component(todo)
        return cal.to_ical()
    else:
        event_ids = sock.execute(dbname, uid, pwd, 'calendar.event', 'search', [('user_id','=',uid)])
        event_data = sock.execute(dbname, uid, pwd, 'calendar.event', 'read', event_ids,['show_as','allday','name','description','date','date_deadline','location','write_date'])
        
        def ics_datetime(idate):
            if idate:
                #returns the datetime as UTC, because it is stored as it in the database
                return DT.datetime.strptime(idate, '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.timezone('UTC'))
            return False

        cal = Calendar()
        cal.add('PRODID', 'Zimbra-Calendar-Provider')
        cal.add('VERSION', '2.0')
        cal.add('METHOD', 'PUBLISH')
        for data in event_data:
            event = Event()
            if data['date_deadline'] and data['date'] and data['allday']:                
                event.add('CREATED', date.today())
                event.add('DTSTART', ics_datetime(data['date']))
                event.add('DTEND', ics_datetime(data['date_deadline']))
                event.add('X-MICROSOFT-CDO-ALLDAYEVENT', 'TRUE')
            else:
                event.add('CREATED', date.today())
                event.add('DTSTART', ics_datetime(data['date']))
                event.add('DTEND', ics_datetime(data['date_deadline']))
                event.add('X-MICROSOFT-CDO-ALLDAYEVENT', 'FALSE')
            if data['write_date']:
                event.add('DTSTAMP', DT.datetime.strptime(data['write_date'], '%Y-%m-%d %H:%M:%S'))
                event.add('LAST-MODIFIED', DT.datetime.strptime(data['write_date'], '%Y-%m-%d %H:%M:%S'))
            if data['show_as']:
                event.add('X-MICROSOFT-CDO-INTENDEDSTATUS', data['show_as'])
            event.add('UID', uid_generat('crmCalendar'+str(data['id'])))
            event.add('SUMMARY', data['name'])
            if data['description']:
                event.add('DESCRIPTION', data['description'])
            if data['location']:
                event.add('LOCATION', data['location'])
            cal.add_component(event)
        return cal.to_ical()

wsgi_server.application = application
wsgi_server.xmlrpc_return = xmlrpc_return
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: