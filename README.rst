Batlab library for Python
=========================

.. image:: https://travis-ci.org/Lexcelon/batlab-software-python.svg?branch=master
	   :target: https://travis-ci.org/Lexcelon/batlab-software-python

.. image:: https://badge.fury.io/py/batlab.svg
	   :target: https://badge.fury.io/py/batlab

.. image:: https://readthedocs.org/projects/batlab-software-python/badge/?version=latest
	   :target: http://batlab-software-python.readthedocs.io/en/latest/?badge=latest
	   :alt: Documentation Status

|

``batlab-software-python`` is a Python library and example command line script to interact with a pool of Batlabs over USB. This tool is designed for hobbyists and more advanced users who would like to incorporate the Batlab hardware in their own cell testing workflow or environment.

Requirements
------------

Python >=3.4 is currently supported by this module.

Python >=2.7 is not yet supported.

Installation
------------

To install the latest release you can use `pip <https://pip.pypa.io/en/stable/>`_:

``$ pip install batlab``

To upgrade, you can run:

``$ pip install batlab --upgrade`` or ``$ pip install batlab -U``.

Documentation
-------------

Documentation for this library is hosted at `Read the Docs <https://batlab-software-python.readthedocs.io/en/latest/?badge=latest>`_.

Usage
-----

The library can be imported into your own programs, or you may use the provided example Batlab Utility Script.

Batlab Utility Script
~~~~~~~~~~~~~~~~~~~~~

The Batlab Utility Script allows users to perform basic interactions with a pool of connected Batlab units through a simple command-line interface.

To run the script, make sure the ``batlab`` package is installed and then run:

``$ batlabutil``

Type ``help`` to display the list of commands in the script and how to use them. The intention for the script is to serve as an example for users to write their own battery cell test software using the Batlab library.

Contributing
------------

When contributing to this repository, please first discuss the change you wish to make via issue, email, or any other method with the owners of this repository.

Git branching model
~~~~~~~~~~~~~~~~~~~

We follow the development model described `here <http://nvie.com/posts/a-successful-git-branching-model/>`_. Anything in the ``master`` branch is considered production. Most work happens in the ``develop`` branch or in a feature branch that is merged into ``develop`` before being merged into ``master``.

Documenting
~~~~~~~~~~~



Running tests
~~~~~~~~~~~~~

To run the unit tests, from the root directory run:

``$ python setup.py test``

Deployment
~~~~~~~~~~

This library is deployed to `PyPi <https://pypi.python.org/pypi/batlab>`_. Builds are generated with `Travis CI <https://travis-ci.org/Lexcelon/batlab-software-python>`_ with each pushed commit. When a new tag is pushed or merged into ``master``, that build is automatically deployed to end users through PyPi.

License
-------

This library is licensed under LGPL-3.0 - see `LICENSE <https://github.com/Lexcelon/batlab-software-python/blob/master/LICENSE>`_ for details.

Acknowledgements
----------------

Thank you to our backers on `Kickstarter <https://www.kickstarter.com/projects/1722018962/batlab-a-battery-testing-system-for-lithium-ion-18>`_ who made this project possible.

Documentation created with `guide <https://samnicholls.net/2016/06/15/how-to-sphinx-readthedocs/>`_ from Sam Nicholls.
