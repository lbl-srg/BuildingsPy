"""
This module contains the class
:class:`buildingspy.simulate.OpenModelica`,
:class:`buildingspy.simulate.Optimica`
and
:class:`buildingspy.simulate.Dymola`
that can be used to automate simulations using OpenModelica, Optimica and Dymola,
respectively.

Their API is identical where possible, but each
class may have methods that are only applicable for
one of the simulators.
For example, the method
:func:`buildingspy.simulate.Optimica.Simulator.generateHtmlDiagnostics`
is only available for Optimica.

"""
