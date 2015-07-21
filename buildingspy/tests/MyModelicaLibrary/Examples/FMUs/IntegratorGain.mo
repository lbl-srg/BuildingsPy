within MyModelicaLibrary.Examples.FMUs;
block IntegratorGain "Block to demonstrate the FMU export"
  extends Modelica.Blocks.Interfaces.BlockIcon;

  parameter Real k = -1 "Gain";

  Modelica.Blocks.Interfaces.RealInput u "Input";
  Modelica.Blocks.Interfaces.RealOutput y1 "Output that depends on the state";
  Modelica.Blocks.Interfaces.RealOutput y2 "Output that depends on the input";

  Real x(start=0, fixed=true) "State";

equation
  der(x) = u;
  y1 = x;
  y2 = k*u;
 annotation (
Documentation(info="<html>
<p>
Block that is used to demonstrate the FMU export
and its dependency analysis.
</p>
</html>"),
  __Dymola_Commands(file="Resources/Scripts/Dymola/Examples/FMUs/IntegratorGain.mos"
        "Export FMU"));
end IntegratorGain;
