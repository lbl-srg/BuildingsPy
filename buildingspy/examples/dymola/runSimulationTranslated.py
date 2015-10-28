import buildingspy.simulate.Simulator as si


# Function to set common parameters and to run the simulation
def simulateTranslatedModel(s):
    ''' Set common parameters and run a simulation
        of an already translated model.

    :param s: A simulator object that has already been translated.

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
    import copy
    import shutil

    from multiprocessing import Pool
    # Build list of cases to run
    li = []

    # First model
    model = 'Buildings.Controls.Continuous.Examples.PIDHysteresis'
    s1 = si.Simulator(model, 'dymola')
    s1.setOutputDirectory('case1')
    s1.addParameters({'con.eOn': 0.1})
    s1.setSolver('dassl')
    s1.showGUI(False)
    # Translate the model
    s1.translate()
    # Add the model to the list of models to be simulated
    li.append(s1)

    # Second model
    s2 = copy.deepcopy(s1)
    s2.setOutputDirectory('case2')
    s2.addParameters({'con.eOn': 1})
    li.append(s2)

    # Run both models in parallel
    po = Pool()
    po.map(simulateTranslatedModel, li)
    # Clean up
    # Clean up
    shutil.rmtree('case1')
    shutil.rmtree('case2')
    s1.deleteTranslateDirectory()

# Main function
if __name__ == '__main__':
    main()
