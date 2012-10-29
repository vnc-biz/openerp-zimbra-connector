from osv import fields, osv
import pytz

class partner_responsibility(osv.osv):
    _name='partner.responsibility'
    _columns={
              'name':fields.char('Name',size=256),
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
        @param uid: the current user’s ID for security checks,
        @param context: A standard dictionary for contextual values
        """
        return [(x, x) for x in pytz.all_timezones]

    _columns = {
        'vtimezone': fields.selection(_tz_get, size=64, string='Timezone'),
    }

    _defaults = {
        'vtimezone': lambda s, cr, uid, c: s.pool.get('res.users').browse(cr, uid, uid, context=c).context_tz,
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
                'partner_address_id':fields.many2one('res.partner.address', 'Contact Adress'),
                'phone': fields.char('Phone', size=32),
                'fax': fields.char('Fax', size=32),
                'email': fields.char('E-mail', size=32),
                'mobile': fields.char('Mobile', size=32),
                'responsibility': fields.many2one('partner.responsibility','Responsibility'),
                }

    def onchange_partner_address(self,cr,uid,ids,partner_address_id,context=None):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: list of object ids,
        @param partner_address_id: specific partner id,
        @param context: A standard dictionary for contextual values
        """
        res={}
        if partner_address_id:
            address_pool = self.pool.get('res.partner.address')
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
        @param uid: the current user’s ID for security checks,
        @param domain: Condition to filter on
        @param fields: list of fields to read
        @param context: A standard dictionary for contextual values
        """
        ids = self.search(cr, uid, domain, context=context)
        read_data = lead_data = []
        lead_pool = self.pool.get('crm.lead')
        if ids:
            read_data = self.read(cr, uid, ids, fields=fields, context=context)
            lead_ids = [data['lead_id'] for data in read_data]
            if lead_ids:
                lead_data = lead_pool.read(cr,uid,lead_ids)
        return lead_data

lead_address_line()

def search_read(self, cr, uid, domain, fields=[], context={}):
    """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
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
