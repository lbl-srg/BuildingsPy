from multiprocessing import Pool
import buildingspy.simulate.Simulator as si


# Function to set common parameters and to run the simulation
def simulateCase(s):
    ''' Set common parameters and run a simulation.

    :param s: A simulator object.

    '''
    s.setStopTime(86400)
    # Kill the process if it does not finish in 1 minute
    s.setTimeOut(60)
    s.showProgressBar(False)
    s.printModelAndTime()
    s.simulate_translated()


def main():
    ''' Main method that configures and runs all simulations
    '''
    # Build list of cases to run
    li = []

    # First model
    model = 'Modelica.Mechanics.MultiBody.Examples.Systems.RobotR3.fullRobot'
    import os
    packagePath = os.path.join(os.environ['MODELICAPATH'],'Modelica 3.2.1')
    s = si.Simulator(model, 'dymola', 'case1', packagePath)
    s.addParameters({'startAngle1': -60})
    s.setSolver('dassl')
    s.showGUI(False)
    s.translate()
    li.append(s)

    # Second model
    import copy
    s2 = copy.deepcopy(s)
    s2.setOutputDirectory('case2')
    s2.addParameters({'startAngle1': 0})
    li.append(s2)

    # Run all cases in parallel
    po = Pool()
    po.map(simulateCase, li)
    # clean up
    s2.deleteTranslateDirectory()

# Main function
if __name__ == '__main__':
    main()
