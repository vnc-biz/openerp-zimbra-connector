from osv import fields, osv
import pytz

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
