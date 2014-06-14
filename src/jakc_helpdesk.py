from openerp.addons.base_status.base_state import base_state
from openerp.addons.base_status.base_stage import base_stage
from openerp.osv import fields, osv
from datetime import datetime
from openerp.tools import html2plaintext
import string
import random
import time
import logging

_logger = logging.getLogger(__name__)

AVAILABLE_STATES = [
    ('draft','New'),    
    ('open','Open'),    
    ('cancel', 'Cancelled'),
    ('done', 'Closed'),
    ('pending','Pending')
]

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
    _inherit = ['mail.thread','ir.needaction_mixin']    
    
    def save_conversation_action(self, cr, uid, ids, context=None):                
        for message in self.browse(cr, uid, ids, context=context):
            values = {}
            values['ticket_id'] = context.get('ticket_id',False)
            values['message_date'] = message.message_date
            values['message'] = message.message
            values['inbound'] = message.inbound
            _logger.info('Conversation values : ' + values)                        
            self.create(cr,uid,values,context=context)
        return {'type': 'ir.actions.act_window_close'}
        
    _columns = {
        'ticket_id': fields.many2one('helpdesk.ticket', 'Ticket', readonly=True),       
        'helpdesk_conversation_recipients': fields.many2many('hr.employee', 
            'helpdesk_conversation_recipients_rel',
            'helpdesk_conversation_id',
            'hr_employee_id',
            'Recipients'),
        'message_date': fields.datetime('Date'),
        'name': fields.char('Name', size=100, required=True),
        'description': fields.text('Description'),
        'attachment_ids': fields.many2many('ir.attachment',
            'helpdesk_conversation_ir_attachments_rel',
            'helpdesk_conversation_id', 'ir_attachment_id', 'Attachments'),        
        'inbound': fields.boolean('Inbound'),             
    }
    _order = "message_date desc"
            
    _defaults = {        
        'message_date': lambda *a: fields.datetime.now(),
    }            
    
    def _process_incoming_conversation(self,cr, uid,context=None):        
        _logger.info('Process Incoming Conversation Started')
        return True
        
    def _get_employee(self, cr, uid, emp_email, context=None):
        obj = self.pool.get('hr.employee')
        ids =  obj.search(cr, uid, [('work_email','=',emp_email)], context=context)
        if len(ids) > 0:
            employees = obj.browse(cr, uid, ids, context=context)
            return employees[0]
        else:
            return False
        
    
    # -------------------------------------------------------
    # Mail gateway
    # -------------------------------------------------------

    def message_new(self, cr, uid, msg, custom_values=None, context=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        if custom_values is None: custom_values = {}
        desc = html2plaintext(msg.get('body')) if msg.get('body') else ''
        defaults = {
            'message_date': msg.get('date'),
            'name': msg.get('subject') or _("No Subject"),
            'description': 'Ticket Created',        
            'inbound': True,
        }
        defaults.update(custom_values)
        message_id = super(helpdesk_conversation,self).message_new(cr, uid, msg, custom_values=defaults, context=context)    
        
        email_from = msg.get('email_from')[msg.get('email_from').find("<")+1:msg.get('email_from').find(">")]
        employee = self._get_employee(cr, uid, email_from, context=context)
                    
        ticket_id = None
        subject = msg.get('subject')
        ticket_id_prefix = subject.find('<')
        ticket_id_suffix = subject.find('>')
        
        if  ticket_id_prefix > -1 or  ticket_id_suffix > -1:
            ticket_id = subject[ticket_id_prefix+1:ticket_id_suffix]
 
        helpdesk_ticket_obj = self.pool.get('helpdesk.ticket')
        
        if ticket_id == None:            
            #Create Ticket
            ticket = {}
            if employee == False:
                ticket['employee'] = 1
            ticket['employee'] = employee['id']
            ticket['name'] = msg.get('subject') or _("No Subject")
            ticket['description'] = desc            
            ticket_id = helpdesk_ticket_obj.create(cr, uid, ticket, context=context)
            ticket_datas = self.pool.get('helpdesk.ticket').browse(cr, uid, [ticket_id], context=context)        
            ticket_data = ticket_datas[0]
            _logger.info('Sending Ticket Created Notification')
            mail_mail = self.pool.get('mail.mail')
            mail_ids = []
            mail_ids.append(mail_mail.create(cr, uid, {
                'email_from': 'helpdesk@jakc.com',
                'email_to': msg.get('email_from'),
                'subject': "<" + ticket_data['trackid'] + ">" + ticket_data['name'],
                'body_html': 'Ticket was created by Helpdesk System'
                }, context=context))
            mail_mail.send(cr, uid, mail_ids, context=context)
            _logger.info('Sending Ticket Created Notification Successfully')                    
                                
        helpdesk_conversation_obj = self.pool.get('helpdesk.conversation')        
        conversation = helpdesk_conversation_obj.write(cr, uid, [message_id],{'ticket_id':ticket_id},context=context)        
        
        #helpdesk_conversation_recipient_obj = self.pool.get('helpdesk_conversation_recipients_rel')
        #recipients = {}
        #recipients['helpdesk_conversation_id'] = message_id
        #recipients['hr_employee_id'] = 1
        #helpdesk_conversation_recipient_obj.create(cr, uid, recipients, context=context)        
        
        return message_id
            
helpdesk_conversation()
    
class helpdesk_conversation_employee(osv.osv):
    _name = "helpdesk.conversation.employee"
    _description = "Helpdesk Conversation Employee"
    _columns = {
        'conversation_id': fields.many2one('helpdesk.conversation', 'Conversation', readonly=True),       
        'employee_id': fields.many2one('hr.employee', 'Employee', readonly=True),               
    }
    
helpdesk_conversation_employee()

            
class helpdesk_ticket(base_state, base_stage, osv.osv):
    _name = "helpdesk.ticket"
    _description = "Helpdesk Ticket"            
    
    #Call Add Conversation Form
    def add_conversation_action(self, cr, uid, ids, context=None):               
        print ids
        print context
        return {
               'type': 'ir.actions.act_window',
               'name': 'Add Conversation',
               'view_mode': 'form',
               'view_type': 'form',               
               'res_model': 'helpdesk.conversation',
               'nodestroy': True,
               'target':'new',
               'context': {'ticket_id': ids[0]},
    }         
    
    #Fetch Helpdesk Ticket by ID
    def _get_values(self, cr, uid, ids, context=None):
        obj = self.pool.get('helpdesk.ticket')
        return obj.browse(cr, uid, ids, context=context)
                       
    def case_response(self, cr, uid, ids, context=None):
        self.write(cr,uid,ids,{'response_date':datetime.now(),'state':'open'})        
        ticket_datas  = self._get_values(cr, uid, ids, context=context)        
        ticket_data = ticket_datas[0]
        conversation_obj = self.pool.get('helpdesk.conversation')           
        values = {}
        values['ticket_id'] = ids[0]
        values['message_date'] = datetime.now()
        values['description'] = "Ticket was responsed"
        conversation_obj.create(cr, uid, values, context=context)
        _logger.info('Sending Ticket Response Notification')
        mail_mail = self.pool.get('mail.mail')
        mail_ids = []
        mail_ids.append(mail_mail.create(cr, uid, {
            'email_from': 'helpdesk@jakc.com',
            'email_to': 'whidayat@jakc.com',
            'subject': "<" + ticket_data['trackid'] + ">" + ticket_data['name'],
            'body_html': 'Ticket was recorded and it staff will follow up'
            }, context=context))
        mail_mail.send(cr, uid, mail_ids, context=context)
        _logger.info('Sending Ticket Response Notification Successfully')        
        return True
    
    def case_pending(self, cr, uid, ids, context=None):        
        self.write(cr,uid,ids,{'state':'pending'})  
        conversation_obj = self.pool.get('helpdesk.conversation')           
        values = {}
        values['ticket_id'] = ids[0]
        values['message_date'] = datetime.now()
        values['description'] = "Ticket Pending"
        conversation_obj.create(cr, uid, values, context=context)        
        return True
    
    def case_cancel_pending(self, cr, uid, ids, context=None):        
        self.write(cr,uid,ids,{'state':'open'})  
        conversation_obj = self.pool.get('helpdesk.conversation')           
        values = {}
        values['ticket_id'] = ids[0]
        values['message_date'] = datetime.now()
        values['description'] = "Ticket Cancel Pending"
        conversation_obj.create(cr, uid, values, context=context)        
        return True
    
    def case_close(self, cr, uid, ids, context=None):        
        self.write(cr,uid,ids,{'end_date': datetime.now(),'state':'done'})  
        conversation_obj = self.pool.get('helpdesk.conversation')
        values = {}
        values['ticket_id'] = ids[0]
        values['message_date'] = datetime.now()
        values['description'] = "Ticket Closed"
        conversation_obj.create(cr, uid, values, context=context)
        _logger.info('Sending Ticket Closed Notification')
        mail_mail = self.pool.get('mail.mail')
        mail_ids = []
        mail_ids.append(mail_mail.create(cr, uid, {
            'email_from': 'helpdesk@jakc.com',
            'email_to': 'whidayat@jakc.com',
            'subject': 'Ticket Closed',
            'body_html': 'Ticket Closed'
            }, context=context))
        mail_mail.send(cr, uid, mail_ids, context=context)
        _logger.info('Sending Ticket Closed Notification Successfully')
        return True
        
    def case_reset(self, cr, uid, ids, context=None):
        self.write(cr,uid,ids,{'state':'open'})        
        conversation_obj = self.pool.get('helpdesk.conversation')        
        values = {}
        values['ticket_id'] = ids[0]
        values['message_date'] = datetime.now()
        values['description'] = "Ticket was re-opened"
        conversation_obj.create(cr, uid, values, context=context)        
        return True
    
    def _id_generator(self,cr,uid,context=None):
        size = 10
        chars= string.ascii_uppercase + string.digits
        return ''.join(random.choice(chars) for _ in range(size))
    
    _columns = {
        'trackid': fields.char('Track ID', size=20, readonly=True),        
        'name': fields.char('Subject', size=100, required=True),            
        'employee': fields.many2one('hr.employee','Employee'),
        'category': fields.many2one('helpdesk.category','Category'),
        'priority': fields.selection([('1', 'Highest'),('2', 'High'),('3', 'Normal'),('4', 'Low'),('5', 'Lowest'),],'Priority'),
        'technician': fields.many2one('res.users', 'Responsible'),        
        'asset': fields.many2one('asset.assets','Asset'),
        'description': fields.text('Description'),        
        'start_date': fields.datetime('Start Date', readonly=True),
        'response_date': fields.datetime('Response Date', readonly=True),
        'end_date': fields.datetime('End Date', states={'done': [('readonly', True)]}),
        'resolution': fields.text('Resolution'),
        'duration': fields.float('Duration', states={'done': [('readonly', True)]}),
        'active': fields.boolean('Active', required=False),
        'state':  fields.selection(AVAILABLE_STATES, 'Status', size=16, readonly=True),
        'conversation_ids': fields.one2many('helpdesk.conversation', 'ticket_id', 'Conversation'),
    }    
    _defaults = {        
        'active': lambda *a: 1,                        
        'state': lambda *a: 'draft',
        'start_date': lambda *a: fields.datetime.now(),
        'priority': lambda *a: '3',
    }
    
    _order = 'start_date desc'
    
    
    def create(self, cr, uid, values, context=None):		                        
        trackid = self._id_generator(cr, uid, context)
        values.update({'trackid':trackid})        
	return super(helpdesk_ticket, self).create(cr, uid, values, context = context)
    
helpdesk_ticket()