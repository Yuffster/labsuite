from setuptools import setup, find_packages

config = {
    'description': "A suite of tools for portable automated scientific protocols.",
    'author': "Michelle Steigerwalt",
    'url': 'http://opentrons.com',
    'version': '0.4',
    'install_requires': ['pyyaml', 'pyserial'],
    'packages': find_packages(exclude=["tests"]),
    'package_data': {
        "labsuite": [
            "config/containers/**/*.yml",
            "compilers/data/*"
        ]
    },
    'scripts': [
        'bin/labsuite-compile'
    ],
    'name': 'labsuite',
    'test_suite': 'nose.collector',
    'zip_safe': False
}

setup(**config)
