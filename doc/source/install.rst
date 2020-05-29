Install and Uninstall BuildingsPy
=================================

To install the *BuildingsPy* module, install
`pip <https://pip.pypa.io/en/latest/>`_ and run from a console

.. parsed-literal::

   python3 -m pip install --user buildingspy

To uninstall, run

.. parsed-literal::

   python3 -m pip uninstall buildingspy

To install the latest development version, run

.. parsed-literal::

   python3 -m pip install --user buildingspy@git+https://github.com/lbl-srg/buildingspy.git@master


To clone BuildingsPy for development, together with its dependency ``funnel`` (https://github.com/lbl-srg/funnel), run

.. parsed-literal::

   git clone git@github.com:lbl-srg/BuildingsPy.git
   python3 -m pip install --user pyfunnel@git+https://github.com/lbl-srg/funnel.git@v0.1.0
