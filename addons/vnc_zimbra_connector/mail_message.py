# -*- coding: utf-8 -*-
import logging
from openerp import tools
from email.header import decode_header
from openerp import SUPERUSER_ID
from openerp.osv import osv, orm, fields
from openerp.tools import html_email_clean
from openerp.tools.translate import _
_logger = logging.getLogger(__name__)


class mail_message(osv.Model):
    _inherit = 'mail.message'
    _message_read_fields = ['id', 'parent_id', 'model', 'res_id', 'body',\
                            'subject', 'date', 'to_read', 'email_from',\
                            'email_to','email_cc', 'type', 'vote_user_ids',\
                            'attachment_ids', 'author_id', 'partner_ids',\
                             'record_name']
    _columns = {
        'email_to': fields.char('To',
            help="Email address of the Receiver. \
            This field is set when no matching partner is found for \
            incoming emails."),
        'email_cc': fields.char('CC',
            help="Email address of the CC. This field is set when no matching \
            partner is found for incoming emails."),
    }

    def _message_read_dict(self, cr, uid, message, parent_id=False, \
                           context=None):
        """ Return a dict representation of the message. This representation is
            used in the JS client code, to display the messages. Partners and
            attachments related stuff will be done in post-processing in batch.
            :param dict message: mail.message browse record
        """
        # private message: no model, no res_id
        is_private = False
        if not message.model or not message.res_id:
            is_private = True
        # votes and favorites: res.users ids, no prefetching should be done
        vote_nb = len(message.vote_user_ids)
        has_voted = uid in [user.id for user in message.vote_user_ids]

        try:
            body_html = html_email_clean(message.body)
        except Exception:
            body_html = '<p><b>Encoding Error : </b><br/>Unable to convert\
                        this message (id: %s).</p>' % message.id
            _logger.exception(Exception)
        return {'id': message.id,
                'type': message.type,
                'subtype': message.subtype_id.name if \
                            message.subtype_id else False,
                'body': body_html,
                'model': message.model,
                'res_id': message.res_id,
                'record_name': message.record_name,
                'subject': message.subject,
                'date': message.date,
                'to_read': message.to_read,
                'parent_id': parent_id,
                'is_private': is_private,
                'author_id': False,
                'is_author': False,
                'partner_ids': [],
                'vote_nb': vote_nb,
                'has_voted': has_voted,
                'is_favorite': message.starred,
                'attachment_ids': [],
                'email_from':message.email_from or '',
                'email_to': message.email_to or '',
                'email_cc': message.email_cc or '',
            }

mail_message()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: