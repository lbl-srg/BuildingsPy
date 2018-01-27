within ;
package MyModelicaLibrary "My Modelica library"

  constant Real one = 1 "A constant that is set to 1";
  constant Real two = 2 "A constant that is set to 2";

  type Reset = enumeration(
    Disabled   "Disabled",
    Parameter   "Use parameter value",
    Input   "Use input signal")
    "Options for integrator reset"
    annotation (
    preferedView="info",
    Documentation(info="<html>
<p>
This enumeration tests whether the package.order is created correctly.
See <code>buildingspy/tests/Test_development_refactor_Annex60</code>.
</p>
</html>"));

  annotation (uses(Modelica(version="3.2.1")));
end MyModelicaLibrary;
