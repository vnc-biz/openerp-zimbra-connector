# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
import base64
import email
from openerp import tools
import binascii
import dateutil.parser
import vobject
from openerp.addons.calendar import calendar
from datetime import datetime
import re
# import pooler
from email.header import decode_header
import time
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
import ast
import markdown
import smartypants
import sys
import re
import codecs


class email_server_tools(osv.osv_memory):
    _name = "email.server.tools"

    def _decode_header(self, text):
        """Returns unicode() string conversion of the the given encoded 
        smtp header"""
        if text:
            text = decode_header(text.replace('\r', ''))
            return ''.join([tools.ustr(x[0], x[1]) for x in text])

    def to_email(self,text):
        return re.findall(r'([^ ,<@]+@[^> ,]+)',text)

    def history(self, cr, uid, model, res_ids, msg, attach, context=None):
        """This function creates history for mails fetched
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param model: OpenObject Model
        @param res_ids: Ids of the record of OpenObject model created
        @param msg: Email details
        @param attach: Email attachments
        """
        if isinstance(res_ids, (int, long)):
            res_ids = [res_ids]
        msg_pool = self.pool.get('mail.message')
        for res_id in res_ids:
            case = self.pool.get(model).browse(cr, uid, res_id, context=context)
            partner_id = hasattr(case, 'partner_id') and (case.partner_id and \
                                        case.partner_id.id or False) or False
            if not partner_id and model == 'res.partner':
                partner_id = res_id
            msg_data = {
                'name': msg.get('subject', 'No subject'),
                'subject': msg.get('subject', 'No subject'),
                'date': msg.get('date'),
                'body': msg.get('body', msg.get('from')),
                'history': True,
                'partner_id': partner_id,
                'model': model,
                'email_cc': msg.get('cc'),
                'email_from': msg.get('from'),
                'email_to': msg.get('to'),
                'message_id': msg.get('message-id'),
                'references': msg.get('references') or msg.get('in-reply-to'),
                'res_id': res_id,
                'user_id': uid,
                'attachment_ids': [(6, 0, attach)]
            }
            msg_pool.create(cr, uid, msg_data, context=context)
        return True

    def history_message(self, cr, uid, model, res_id, message, context=None):
        #@param message: string of mail which is read from EML File
        import email.header
        attachment_pool = self.pool.get('ir.attachment')
        msg = self.parse_message(message)
        attachments = msg.get('attachments', [])
        att_ids = []
        for attachment in attachments:
            try:
                name= u''.join([
                    unicode(b, e or 'ascii') for b, e in \
                    email.header.decode_header(attachment)
                ])
            except email.Errors.HeaderParseError:
                pass # leave name as it was
            data_attach = {
                'name': name,
                'datas': binascii.b2a_base64(str(attachments.get(attachment))),
                'datas_fname': name,
                'description': 'Mail attachment From zimbra msg_id: %s' \
                                %(msg.get('message_id', '')),
                'res_model': model,
                'res_id': res_id,
            }
            att_ids.append(attachment_pool.create(cr, uid, data_attach))
        return self.history(cr, uid, model, res_id, msg, att_ids)

    def parse_message(self, message):
        """
            @param self: The object pointer
            @param message: Email Message for parsing
        """
        #TOCHECK: put this function in mailgateway module
        if isinstance(message, unicode):
            message = message.encode('utf-8')
        msg_txt = email.message_from_string(message)
        message_id = msg_txt.get('message-id', False)
        msg = {}
        fields = msg_txt.keys()
        msg['id'] = message_id
        msg['message-id'] = message_id
        if 'Subject' in fields:
            msg['subject'] = self._decode_header(msg_txt.get('Subject'))

        if 'Content-Type' in fields:
            msg['content-type'] = msg_txt.get('Content-Type')

        if 'From' in fields:
            msg['from'] = self._decode_header(msg_txt.get('From'))

        if 'To' in fields:
            msg['to'] = self._decode_header(msg_txt.get('To'))
        else:
            msg['to'] = self._decode_header(msg_txt.get('Delivered-To'))

        if 'Cc' in fields:
            msg['cc'] = self._decode_header(msg_txt.get('Cc'))

        if 'Reply-to' in fields:
            msg['reply'] = self._decode_header(msg_txt.get('Reply-To'))

        if 'Date' in fields:
            date = self._decode_header(msg_txt.get('Date'))
            msg['date'] = dateutil.parser.parse(date).\
                        strftime("%Y-%m-%d %H:%M:%S")

        if 'Content-Transfer-Encoding' in fields:
            msg['encoding'] = msg_txt.get('Content-Transfer-Encoding')

        if 'References' in fields:
            msg['references'] = msg_txt.get('References')

        if 'In-Reply-To' in fields:
            msg['in-reply-to'] = msg_txt.get('In-Reply-To')

        if 'X-Priority' in fields:
            msg['priority'] = msg_txt.get('X-Priority', '3 (Normal)').\
            split(' ')[0]

        if not msg_txt.is_multipart() or 'text/plain' in \
                                                msg.get('Content-Type', ''):
            encoding = msg_txt.get_content_charset()
            content = msg_txt.get_payload(decode=True)
            html_header = u"""
            <html>
            <body>
            """
            html_footer = u"""</body>
            </html>
            """
            original_txt = content
            # catch any mis-typed en dashes
            converted_txt = original_txt.replace(" - ", " -- ")
            converted_txt = smartypants.educateQuotes(converted_txt)
            converted_txt = smartypants.educateEllipses(converted_txt)
            converted_txt = smartypants.educateDashesOldSchool(converted_txt)
            # normalise line endings and insert blank line between paragraphs for Markdown
            converted_txt = re.sub("\r\n", "\n", converted_txt)
            converted_txt = re.sub("\n\n+", "\n", converted_txt)
            converted_txt = re.sub("\n", "\n\n", converted_txt)
            converted_txt = unicode( converted_txt, "utf8" )
            html = markdown.markdown(converted_txt)
            html_out = html_header + html + html_footer
            body = html_out
            msg['body'] = body

        attachments = {}
        has_plain_text = False
        if msg_txt.is_multipart() or 'multipart/alternative' in \
                                                msg.get('content-type', ''):
            body = ""
            for part in msg_txt.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                encoding = part.get_content_charset()
                filename = part.get_filename()
                if part.get_content_maintype()=='text':
                    content = part.get_payload(decode=True)
                    if filename:
                        attachments[filename] = content
                    elif not has_plain_text:
                        # main content parts should have 'text' maintype
                        # and no filename. we ignore the html part if
                        # there is already a plaintext part without filename,
                        # because presumably these are alternatives.
                        content = tools.ustr(content, encoding)
                        if part.get_content_subtype() == 'html':
                            body = content
                            has_plain_text = True
                        elif part.get_content_subtype() == 'plain':
                            html_header = u"""
                            <html>
                            <body>
                            """
                            html_footer = u"""</body>
                            </html>
                            """
                            original_txt = content
                            # catch any mis-typed en dashes
                            converted_txt = original_txt.replace(" - ", " -- ")
                            converted_txt = smartypants.\
                                            educateQuotes(converted_txt)
                            converted_txt = smartypants.\
                                            educateEllipses(converted_txt)
                            converted_txt = smartypants.\
                                        educateDashesOldSchool(converted_txt)
                            # normalise line endings and insert blank line between paragraphs for Markdown
                            converted_txt = re.sub("\r\n", "\n", converted_txt)
                            converted_txt = re.sub("\n\n+", "\n", converted_txt)
                            converted_txt = re.sub("\n", "\n\n", converted_txt)
                            html = markdown.markdown(converted_txt)
                            html_out = html_header + html + html_footer
                            body = html_out
                            msg['body'] = body
                elif part.get_content_maintype() in \
                                    ('application', 'image', 'audio', 'video'):
                    if filename:
                        attachments[filename] = part.get_payload(decode=True)
                    else:
                        res = part.get_payload(decode=True)
                        body += tools.ustr(res, encoding)
            msg['body'] = body
            msg['attachments'] = attachments
        return msg

email_server_tools()


class zimbra_partner(osv.osv_memory):
    _name = "zimbra.partner"
    _description="Zimbra Plugin Tools"

    def create_contact(self,cr,user,vals):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param vals: Value
        """
        dictcreate = dict(vals)
        # Set False value if 'undefined' for record. Id User does not spicify 
        #the values, Thunerbird set 'undefined' by default for new contact.
        for key in dictcreate:
            if dictcreate[key] == 'undefined':
                dictcreate[key] = False
        if not eval(dictcreate.get('partner_id')):
            dictcreate.update({'partner_id': False})
        create_id = self.pool.get('res.partner').create(cr, user, dictcreate)
        return create_id

    def history_message(self, cr, uid, vals):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param vals: Valuse for archiving email
                [(object_name,object_id),{binary_of_email}]
        """
        for val in vals:
            if not isinstance(val, (list,tuple)):
                continue
            if val[0] == 'message':
                val[1] = base64.decodestring(val[1])
        dictcreate = dict(vals)
        ref_ids = str(dictcreate.get('ref_ids')).split(';')
        msg = dictcreate.get('message')
        mail = msg
        msg = self.pool.get('email.server.tools').parse_message(msg)
        server_tools_pool = self.pool.get('email.server.tools')
        message_id = msg.get('message-id', False)
        msg_pool = self.pool.get('mail.message')
        msg_ids = []
        res = {}
        res_ids = []
        obj_list= ['crm.lead','project.issue','hr.applicant','res.partner',\
                   'project.project']
        for ref_id in ref_ids:
            msg_new = dictcreate.get('message')
            ref = ref_id.split(',')
            model = ref[0]
            res_id = int(ref[1])
            if message_id:
                msg_ids = msg_pool.search(cr, uid, [('message_id','=',\
                        message_id),('res_id','=',res_id),('model','=',model)])
                if msg_ids and len(msg_ids):
                    continue
            if model not in obj_list:
                res={}
                obj_attch = self.pool.get('ir.attachment')
                ls = ['*', '/', '\\', '<', '>', ':', '?',\
                       '"', '|', '\t', '\n',':','~']
                sub = msg.get('subject','NO-SUBJECT').replace(' ','')
                if sub.strip() == '':
                   sub = 'NO SBUJECT'
                fn = sub
                for c in ls:
                   fn = fn.replace(c,'')
                if len(fn) > 64:
                   l = 64 - len(fn)
                   f = fn.split('-')
                   fn = '-'.join(f[1:])
                   if len(fn) > 64:
                      l = 64 - len(fn)
                      f = fn.split('.')
                      fn = f[0][0:l] + '.' + f[-1]
                fn = fn[:-4]+'.eml'
                res['res_model'] = model
                res['name'] = msg.get('subject','NO-SUBJECT')+".eml"
                res['datas_fname'] = fn
                res['datas'] = base64.b64encode(mail.encode('utf-8'))
                res['res_id'] = res_id
                obj_attch.create(cr, uid, res)
            server_tools_pool.history_message(cr, uid, model, res_id, msg_new)
            res_ids.append(res_id)
        return len(res_ids)

    def process_email(self, cr, uid, vals):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param vals: Get Values
        """
        dictcreate = dict(vals)
        model = str(dictcreate.get('model'))
        message = dictcreate.get('message')
        return self.pool.get('email.server.tools').process_email(cr, uid, \
                                    model, message, attach=True, context=None)

    def search_message(self, cr, uid, message, context=None):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param message: ID of message to search for
            @param context: A standard dictionary for contextual values
        """
        #@return model,res_id
        references = []
        dictcreate = dict(message)
        msg = dictcreate.get('message')
        msg = self.pool.get('email.server.tools').parse_message(msg)
        message_id = msg.get('message-id')
        refs =  msg.get('references',False)
        references = False
        if refs:
            references = refs.split()
        msg_pool = self.pool.get('mail.message')
        model = ''
        res_id = 0
        if message_id:
            msg_ids = msg_pool.search(cr, uid, [('message_id','=',message_id)])
            if msg_ids and len(msg_ids):
                msg = msg_pool.browse(cr, uid, msg_ids[0])
                model = msg.model
                res_id = msg.res_id
            else:
                if references:
                    msg_ids = msg_pool.search(cr, uid,\
                                         [('message_id','in',references)])
                    if msg_ids and len(msg_ids):
                        msg = msg_pool.browse(cr, uid, msg_ids[0])
                        model = msg.model
                        res_id = msg.res_id
        return (model,res_id)

    def search_contact(self, cr, user, email):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param email: Email address to search for
        """
        address_pool = self.pool.get('res.partner')
        address_ids = address_pool.search(cr, user, [('email','=',email)])
        res = {}
        if not address_ids:
            res = {
                'email':'',
            }
        else:
            address_id = address_ids[0]
            address = address_pool.browse(cr, user, address_id)
            res = {
                'partner_name': address and address.name or '',
                'contactname': address.name,
                'street': address.street or '',
                'street2': address.street2 or '',
                'zip': address.zip or '',
                'city': address.city or '',
                'country': address.country_id and address.country_id.name or '',
                'state': address.state_id and address.state_id.name or '',
                'email': address.email or '',
                'phone': address.phone or '',
                'mobile': address.mobile or '',
                'fax': address.fax or '',
                'res_id': str(address.id),
            }
        return res.items()

    def update_contact(self, cr, user, vals):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param vals: Get Values
        """
        dictcreate = dict(vals)
        res_id = dictcreate.get('res_id',False)
        result = {}
        address_pool = self.pool.get('res.partner')
        if not (dictcreate.get('partner_id')):# TOCHECK: It should be check res_id or not
            dictcreate.update({'partner_id': False})
            create_id = address_pool.create(cr, user, dictcreate)
            return create_id

        if res_id:
            address_data = address_pool.read(cr, user, int(res_id), [])
            result = {
               'country_id': dictcreate['country_id'] and \
                            int(dictcreate['country_id'][0]) or False,
               'state_id': dictcreate['state_id'] and \
                            int(dictcreate['state_id'][0]) or False,
               'name': dictcreate['name'],
               'street': dictcreate['street'],
               'street2': dictcreate['street2'],
               'zip': dictcreate['zip'],
               'city': dictcreate['city'],
               'phone': dictcreate['phone'],
               'fax': dictcreate['fax'],
               'mobile': dictcreate['mobile'],
               'email': dictcreate['email'],
            }
        address_pool.write(cr, user, int(res_id), result )
        return True

    def create_partner(self,cr,user,vals):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param vals: Get Values
        """
        dictcreate = dict(vals)
        partner_obj = self.pool.get('res.partner')
        search_id =  partner_obj.search(cr, user,[('name','=',\
                                            dictcreate['name'])])
        if search_id:
            return 0
        create_id =  partner_obj.create(cr, user, dictcreate)
        return create_id

    def search_document(self,cr,user,vals):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param vals: Get Values
        """
        dictcreate = dict(vals)
        search_id = self.pool.get('ir.model').search(cr, user,\
                                        [('model','=',dictcreate['model'])])
        return (search_id and search_id[0]) or 0

    def search_checkbox(self,cr,user,vals):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param vals: Get Values
        """
        if vals[0]:
            value = vals[0][0]
        if vals[1]:
            obj = vals[1];
        name_get=[]
        er_val=[]
        for object in obj:
            dyn_object = self.pool.get(object)
            if object == 'res.partner':
                search_id1 = dyn_object.search(cr,user,[('name','ilike',value)])
                search_id2 = dyn_object.search(cr,user,[('email','=',value)])
                if search_id1:
                    name_get.append(object)
                    name_get.append(dyn_object.name_get(cr, user, search_id1))
                elif search_id2:
                    name_get.append(object)
                    name_get.append(dyn_object.name_get(cr, user, search_id2))
            else:
                try:
                    search_id1 = dyn_object.search(cr,user,\
                                                   [('name','ilike',value)])
                    if search_id1:
                        name_get.append(object)
                        name_get.append(dyn_object.name_get(\
                                                        cr, user, search_id1))
                except:
                    er_val.append(object)
                    continue
        if len(er_val) > 0:
            name_get.append('error')
            name_get.append(er_val)
        return name_get

    def list_alldocument(self,cr,user,vals):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param vals: Get Values
        """
        obj_list= [('crm.lead','CRM Lead'),('project.issue','Project Issue'),\
                   ('hr.applicant','HR Applicant')]
        object=[]
        model_obj=self.pool.get('ir.model')
        for obj in obj_list:
            if model_obj.search(cr, user, [('model', '=', obj[0])]):
                object.append(obj)
        return object

    def list_allcountry(self,cr,user,vals):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param vals: Get Values
        """
        country_list = []
        cr.execute("SELECT id, name from res_country order by name")
        country_list = cr.fetchall()
        return country_list

    def list_allstate(self,cr,user,vals):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param vals: Get Values
        """
        cr.execute("select id, name  from res_country_state  where "\
                    "country_id = %s order by name",(vals,) )
        state_country_list = cr.fetchall()
        return state_country_list

    def search_document_attachment(self,cr,user,vals):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param vals: Get Values
        """
        model_obj = self.pool.get('ir.model')
        object=''
        for obj in vals[0][1].split(','):
            if model_obj.search(cr, user, [('model', '=', obj)]):
                object += obj + ","
            else:
                object += "null,"
        return object

    def meeting_push(self,cr,uid,vals):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param vals: Get Values
        """
        vals_dict = dict(vals)
        context = {}
        cal_pool = self.pool.get('calendar.event')
        obj_name = vals_dict['ref_ids'].split(',')[0]
        if vals_dict['ref_ids'].split(',') and \
                    len(vals_dict['ref_ids'].split(',')) > 1:
            obj_id = vals_dict['ref_ids'].split(',')[1]
        else:
             obj_id = False
        if not obj_name and not obj_id:
            meeting_ids=cal_pool.import_cal(cr,uid,vals_dict['message'],\
                                            context=context)
        else:
            obj_dict = {'crm.lead':'default_opportunity_id',\
                        'res.partner':'default_partner_id'}
            context[obj_dict[obj_name]]=int(obj_id)
            if obj_name == 'crm.lead':
                partner_id = self.pool.get('crm.lead').browse(\
                                    cr,uid,int(obj_id)).partner_id.id or False
                context.update({'default_partner_id':partner_id})
            meeting_ids=cal_pool.import_cal(cr,uid,
                                        vals_dict['message'],context=context)
        return True

    def check_calendar_existance(self,cr,uid,vals):
        if not vals:
            return False
        else:
            pass
        self_ids = self.pool.get('calendar.event').search(cr,uid,\
                                                [('ext_meeting_id','=',vals)])
        if self_ids:
            self.meeting_push(cr, uid, vals)
        else:
            return False

zimbra_partner()


class crm_meeting(osv.osv):
    _inherit = 'calendar.event'
    _columns = {
                'ext_meeting_id':fields.char('External Meeting ID',size=256)
                }

    def uid2openobjectid(self,cr, uidval, oomodel, rdate):
        """ UID To Open Object Id
            @param cr: the current row, from the database cursor,
            @param uidval: Get USerId vale
            @oomodel: Open Object ModelName
            @param rdate: Get Recurrent Date
        """
        __rege = re.compile(r'OpenObject-([\w|\.]+)_([0-9]+)@(\w+)$')
        if not uidval:
            return (False, None)
        wematch = __rege.match(uidval.encode('utf8'))
        if not wematch:
            if oomodel:
                model_obj = pooler.get_pool(cr.dbname).get(oomodel)
                sql = "SELECT DISTINCT(id) FROM "+model_obj._table\
                        +" where ext_meeting_id ilike '"+uidval+"'"
                cr.execute(sql)
                ex_id = cr.fetchone()
                if ex_id:
                    return (ex_id[0],None)
                else:
                    return (False, None)
            else:
                return (False, None)
        else:
            model, id, dbname = wematch.groups()
            model_obj = pooler.get_pool(cr.dbname).get(model)
            if (not model == oomodel) or (not dbname == cr.dbname):
                return (False, None)
            qry = 'SELECT DISTINCT(id) FROM %s' % model_obj._table
            if rdate:
                qry += " WHERE recurrent_id=%s"
                cr.execute(qry, (rdate,))
                r_id = cr.fetchone()
                if r_id:
                    return (id, r_id[0])
                else:
                    return (False, None)
            cr.execute(qry)
            ids = map(lambda x: str(x[0]), cr.fetchall())
            if id in ids:
                return (id, None)
            return (False, None)

    def import_cal(self, cr, uid, data, data_id=None, context=None):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param data: Get Data of CRM Meetings
            @param data_id: calendar's Id
            @param context: A standard dictionary for contextual values
        """
        if context is None:
            context= {}
        event_obj = self.pool.get('basic.calendar.event')
        context.update({'model':'calendar.event'})
        vals = event_obj.import_cal(cr, uid, data, context=context)
        return self.check_import(cr, uid, vals, context=context)

    def check_import(self, cr, uid, vals, context=None):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param vals: Get Values
            @param context: A standard dictionary for contextual values
        """
        if context is None:
            context = {}
        ids = []
        model_obj = self.pool.get(context.get('model'))
        recur_pool = {}
        try:
            for val in vals:
                # Compute value of duration
                if val.get('date_deadline', False) and 'duration' not in val:
                    start = datetime.strptime(val['start_datetime'], '%Y-%m-%d %H:%M:%S')
                    end = datetime.strptime(val['date_deadline'],\
                                             '%Y-%m-%d %H:%M:%S')
                    diff = end - start
                    val['duration'] = (diff.seconds/float(86400) +\
                                        diff.days) * 24
                exists, r_id = self.uid2openobjectid(cr, val['id'],\
                                 context.get('model'), val.get('recurrent_id'))
                if val.has_key('create_date'):
                    val.pop('create_date')
                u_id = val.get('id', None)
                val.pop('id')
                if exists and r_id:
                    val.update({'recurrent_uid': exists})
                    model_obj.write(cr, uid, [r_id], val,context=context)
                    ids.append(r_id)
                elif exists:
                    model_obj.write(cr, uid, [exists], val)
                    ids.append(exists)
                else:
                    if u_id in recur_pool and val.get('recurrent_id'):
                        val.update({'recurrent_uid': recur_pool[u_id]})
                        val.update({'ext_meeting_id':u_id})
                        revent_id = model_obj.create(cr, uid, val,\
                                                     context=context)
                        ids.append(revent_id)
                    else:
                        __rege = re.compile\
                                (r'OpenObject-([\w|\.]+)_([0-9]+)@(\w+)$')
                        wematch = __rege.match(u_id.encode('utf8'))
                        if wematch:
                            model, recur_id, dbname = wematch.groups()
                            val.update({'recurrent_uid': recur_id})
                        val.update({'ext_meeting_id':u_id})
                        event_id = model_obj.create(cr, uid, val,\
                                                    context=context)
                        recur_pool[u_id] = event_id
                        ids.append(event_id)
        except Exception:
            raise
        return ids

    def check_calendar_existance(self,cr,uid,ids,data):
        if data:
            self_ids=self.search(cr,uid,[('ext_meeting_id','=',data)])
        return True

crm_meeting()


class res_partner(osv.osv):
    _inherit='res.partner'
    _columns={
              'name': fields.char('Name', size=128),
              'first_name':fields.char('First Name',size=128),
              'middle_name':fields.char('Middle Name',size=128),
              'last_name':fields.char('Last Name',size=128),
              'zcontact_id': fields.char('Zimbra Contact ID', size=128),
              }

    def partner_sync_multi(self, cr, uid, zlistofdict=[], context={}):
        created = updated = 0
        if zlistofdict:
            for element in zlistofdict:
                revised_element = {}
                found_ids = self.search(cr, uid, [('zcontact_id','=',\
                            element.has_key('id') and element['id'] or False)])

                if element.has_key('country_id') or element.has_key('state_id'):
                    cr.execute("SELECT id from res_country_state where \
                                LOWER(name)=LOWER('%s')"%(element['state_id']))
                    state_ids = map(lambda x: x, cr.fetchall())
                    if state_ids and state_ids[0]:
                        element.update({'state_id': state_ids[0][0]})
                    else:
                        element.update({'state_id': False})

                    cr.execute("SELECT id from res_country where \
                            LOWER(name)=LOWER('%s')"%(element['country_id']))
                    country_ids = map(lambda x: x, cr.fetchall())
                    if country_ids and country_ids[0]:
                        element.update({'country_id': country_ids[0][0]})
                    else:
                        element.update({'country_id': False})

                element.update({'zcontact_id': element.has_key('id') \
                                 and element['id'] or False})
                for key,val in element.iteritems():
                    if val == 'False':
                        val = False
                    revised_element.update({key:val})
                revised_element.pop('id',None)
                if not found_ids:
                    partner_id = self.create(cr, uid, revised_element, \
                                             context=context)
                    created += 1
                else:
                    self.write(cr, uid, found_ids, revised_element, \
                               context=context)
                    updated += 1
        return {'created': created,'updated': updated}

    def partner_sync_openerp(self,cr, uid, zuid=False, addbookid=False, \
                             context=None):
        datas = False
        deleted_datas = {'deleted_datas':[]}
        zimbra_contactsync_pool = self.pool.get('zimbra.contactsync.log')
        if not zuid and not addbookid:
            return {'error':'UserID/AddressBook ID missing !'}
        zsync_ids = zimbra_contactsync_pool.search(cr, uid, \
                        [('zimbra_uid','=',zuid),('addbook_id','=',addbookid)])
        if zsync_ids:
            data_read = zimbra_contactsync_pool.read(cr, uid, zsync_ids[0])
            partner_ids = self.search(cr, uid, [('write_date','>',\
                            str(datetime.strptime(data_read['last_sync'],\
                            '%Y-%m-%d %H:%M:%S'))),('zcontact_id','=',False)])
            if data_read['delete_items']:
                deleted_datas['deleted_datas'] = \
                                    ast.literal_eval(data_read['delete_items'])
            zimbra_contactsync_pool.write(cr, uid, zsync_ids, 
                                {
                                'last_sync':time.strftime('%Y-%m-%d %H:%M:%S'),
                                'delete_items':'',
                                })
            datas = self.export_data(cr,uid,partner_ids,\
                                     ['id','first_name','middle_name',\
                                      'last_name','city','street','street2',\
                                      'zip','phone','fax','email','mobile',\
                                      'parent_id','title','country_id','state_id'])
        else:
            partner_id = self.search(cr, uid, [('zcontact_id','=',False)])
            datas = self.export_data(cr,uid,partner_id,['id','first_name',\
                                            'middle_name','last_name','city',\
                                            'street','street2','zip','phone',\
                                            'fax','email','mobile','parent_id',\
                                            'title','country_id','state_id'])
            zimbra_contactsync_pool.create(cr, uid, {
                                'zimbra_uid':zuid,
                                'addbook_id':addbookid,
                                'last_sync':time.strftime('%Y-%m-%d %H:%M:%S')
                                })
        return datas, deleted_datas

    def unlink(self, cr, uid, ids, context=None):
        datas = []
        data_write = []
        read_data = [x['id'] for x in self.read(cr, uid, ids, \
                                    ['zcontact_id']) if not x['zcontact_id']]
        if not read_data:
            return super(res_partner, self).unlink(cr, uid, ids, \
                                                   context=context)
        all_ids = self.pool.get('zimbra.contactsync.log').search(cr, uid, [])
        for zcs in self.pool.get('zimbra.contactsync.log').browse(cr, uid,\
                                                                   all_ids):
            if zcs.delete_items:
                data_write = ast.literal_eval(zcs.delete_items)
                datas = self.export_data(cr,uid,read_data,['id'])
                for d in datas['datas']:
                    data_write.append(d[0])
            else:
                datas = self.export_data(cr,uid,read_data,['id'])
                for d in datas['datas']:
                    data_write.append(d[0])
            self.pool.get('zimbra.contactsync.log').write(cr, uid, zcs.id,\
                                                 {'delete_items':data_write})
        return super(res_partner, self).unlink(cr, uid, ids, context=context)

    def name_create(self, cr, uid, name, context=None):
        """ Override of orm's name_create method for partners. The purpose is
            to handle some basic formats to create partners using the
            name_create.
            It will duplicate name to first_name """
        rec_id = self.create(cr, uid, {self._rec_name: name, 'first_name': name}, context=context)
        return self.name_get(cr, uid, [rec_id], context)[0]

    def create(self, cr, uid, vals, context=None):
        if vals.get('is_company') != True:
            if vals.get('first_name') or vals.get('middle_name') or \
                                        vals.get('last_name'):
                vals['name'] = (vals.get('first_name') or "") + ' '+  \
                                (vals.get('middle_name') or "") + ' '+\
                                ( vals.get('last_name') or "")
        else:
            vals['first_name'] = vals['name']
        return super(res_partner, self).create(cr, uid, vals, context=context)

    def onchange_fml_name(self, cr, uid, ids, fname, mname=' ', lname=' ' ):
        res={}
        if fname:
            res['name']=fname+' '+(mname or '')+' '+(lname or '')
        return {'value':res}

    def write(self, cr, uid, ids, vals, context=None):
        f_name = ''
        m_name = ''
        l_name = ''
        if not type(ids) is list:
            ids = [ids]
        for data in self.browse(cr, uid, ids):
            if not vals.get('is_company') or not data['is_company']:
                if vals.get('first_name') or vals.get('middle_name') or \
                    vals.get('last_name'):
                    f_name=vals.get('first_name') or  data['first_name'] or ''
                    m_name=vals.get('middle_name') or data['middle_name'] or ''
                    l_name=vals.get('last_name') or data['last_name'] or ''
                    vals['name'] = (f_name or "") + ' '+  (m_name or "")+ ' '+\
                                    (l_name or "")
            else:
                if not vals.get('name'):
                    for data in self.browse(cr, uid, ids):
                        vals['first_name'] = data['name']
                else:
                    vals['first_name'] = vals['name']
        return super(res_partner, self).write(cr, uid, ids, vals,\
                                               context=context)

    def res_partner_name_cron(self, cr, uid, context={}):
        ids = self.search(cr, uid, [], context=context)
        for data in self.browse(cr, uid, ids, context=context):
            if not data.is_company:
                name_data = data.name.split(' ')
                self.write(cr, uid, data['id'], {'first_name': name_data[0], 'last_name': name_data[-1]},\
                            context)
            else:
                self.write(cr, uid, data['id'], {'first_name': data.name}, context)
        return True

res_partner()

class zimbra_contactsync_log(osv.osv):
    _name = 'zimbra.contactsync.log'
    _rec_name = 'zimbra_uid'
    _columns = {
                'zimbra_uid':fields.char('Zimbra UserID',size=256),
                'addbook_id':fields.char('AddresBook ID',size=256),
                'last_sync':fields.datetime('Last Sync Time'),
                'delete_items':fields.text('Delete Sync Pending Partners')
                }
    _defaults = {'delete_items':'[]'}

zimbra_contactsync_log()

class crm_phonecall(osv.osv):
    _inherit='crm.phonecall'
    _columns={
              'priority': fields.selection([('1', 'Highest'),('2', 'High'),('3', 'Normal'),('4', 'Low'),('5', 'Lowest')], 'Priority'),
              }
    
class calendar_event(osv.Model):
    _inherit='calendar.event'
    reminder_mapping = {'1':{'duration': 1, 'interval': 'minutes', 'type':'notification'},
                    '2': {'duration': 5, 'interval': 'minutes', 'type': 'notification'},
                    '3': {'duration': 10, 'interval': 'minutes', 'type': 'notification'},
                    '4': {'duration': 15, 'interval': 'minutes', 'type': 'notification'},
                    '5': {'duration': 30, 'interval': 'minutes', 'type': 'notification'},
                    '6': {'duration': 45, 'interval': 'minutes', 'type': 'notification'},
                    '7': {'duration': 1, 'interval': 'hours', 'type': 'notification'},
                    '8': {'duration': 2, 'interval': 'hours', 'type': 'notification'},
                    '9': {'duration': 3, 'interval': 'hours', 'type': 'notification'},
                    '10': {'duration': 4, 'interval': 'hours', 'type': 'notification'},
                    '11': {'duration': 5, 'interval': 'hours', 'type': 'notification'},
                    '12': {'duration': 18, 'interval': 'hours', 'type': 'notification'}
                    }

    def create(self, cr, uid, vals, context=None):
        alarm_id = vals.get('alarm_id', '')
        if alarm_id:
            alarm_data = self.reminder_mapping[alarm_id]
            alarm_pool = self.pool.get('calendar.alarm')
            alarm_ids = alarm_pool.search(cr, uid, [('duration', '=', alarm_data['duration']),
                                              ('interval', '=', alarm_data['interval']),
                                              ('type', '=', alarm_data['type'])])
            if not alarm_ids:
                alarm_data['name'] = str(alarm_data['duration']) + ' ' + alarm_data['interval'] + ' before'
                alarm_ids = alarm_pool.create(cr, uid, alarm_data, context=context)
            else:
                alarm_ids = alarm_ids[0]
            
            vals['alarm_ids'] = [(4, alarm_ids)]
                
        return super(calendar_event, self).create(cr, uid, vals, context=context)
    
    def write(self, cr, uid, ids, vals, context=None):
        #FIX: needed because _constraint function(_check_closing_date) uses DB values and not current values
        stop_date = vals.get('stop_datetime', '') or vals.get('stop_date', '')
        if stop_date:
            start_date = vals.get('start_datetime', '')
            if not start_date:
                event = self.browse(cr, uid, ids[0], context=context)
                start_date = event.start_datetime or event.start_date

            if start_date:
                if stop_date < start_date:
                    raise osv.except_osv('Invalid Data!','Error ! End date cannot be set before start date.')

        return super(calendar_event, self).write(cr, uid, ids, vals, context=context)

    
calendar_event()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
