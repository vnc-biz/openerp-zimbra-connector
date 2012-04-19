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
