from setuptools import setup

setup(
    name='geoometa',
    version='0.0.1',
    description='Geoo: project-wide utils and data-structures.',
    url='git@github.com:deniskolokol/geoo-meta.git',
    author='Denis Kolokol',
    author_email='dkolokol@gmail.com',
    license='MIT',
    packages=['geoometa'],
    install_requires=[
        'urllib3==1.26.4',
        'six==1.15.0',
        'certifi==2020.12.5',
        'python-dateutil==2.8.1',
        'elasticsearch==7.12.0',
        'elasticsearch-dsl==7.3.0'
    ],
    zip_safe=False
)
