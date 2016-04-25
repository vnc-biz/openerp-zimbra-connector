# -*- coding: utf-8 -*-
from openerp.osv import fields, osv



class res_company(osv.osv):
    _inherit = 'res.company'
    
    def name_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        res = []
        for comps in self.browse(cr, uid, ids, context=context):
            c_name = comps.code and '[' + comps.code + '] ' or ''
            c_name += comps.name
            res.append((comps.id,c_name))
        return res
    
    _columns = {
        'code': fields.char('Code', size=32)
    }
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: