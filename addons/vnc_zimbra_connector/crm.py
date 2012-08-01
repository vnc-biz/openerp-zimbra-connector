from osv import fields, osv
import pytz

class crm_meeting(osv.osv):
    """ CRM Meeting Cases """
    _order = 'date asc'

    _inherit = 'crm.meeting'

    def _tz_get(self, cr, uid, context=None):
        return [(x, x) for x in pytz.all_timezones]

    _columns = {
        'vtimezone': fields.selection(_tz_get, size=64, string='Timezone'),
    }

    _defaults = {
        'vtimezone': lambda s, cr, uid, c: s.pool.get('res.users').browse(cr, uid, uid, context=c).context_tz,
    }

crm_meeting()

def search_read(self, cr, uid, domain, fields=[], context={}):
    ids = self.search(cr, uid, domain, context=context)
    read_data = []
    if ids:
        read_data = self.read(cr, uid, ids, fields=fields, context=context)
    return read_data

osv.osv.search_read = search_read
