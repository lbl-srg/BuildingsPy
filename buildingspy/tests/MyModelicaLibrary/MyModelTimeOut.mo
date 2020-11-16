within MyModelicaLibrary;
model MyModelTimeOut
  import Modelica;
initial equation
  Modelica_DeviceDrivers.OperatingSystem.sleep(3);
  Modelica.Utilities.Streams.print("Initial sleep time exceeded.");
end MyModelTimeOut;
