within MyModelicaLibrary.Examples;
model Constants "Test model for two constant sources"

  Modelica.Blocks.Sources.Constant[2] const1(each k=1) "Constant source"
    annotation (Placement(transformation(extent={{0,20},{20,40}})));
   Modelica.Blocks.Sources.Constant[3, 2] const2(each k=2) "Constant source"
    annotation (Placement(transformation(extent={{0,-20},{20,0}})));
  Modelica.Blocks.Sources.Constant const3(k=1) "Constant source"
    annotation (Placement(transformation(extent={{0,-60},{20,-40}})));
  annotation (
  __Dymola_Commands(file="Resources/Scripts/Dymola/Examples/Constants.mos"
        "Simulate and plot"),
Documentation(info="<html>
This model is used in the regression test
to set a vector of parameters.
</html>"));
end Constants;
