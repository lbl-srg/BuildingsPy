within MyModelicaLibrary.Obsolete;
model Constant "An obsolete model"
  extends Modelica.Blocks.Icons.Block;
  extends Modelica.Icons.ObsoleteModel;
  Modelica.Blocks.Sources.Constant const(k=1) "Constant source"
    annotation (Placement(transformation(extent={{-12,-10},{8,10}})));
annotation (
obsolete = "This model is obsolete.",
Documentation(info="<html>
This model is used in the regression test
to test an obsolete model.
</html>"));
end Constant;
