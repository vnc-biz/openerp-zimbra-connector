# -*- coding: utf-8 -*-
from openerp.service import wsgi_server
import xmlrpclib
from icalendar import Calendar, Event, Todo
import datetime as DT
from datetime import date
import hashlib

import werkzeug.serving
import werkzeug.contrib.fixers

import openerp
import pytz
import urllib2
import threading

def wsgi_xmlrpc(environ, start_response):
    """ Two routes are available for XML-RPC

    /xmlrpc/<service> route returns faultCode as strings. This is a historic
    violation of the protocol kept for compatibility.

    /xmlrpc/2/<service> is a new route that returns faultCode as int and is
    therefore fully compliant.
    """
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
                    cal_data = make_service_call(environ.get('SERVER_NAME'), \
                                environ.get('SERVER_PORT'), username, \
                                password, para_final[1], 'task')
                elif environ.get('PATH_INFO') == '/calendar':
                    cal_data = make_service_call(environ.get('SERVER_NAME'), \
                                environ.get('SERVER_PORT'), username, \
                                password, para_final[1], 'calendar')
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
        start_response("200 OK", [('cache-control', 'no-cache'), \
                        ('Pragma', 'no-cache'), ('Expires', 0), \
                        ('Content-Type', 'text/calendar'), \
                        ('Content-length', len(cal_data)), \
                        ('Content-Disposition', 'attachment; filename='+\
                         'task_calender'+'.ics')])
        return cal_data
    if environ['REQUEST_METHOD'] == 'POST' and environ['PATH_INFO'].startswith('/xmlrpc/'):
        length = int(environ['CONTENT_LENGTH'])
        data = environ['wsgi.input'].read(length)

        # Distinguish betweed the 2 faultCode modes
        string_faultcode = True
        if environ['PATH_INFO'].startswith('/xmlrpc/2/'):
            service = environ['PATH_INFO'][len('/xmlrpc/2/'):]
            string_faultcode = False
        else:
            service = environ['PATH_INFO'][len('/xmlrpc/'):]

        params, method = xmlrpclib.loads(data)
        return wsgi_server.xmlrpc_return(start_response, service, method, params, string_faultcode)

def application_unproxied(environ, start_response):
    """ WSGI entry point."""
    # cleanup db/uid trackers - they're set at HTTP dispatch in
    # web.session.OpenERPSession.send() and at RPC dispatch in
    # openerp.service.web_services.objects_proxy.dispatch().
    # /!\ The cleanup cannot be done at the end of this `application`
    # method because werkzeug still produces relevant logging afterwards 
    if hasattr(threading.current_thread(), 'uid'):
        del threading.current_thread().uid
    if hasattr(threading.current_thread(), 'dbname'):
        del threading.current_thread().dbname

    with openerp.api.Environment.manage():
        # Try all handlers until one returns some result (i.e. not None).
        wsgi_handlers = [wsgi_server.wsgi_xmlrpc]
        wsgi_handlers += wsgi_server.module_handlers
        for handler in wsgi_handlers:
            result = handler(environ, start_response)
            if result is None:
                continue
            return result

    # We never returned from the loop.
    response = 'No handler found.\n'
    start_response('404 Not Found', [('Content-Type', 'text/plain'), ('Content-Length', str(len(response)))])
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
                    cal_data = make_service_call(environ.get('SERVER_NAME'), \
                                environ.get('SERVER_PORT'), username, \
                                password, para_final[1], 'task')
                elif environ.get('PATH_INFO') == '/calendar':
                    cal_data = make_service_call(environ.get('SERVER_NAME'), \
                                environ.get('SERVER_PORT'), username, \
                                password, para_final[1], 'calendar')
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
        start_response("200 OK", [('cache-control', 'no-cache'), \
                        ('Pragma', 'no-cache'), ('Expires', 0), \
                        ('Content-Type', 'text/calendar'), \
                        ('Content-length', len(cal_data)), \
                        ('Content-Disposition', 'attachment; filename='+\
                         'task_calender'+'.ics')])
        return cal_data
    if wsgi_server.config['proxy_mode'] and 'HTTP_X_FORWARDED_HOST' in environ:
        return wsgi_server.werkzeug.contrib.fixers.ProxyFix\
                (wsgi_server.application_unproxied)(environ, start_response)
    else:
        return wsgi_server.application_unproxied(environ, start_response)

def make_service_call(host, port, username, pwd, dbname, option):
    def uid_generat(data):# UID generat
        sha_obj = hashlib.sha1(data)
        return sha_obj.hexdigest()
    if host == '1' and port == '1':
        sock_common = xmlrpclib.ServerProxy('http://127.0.0.1:8069/xmlrpc/common')
        uid = sock_common.login(dbname, username, pwd)
        sock = xmlrpclib.ServerProxy('http://127.0.0.1:8069/xmlrpc/object')
    else:
        sock_common = xmlrpclib.ServerProxy('http://'+host+':'+port+'/xmlrpc/common')
        uid = sock_common.login(dbname, username, pwd)
        sock = xmlrpclib.ServerProxy('http://'+host+':'+port+'/xmlrpc/object')
    if option == "task":
        task_ids = sock.execute(dbname, uid, pwd, 'crm.task', 'search',\
                             [('task_type', '=', 't'), ('user_id', '=', uid), ('state', '!=', 'cancel')])
        task_data = sock.execute(dbname, uid, pwd, 'crm.task', 'read', task_ids,\
                    ['name','description','start_datetime','stop_datetime',\
                     'priority','state','location','write_date'])

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
        event_ids = sock.execute(dbname, uid, pwd, 'calendar.event', 'search',\
                                 [('user_id','=',uid)])
        event_data = sock.execute(dbname, uid, pwd, 'calendar.event', 'read',\
                     event_ids,['show_as','allday','name','description',\
                                'start_datetime','stop_datetime','location','write_date','start_date','stop_date'])
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
            event = Event()
            if data['allday']:
                event.add('CREATED', date.today())
                event.add('DTSTART', DT.datetime.combine(DT.datetime.strptime(data['start_date'], '%Y-%m-%d'), DT.time.min))
                event.add('DTEND', DT.datetime.combine(DT.datetime.strptime(data['stop_date'], '%Y-%m-%d'), DT.time.max))
                event.add('X-MICROSOFT-CDO-ALLDAYEVENT', 'TRUE')
            else:
                event.add('CREATED', date.today())
                event.add('DTSTART', ics_datetime(data['start_datetime']))
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
            event.add('SUMMARY', data['name'])
            if data['description']:
                event.add('DESCRIPTION', data['description'])
            if data['location']:
                event.add('LOCATION', data['location'])
            cal.add_component(event)
        return cal.to_ical()

wsgi_server.application_unproxied = application_unproxied
wsgi_server.wsgi_xmlrpc = wsgi_xmlrpc
wsgi_server.application = application
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: