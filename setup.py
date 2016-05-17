from setuptools import setup

setup(
    name='swilite',
    version='0.1.1',
    author='Eric Langlois',
    author_email='eric@langlois.xyz',
    license='MIT',
    keywords='Prolog SWI-Prolog',
    url='https://github.com/EdTsft/swilite',
    packages=['swilite'],
    description='A light-weight object-oriented interface to SWI-Prolog.',
    install_requires=[],
    test_suite='nose.collector',
    tests_require=[
        'nose',
    ]
)
