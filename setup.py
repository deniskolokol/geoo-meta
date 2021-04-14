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
        'elasticsearch-dsl',
        'mongoengine'
    ],
    zip_safe=False
)
