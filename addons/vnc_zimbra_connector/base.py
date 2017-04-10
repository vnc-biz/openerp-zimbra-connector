# -*- coding: utf-8 -*-
from openerp.models import BaseModel

from openerp import api

@api.model
def name_search_with_create_date(self, name, args=None, operator='ilike', limit=100):
    ret_val = self.name_search(name, args=args, operator=operator, limit=limit)
    new_ret_val = []
    for val in ret_val:
        rec = self.browse(val[0])
        new_ret_val.append((val[0], val[1], rec.create_date or ''))
    return new_ret_val


BaseModel.name_search_with_create_date = name_search_with_create_date