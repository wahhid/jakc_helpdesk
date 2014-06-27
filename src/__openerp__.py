{
    'name' : 'Helpdesk Management',
    'version' : '1.0',
    'author' : 'JakC',
    'category' : 'Generic Modules/Helpdesk Management',
    'depends' : ['base_setup','base','mail','jakc_itms','jakc_assets'],
    'init_xml' : [],
    'data' : [			
        'security/ir.model.access.csv'
        'jakc_helpdesk_view.xml',
        'jakc_helpdesk_report_view.xml',
        'jakc_helpdesk_conversation_view.xml',
        'jakc_assets_view.xml',        
        'jakc_helpdesk_menu.xml',                        
        'res_config_view.xml',
        'res_users_view.xml',
        'report/jakc_helpdesk_report_view.xml',        
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}