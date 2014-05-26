{
    'name' : 'Helpdesk Management',
    'version' : '1.0',
    'author' : 'JakC',
    'category' : 'Generic Modules/Helpdesk Management',
    'depends' : ['base_setup','base','mail','jakc_itms','jakc_assets'],
    'init_xml' : [],
    'data' : [			
        'jakc_helpdesk_view.xml',				
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}