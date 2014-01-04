within ;
package MyModelicaLibrary "My Modelica library"
  model MyModel
    replaceable Modelica.Blocks.Sources.Constant source(k=0.5) constrainedby
    Modelica.Blocks.Interfaces.SO
      annotation (Placement(transformation(extent={{-10,-10},{10,10}})));
  end MyModel;


  model MyStep
    extends MyModel(redeclare Modelica.Blocks.Sources.Step source(height=1));
  Modelica.Blocks.Interfaces.RealOutput y "Connector of Real output signal"
    annotation (Placement(transformation(extent={{100,-10},{120,10}})));
  equation
  connect(source.y, y) annotation (Line(
      points={{11,0},{56,0},{56,4.44089e-16},{110,4.44089e-16}},
      color={0,0,127},
      smooth=Smooth.None));
  annotation (Diagram(coordinateSystem(preserveAspectRatio=false, extent={{-100,
            -100},{100,100}}), graphics));
  end MyStep;


  annotation (uses(Modelica(version="3.2.1")));
end MyModelicaLibrary;
