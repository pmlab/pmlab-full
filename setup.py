from setuptools import setup
setup(name = 'pmlab',
    version = '0.1',
    description = 'Process Mining suite',
    author = ['Marc Sole','Josep Carmona'],
    author_email = 'jcarmona@lsi.upc.edu',
    packages = ['pmlab','pmlab.log','pmlab.ts','pmlab.pn','pmlab.log_ts','pmlab.cnet','pmlab.bpmn','pmlab.scripts','pmlab.rapidprom'],
    package_data = {
        'pmlab.bpmn':['graphics/*.eps','graphics/*.gif'], #include figures
        'pmlab.rapidprom':['*.rmp'], 
    },
    install_requires = ['pyparsing == 2.0.1',
                        'pygame == 1.9.2',
                        'euclid == 0.01',
                        'pydot == 1.0.28',
                        'dedupe-hcluster == 0.3.3',
                        'bitstring == 3.1.2'
			]
    )
