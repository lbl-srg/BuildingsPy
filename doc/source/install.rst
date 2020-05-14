Install and Uninstall BuildingsPy
=================================

To install the *BuildingsPy* module, install
`pip <https://pip.pypa.io/en/latest/>`_ and run from a console

.. parsed-literal::

   python -m pip install --user buildingspy

To uninstall, run

.. parsed-literal::

   python -m pip uninstall buildingspy

To install the latest development version, run

.. parsed-literal::

   python -m pip install --user buildingspy@git+https://github.com/lbl-srg/buildingspy.git@master


To run regression tests with *BuildingsPy*,
*PyTidyLib* needs to be installed. On Ubuntu, this can be done using

.. parsed-literal::

   sudo pip install pytidylib
   sudo apt-get install tidy

For other operating systems, see the instructions at the
`PyTidyLib <https://pythonhosted.org/pytidylib/>`_
site.
