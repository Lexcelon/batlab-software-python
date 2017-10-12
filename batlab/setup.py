from setuptools import setup

setup(name='batlab',
      version='0.3.0',
      description='Low level library for communication with the Batlab V1.0 Battery Testing System by Lexcelon',
      url='https://github.com/Lexcelon/batlab-software-python',
      author='Lexcelon, LLC',
      author_email='dcambron@lexcelon.com',
      #author_email='danielcambron11@gmail.com','john.broadbent.ky@gmail.com','support@lexcelon.com.',
      license='GPL3',
      packages=['batlab'],
      install_requires=['pyserial'],
	  scripts=['batlab-util'],
      zip_safe=False)
	  
	  
#example based on 
#https://python-packaging.readthedocs.io/en/latest/minimal.html
#and
#http://marthall.github.io/blog/how-to-package-a-python-app/
