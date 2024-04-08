within MyModelicaLibrary.Obsolete.Examples;
model Constant "Test model for an obsolete model"

  MyModelicaLibrary.Obsolete.Constant const      "Constant source"
    annotation (Placement(transformation(extent={{-10,-12},{10,8}})));
  annotation (
  experiment(Tolerance=1e-6, StopTime=1.0),
  __Dymola_Commands(file="Resources/Scripts/Dymola/Obsolete/Examples/Constant.mos"
        "Simulate and plot"),
Documentation(info="<html>
<p>
This model is used to test BuildingsPy for the case of an obsolete model.
In Dymola 2020, obsolete models trigger an error in pedantic mode.
</p>
</html>"));
end Constant;
