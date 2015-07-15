from setuptools import setup
setup(name = 'pmlab',
    version = '0.1',
    description = 'Process Mining suite',
    author = ['Marc Sole','Josep Carmona'],
    author_email = 'jcarmona@lsi.upc.edu',
    packages = ['pmlab','pmlab.log','pmlab.ts','pmlab.pn','pmlab.cnet','pmlab.bpmn','pmlab.scripts'],
    package_data = {
        'pmlab.bpmn':['graphics/*.eps','graphics/*.gif'], #include figures
    },
    install_requires = ['graph_tool >= 2.2.17',
                        'pyparsing >= 1.5.2',
#                        'pygame >= 1.9.1',
                        'euclid >= 0.01',
                        'pydot >= 1.0',
#                        'hcluster',
                        'bitstring >= 1.0'
			]
    )
