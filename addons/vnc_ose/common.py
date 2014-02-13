# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from functools import partial


class region_class(osv.osv):
    """ New class named region_class made for Region Management """

    _name = 'region.region'
    _rec_name ='name'
    _columns = {
        'name':fields.char('Name', size=256),
        'crm_id':fields.char('CRM ID', size=256),
        'type':fields.selection([('territory','Territory'),('area','Area'),\
                                 ('zone','Zone')],'Type'),
        'user_ids':fields.many2many('res.users','region_user_rel',\
                                    'region_id','user_id','Users'),
        'area_ids':fields.many2many('region.region','region_area_rel',\
                                    'region_id','area_id','Areas',\
                                    domain=[('type','=','area')]),
        'zone_ids':fields.many2many('region.region','region_zone_rel',\
                                    'region_id','zone_id','Zone',\
                                    domain=[('type','=','zone')]),
        'area_zone_ids':fields.many2many('region.region','region_area_zone_rel',\
                                    'region_id','area_zone_id','Zone',\
                                    domain=[('type','=','zone')]),
    }

    def name_search(self, cr, user, name, args=None, operator='ilike', \
                                            context=None, limit=100):
        """ 
        Name search method overridden for searching throught crm_id and name 
        """

        if not args:
            args=[]
        if not context:
            context={}
        ids = []
        if not name:
            ids = self.search(cr, user, args, limit=limit, context=context)
        if not ids:
            ids = self.search(cr, user, [('crm_id', operator, name)])
        if not ids:
            ids = self.search(cr, user, [('name', operator, name)])
        return self.name_get(cr, user, ids, context=context)

    def write(self, cr, user, ids, vals, context={}):
        self.pool.get('ir.model.access').call_cache_clearing_methods(cr)
        clear = partial(self.pool.get('ir.rule').clear_cache, cr)
        map(clear, [user])
        db = cr.dbname
        user_pool = self.pool.get('res.users')
        uids = user_pool.search(cr, user, [])
        user_pool.write(cr, user, uids, {})
        return super(region_class, self).write(cr, user, ids, vals, \
                                               context=context)

region_class()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: