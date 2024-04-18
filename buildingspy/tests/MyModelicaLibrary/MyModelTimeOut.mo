within MyModelicaLibrary;
model MyModelTimeOut
  parameter Integer sec = 2 "Time for sleep in seconds";
  parameter Integer r = mySleep(sec) "Return value of mySleep";
   function mySleep
    input Integer sec "Sleep time in seconds";
    output Integer r "Return value";
    external "C" r = MySleep(sec)
      annotation (
       Include="#include <MySleep.c>",
       IncludeDirectory="modelica://MyModelicaLibrary/Resources/C-Sources");
  end mySleep;

end MyModelTimeOut;
