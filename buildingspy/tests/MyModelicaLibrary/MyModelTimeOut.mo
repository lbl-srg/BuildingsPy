within MyModelicaLibrary;
model MyModelTimeOut
  parameter Integer sec = 5 "Time for sleep in seconds";
  Real r "Return value of mySleep";

  function mySleep
    input Integer sec "Sleep time in seconds";
    output Integer r "Return value";
    external "C" r = MySleep(sec)
      annotation (
       Include="#include <MySleep.c>",
       IncludeDirectory="modelica://MyModelicaLibrary/Resources/C-Sources");
  end mySleep;
equation
  r = mySleep(sec=sec);
end MyModelTimeOut;
