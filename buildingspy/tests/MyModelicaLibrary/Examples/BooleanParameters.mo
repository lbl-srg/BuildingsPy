within MyModelicaLibrary.Examples;
model BooleanParameters "This model tests setting values of boolean parameters"
   parameter Boolean p1 = false;
   parameter Boolean p2 = true;
  annotation (experiment(Tolerance=1e-6, StopTime=1.0),
  __Dymola_Commands(file="Resources/Scripts/Dymola/Examples/BooleanParameters.mos"
        "Simulate and plot"),
Documentation(info="<html>
This model is used in the regression test
to set boolean parameters.
</html>"));
end BooleanParameters;
