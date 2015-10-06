within MyModelicaLibrary;
model MyModel
  replaceable Modelica.Blocks.Sources.Constant source(k=0.5) constrainedby
    Modelica.Blocks.Interfaces.SO
    annotation (Placement(transformation(extent={{-10,-10},{10,10}})));
end MyModel;

