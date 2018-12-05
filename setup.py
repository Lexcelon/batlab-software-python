from setuptools import setup

def readme():
    with open('README.rst') as f:
        return f.read()

setup(name='batlab',
      version='0.5.30',
      description='Low level library for communication with the Batlab V1.0 Battery Testing System by Lexcelon',
      long_description=readme(),
      url='https://github.com/Lexcelon/batlab-software-python',
      author='Lexcelon, LLC',
      author_email='support@lexcelon.com',

      license='LGPL3',
      packages=['batlab'],
      # Needed to include the source files from the MANIFEST
      include_package_data=True,
      install_requires=['pyserial', 'future'],
      entry_points={
          'console_scripts': [
              'batlabutil = batlab.batlabutil:batlabutil',
          ],
      },
      test_suite='tests.batlab_tests',
      zip_safe=False)

#example based on
#https://python-packaging.readthedocs.io/en/latest/minimal.html
#and
#http://marthall.github.io/blog/how-to-package-a-python-app/
