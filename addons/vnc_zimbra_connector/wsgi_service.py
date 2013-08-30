# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011-2012 OpenERP s.a. (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

"""

WSGI stack, common code.

"""
import logging
import threading
import werkzeug.serving
import werkzeug.contrib.fixers
import xmlrpclib
from icalendar import Calendar, Event, Todo
import datetime as DT
import hashlib


_logger = logging.getLogger(__name__)

def application(environ, start_response):
    if not environ.get('HTTP_AUTHORIZATION'):
        start_response("401 Authorization required", [
                        ('WWW-Authenticate', 'Basic realm="OpenERP"'),
                        ('cache-control', 'no-cache'),
                        ('Pragma', 'no-cache'),
                        ('Expires', 0),
                        ('Content-Type', 'text/html'),
                        ('Content-Length', 4), # len(self.auth_required_msg)
                        ])
        return environ
    
    auth = environ.get('HTTP_AUTHORIZATION')
    if auth:
        scheme, data = auth.split(None, 1)
        assert scheme.lower() == 'basic'
        username, password = data.decode('base64').split(':', 1)
        query_str = environ.get('QUERY_STRING')
        para = query_str.split('&')
        para_final = [x.split('=') for x in para]
        cal_data = ''
        
        try:
            if environ.get('PATH_INFO') == '/task':  
                cal_data = make_service_call(para_final[0][1],para_final[1][1],username,password,para_final[2][1],'task')
            elif environ.get('PATH_INFO') == '/calendar':
                cal_data = make_service_call(para_final[0][1],para_final[1][1],username,password,para_final[2][1],'calendar')
            else:
                body = 'Invalid URL'
                headers = [
                ('content-type', 'text/plain'),
                ('content-length', str(len(body))),
                ('WWW-Authenticate', 'Basic realm="OpenERP"')]
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
     
    start_response( "200 OK", [ ('cache-control', 'no-cache'),('Pragma', 'no-cache'),('Expires', 0),('Content-Type', 'text/calendar'), ('Content-length', len(cal_data)), ('Content-Disposition', 'attachment; filename='+'task_calender'+'.ics') ] ) 
    return cal_data   

# The WSGI server, started by start_server(), stopped by stop_server().
httpd = None

def serve():
    """ Serve HTTP requests via werkzeug development server.

    If werkzeug can not be imported, we fall back to wsgiref's simple_server.

    Calling this function is blocking, you might want to call it in its own
    thread.
    """
    global httpd

    # TODO Change the xmlrpc_* options to http_*
    interface = '0.0.0.0'
    port = '9090'
    httpd = werkzeug.serving.make_server(interface, port, application, threaded=True)
    _logger.info('HTTP service (werkzeug) running on %s:%s', interface, port)
    httpd.serve_forever()

def start_service():
    """ Call serve() in its own thread.
    The WSGI server can be shutdown with stop_server() below.
    """
    threading.Thread(target=serve).start()

def stop_service():
    """ Initiate the shutdown of the WSGI server.
    The server is supposed to have been started by start_server() above.
    """
    if httpd:
        httpd.shutdown()

def make_service_call(host, port, username, pwd, dbname,option):
    
    def uid_generat(data):  #UID generat
        sha_obj = hashlib.sha1(data)
        return sha_obj.hexdigest()
    
    sock_common = xmlrpclib.ServerProxy ('http://'+host+':'+port+'/xmlrpc/common')
    uid = sock_common.login(dbname, username, pwd)
    sock = xmlrpclib.ServerProxy('http://'+host+':'+port+'/xmlrpc/object')
    if option == "task":
    
        task_ids = sock.execute(dbname, uid, pwd, 'crm.task', 'search', [('task_type','=','t'),('user_id','=',uid)])
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
        event_data = sock.execute(dbname, uid, pwd, 'res.users', 'get_ics_file', event_ids)
        return event_data
start_service()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
