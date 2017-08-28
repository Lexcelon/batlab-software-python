from setuptools import setup

setup(name='batlab',
      version='0.2.1',
      description='low leve commuication between a PC and a batlab unit',
      url='https://github.com/Lexcelon/batlab-software-python',
      author='Dan Cambron',
      author_email='john.broadbent.ky@gmail.com',
      #author_email='danielcambron11@gmail.com','john.broadbent.ky@gmail.com','support@lexcelon.com.',
      license='GPL3',
      packages=['batlab'],
      install_requires=['pyserial'],
      zip_safe=False)
	  
	  
#example based on 
#https://python-packaging.readthedocs.io/en/latest/minimal.html
#and
#http://marthall.github.io/blog/how-to-package-a-python-app/
