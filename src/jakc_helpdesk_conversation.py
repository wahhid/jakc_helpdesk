from openerp.osv import fields, osv
from datetime import datetime
from openerp.tools import html2plaintext
import string
import random
import time
import logging

_logger = logging.getLogger(__name__)

class helpdesk_conversation(osv.osv):
    _name = "helpdesk.conversation"
    _description = "Helpdesk Conversation"    
    
    def _send_email_notification(self, cr, uid, values, context=None):
        _logger.info(values['start_logger'])
        mail_mail = self.pool.get('mail.mail')
        mail_ids = []
        mail_ids.append(mail_mail.create(cr, uid, {
            'email_from': values['email_from'],
            'email_to': values['email_to'],
            'subject': values['subject'],
            'body_html': values['body_html'],
            }, context=context))
        mail_mail.send(cr, uid, mail_ids, context=context)
        _logger.info(values['end_logger'])    
        
    def save_conversation_action(self, cr, uid, ids, context=None):                
        message = self.browse(cr, uid, ids, context=context)[0]        
        values = {}
        values['ticket_id'] = message.ticket_id
        values['message_date'] = message.message_date
        values['description'] = message.description
        values['inbound'] = message.inbound                            
        #values['helpdesk_conversation_recipients'] = message.helpdesk_conversation_recipients
        #values['helpdesk_conversation_senders'] = message.helpdesk_conversation_senders
        #values['attachments'] = message.attachments        
        conversation_id = super(helpdesk_conversation,self).create(cr,uid,values,context=context)   
        
        ticket = self.pool.get('helpdesk.ticket').browse(cr, uid, values['ticket_id'],context=context)
        #employee = self.pool.get('hr.employee').browse(cr, uid, ticket.employee.id, context=context)
        
        for emp in message.helpdesk_conversation_recipients:            
            email_data = {}
            email_data['start_logger'] = 'Start Email Ticket Conversation Notification'
            email_data['email_from'] = 'helpdesk@jakc.com'
            email_data['email_to'] = emp.work_email
            email_data['subject'] = "<" + ticket.trackid + "> "  + ticket.name
            email_data['body_html'] = message.description
            email_data['end_logger'] = 'End Email Ticket Conversation Notification'
            self._send_email_notification(cr, uid, email_data, context=context)                      
                    
        return {'type': 'ir.actions.act_window_close'}
        
    _columns = {
        'ticket_id': fields.many2one('helpdesk.ticket', 'Ticket', readonly=True),            
        'helpdesk_conversation_senders': fields.many2many('hr.employee',
            'helpdesk_conversation_senders_rel',
            'helpdesk_conversation_id',
            'hr_employee_id',
            'Senders'
        ),        
        'helpdesk_conversation_recipients': fields.many2many('hr.employee', 
            'helpdesk_conversation_recipients_rel',
            'helpdesk_conversation_id',
            'hr_employee_id',
            'Recipients'),
        'message_date': fields.datetime('Date'),
        'name': fields.char('Name', size=100, required=True),
        'description': fields.text('Description'),        
        'attachments': fields.many2many('ir.attachment',string="Attachments"),             
        'inbound': fields.boolean('Inbound')
    }
    _order = "message_date desc"
            
    _defaults = {        
        'message_date': lambda *a: fields.datetime.now(),        
    }            
    
    def _process_incoming_conversation(self,cr, uid,context=None):        
        _logger.info('Process Incoming Conversation Started')
        return True
                
helpdesk_conversation()
