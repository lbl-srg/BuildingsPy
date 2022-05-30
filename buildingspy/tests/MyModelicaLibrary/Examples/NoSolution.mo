within MyModelicaLibrary.Examples;
model NoSolution
  Real x(start=0, fixed=true) "State";
  Real y(start=1);
equation
  der(x) = 1;
  cos(y) = 2*x;

annotation (
    Documentation(info = "<p>
Model with equations that have no solution.
</p>"),
experiment(Tolerance=1e-6, StopTime=1.0),
__Dymola_Commands(file="Resources/Scripts/Dymola/Examples/NoSolution.mos"
        "Simulate and plot"));
end NoSolution;
