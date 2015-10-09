within MyModelicaLibrary.Examples;
model ParameterEvaluation
  "This model is used to test whether Python throws an exception"
  parameter Real x = 0.1;
  parameter Integer n = integer(1/x) "Dimension";
  Real T[n] "Vector";
equation
  der(T) = ones(n)
  annotation (Documentation(info="<html>
<p>
This model is used in the Python regression tests to ensure that BuildingsPy
throws an exception if it attempts to change a structural parameter after
the compilation.
</p>
</html>"));

end ParameterEvaluation;
