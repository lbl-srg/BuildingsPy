within MyModelicaLibrary.Examples;
model MyStep "Test model for MyStep"
  import MyModelicaLibrary;
  MyModelicaLibrary.MyStep myStep
    annotation (Placement(transformation(extent={{-10,-10},{10,10}})));
  annotation (__Dymola_Commands(file="Resources/Scripts/Dymola/Examples/MyStep.mos"
        "Simulate and plot"));
end MyStep;
