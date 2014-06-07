from openerp.osv import fields, osv
from datetime import datetime
import string
import random

class helpdesk_category(osv.osv):
    _name = "helpdesk.category"
    _description = "Helpdesk Category"
    _columns = {
        'name': fields.char('Name', size=100, required=True),            
    }    
helpdesk_category()

class helpdesk_priority(osv.osv):
    _name = "helpdesk.priority"
    _description = "Helpdesk Priority"
    _columns = {
        'name': fields.char('Name', size=100, required=True),            
    }    
    
helpdesk_priority()

class helpdesk_conversation(osv.osv):
    _name = "helpdesk.conversation"
    _description = "Helpdesk Conversation"
    _columns = {
        'ticket_id': fields.many2one('helpdesk.ticket', 'Ticket'),
        'from_name': fields.char('From', size=100, required=True),            
        'from_email': fields.char('Email', size=100, required=True),            
        'message_date': fields.datetime('Date'),
        'message': fields.text('message'),
    }
    
helpdesk_conversation()
    
class helpdesk_ticket(osv.osv):
    _name = "helpdesk.ticket"
    _description = "Helpdesk Ticket"        
        
    def case_close(self, cr, uid, ids, context=None):        
        self.write(cr,uid,ids,{'end_date': datetime.now(),'state':'done'})        
        return True
        
    def case_reset(self, cr, uid, ids, context=None):
        self.write(cr,uid,ids,{'state':'draft'})        
        return True
    
    def _id_generator(self,cr,uid,context=None):
        size = 10
        chars= string.ascii_uppercase + string.digits
        return ''.join(random.choice(chars) for _ in range(size))
    
    _columns = {
        'trackid': fields.char('Track ID', size=20, readonly=True),        
        'name': fields.char('Subject', size=100, required=True),            
        'sender': fields.char('Sender Name', size=100, required=True),            
        'email': fields.char('Sender Email', size=100, required=True),            
        'category': fields.many2one('helpdesk.category','Category'),
        'priority': fields.selection([('1', 'Highest'),('2', 'High'),('3', 'Normal'),('4', 'Low'),('5', 'Lowest'),],'Priority'),
        'technician': fields.many2one('res.users', 'Responsible'),        
        'asset': fields.many2one('asset.assets','Asset'),
        'description': fields.text('Description'),
        'conversation_ids': fields.one2many('helpdesk.conversation', 'ticket_id', 'Conversation'),
        'start_date': fields.datetime('Start Date', readonly=True),
        'end_date': fields.datetime('End Date', states={'done': [('readonly', True)]}),
        'resolution': fields.text('Resolution'),
        'duration': fields.float('Duration', states={'done': [('readonly', True)]}),
        'active': fields.boolean('Active', required=False),
        'state': fields.selection([('draft', 'New'),('cancel', 'Cancelled'),('open', 'In Progress'),('pending', 'Pending'),('done', 'Closed')], 'Status', size=16, readonly=True),        
    }    
    _defaults = {        
        'active': lambda *a: 1,                        
        'state': lambda *a: 'draft',
        'start_date': lambda *a: fields.datetime.now(),
        'priority': lambda *a: '3',
    }
    
    def create(self, cr, uid, values, context=None):		                        
        trackid = self._id_generator(cr, uid, context)
        values.update({'trackid':trackid})        
	return super(helpdesk_ticket, self).create(cr, uid, values, context = context)
    
helpdesk_ticket()