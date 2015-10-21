from setuptools import setup

setup(
    name='sqlacrossover',
    version='0.2.2',
    url='https://github.com/ei-grad/sqlacrossover',
    author='Andrew Grigorev',
    author_email='andrew@ei-grad.ru',
    description='SQLAlchemy-based cross-database migration tool',
    license="Apache License 2.0",
    py_modules=['sqlacrossover'],
    install_requires=[
        'sqlalchemy>=1.0',
    ],
    extras_require={
        'PostgreSQL': ['psycopg2'],
        'MySQL': ['pymysql'],
    },
    entry_points={
        'console_scripts': [
            'sqlacrossover=sqlacrossover:main'
        ],
    },
)
