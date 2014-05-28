from openerp.osv import fields,osv

class asset_assets(osv.osv):    
    _name = 'asset.assets'
    _inherit = 'asset.assets'    
    _columns = {
        'ticket_ids': fields.one2many('helpdesk.ticket', 'asset', 'Tickets'),
    }
    
asset_assets()    