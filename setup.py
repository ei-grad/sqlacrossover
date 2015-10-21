from setuptools import setup

setup(
    name='sqlacrossover',
    version='0.1',
    py_modules=['sqlacrossover'],
    install_requires=[
        'sqlalchemy',
    ],
    extras_require={
        'PostgreSQL': ['psycopg2'],
        'MySQL': ['python-mysqldb'],
    },
    entry_points={
        'console_scripts': [
            'sqlacrossover=sqlacrossover:main'
        ],
    },
)
