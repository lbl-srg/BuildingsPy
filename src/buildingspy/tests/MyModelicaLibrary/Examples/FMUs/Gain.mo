within MyModelicaLibrary.Examples.FMUs;
model Gain "Block to test FMU export"

  Modelica.Blocks.Math.Gain gain(k=1)
    annotation (Placement(transformation(extent={{-10,-10},{10,10}})));
  Modelica.Blocks.Interfaces.RealOutput y "Output signal connector"
    annotation (Placement(transformation(extent={{100,-10},{120,10}})));
  Modelica.Blocks.Interfaces.RealInput u "Input signal connector"
    annotation (Placement(transformation(extent={{-140,-20},{-100,20}})));
equation
  connect(gain.y, y) annotation (Line(
      points={{11,0},{110,0}},
      color={0,0,127},
      smooth=Smooth.None));
  connect(gain.u, u) annotation (Line(
      points={{-12,0},{-120,0}},
      color={0,0,127},
      smooth=Smooth.None));
  annotation (Diagram(coordinateSystem(preserveAspectRatio=false, extent={{-100,
            -100},{100,100}}), graphics),
  __Dymola_Commands(file="Resources/Scripts/Dymola/Examples/FMUs/Gain.mos"
        "Export FMU"));
end Gain;
