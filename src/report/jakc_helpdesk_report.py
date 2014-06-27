from openerp.osv import fields,osv
from openerp import tools
import logging

_logger = logging.getLogger(__name__)

AVAILABLE_STATES = [
    ('draft','New'),    
    ('open','Open'),    
    ('cancel', 'Cancelled'),
    ('done', 'Closed'),
    ('pending','Pending')
]

class helpdesk_report(osv.osv):

    _name = "helpdesk.report"
    _description = "Helpdesk Report"
    _auto = False

    _columns = {
        'name': fields.char('Year', size=64, required=False, readonly=True),
        'month': fields.selection([('01', 'January'), ('02', 'February'), \
                                  ('03', 'March'), ('04', 'April'),\
                                  ('05', 'May'), ('06', 'June'), \
                                  ('07', 'July'), ('08', 'August'),\
                                  ('09', 'September'), ('10', 'October'),\
                                  ('11', 'November'), ('12', 'December')], 'Month', readonly=True),
        'state': fields.selection(AVAILABLE_STATES, 'Status', size=16, readonly=True),                          
        'nbr': fields.integer('# of Cases', readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'start_date': fields.date('Start Date' , readonly=True, select=True),
        'end_date': fields.date('End Date' , readonly=True, select=True),
        'response_date': fields.date('Response Date' , readonly=True, select=True),
        'category':fields.many2one('helpdesk.category', 'Category', readonly=True),
        'technician':fields.many2one('res.users', 'Section', readonly=True),        
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'helpdesk_report')
        cr.execute("""
            create or replace view helpdesk_report as (
                select
                    min(c.id) as id,                                        
                    to_char(c.start_date, 'YYYY') as name,
                    to_char(c.start_date, 'MM') as month,
                    to_char(c.start_date, 'YYYY-MM-DD') as day,                
                    to_char(c.start_date, 'YYYY-MM-DD') as start_date,
                    to_char(c.response_date, 'YYYY-MM-DD') as response_date,
                    to_char(c.end_date, 'YYYY-MM-DD') as end_date,										
                    c.category as category,
                    c.technician as technician,
                    c.state as state,
                    count(*) as nbr
                from
                    helpdesk_ticket c           
                group by to_char(c.start_date, 'YYYY'), to_char(c.start_date, 'MM'),to_char(c.start_date, 'YYYY-MM-DD'),\
                    c.response_date,c.end_date,c.category, c.technician,c.state,c.id                    
            )""")

helpdesk_report()
