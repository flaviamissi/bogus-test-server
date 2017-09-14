# Copyright 2017 bogus-test-server authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

from distutils.core import setup

setup(name='bogus',
      version='0.2.0',
      description='A simple bogus server to use in tests',
      author='Globo.com',
      author_email='flavia.missi@corp.globo.com',
      url='https://github.com/globocom/bogus-test-server#bogus-test-server',
      py_modules=["bogus.server"]
     )
