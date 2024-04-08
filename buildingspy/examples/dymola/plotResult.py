#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

def main():
    """ Main method that plots the results
    """
    import os

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    from buildingspy.io.outputfile import Reader

    # Optionally, change fonts to use LaTeX fonts
    # from matplotlib import rc
    # rc('text', usetex=True)
    # rc('font', family='serif')

    # Read results
    ofr1 = Reader(os.path.join("buildingspy", "examples", "dymola",
                               "case1", "FlatPlateWithTank.mat"), "dymola")
    ofr2 = Reader(os.path.join("buildingspy", "examples", "dymola",
                               "case2", "FlatPlateWithTank.mat"), "dymola")
    (time1, TIn1) = ofr1.values("TIn.T")
    (time1, TOut1) = ofr1.values("TOut.T")
    (time2, TIn2) = ofr2.values("TIn.T")
    (time2, TOut2) = ofr2.values("TOut.T")

    # Plot figure
    fig = plt.figure()
    ax = fig.add_subplot(111)

    ax.plot(time1 / 3600, TIn1 - 273.15, 'r', label='$T_{in,1}(V=1.5 \\mathrm{m^3})$')
    ax.plot(time1 / 3600, TOut1 - 273.15, 'g', label='$T_{out,1}(V=1.5 \\mathrm{m^3})$')
    ax.plot(time2 / 3600, TIn2 - 273.15, 'b', label='$T_{in,2}(V=2.0 \\mathrm{m^3})$')
    ax.plot(time2 / 3600, TOut2 - 273.15, 'k', label='$T_{out,2}(V=2.0 \\mathrm{m^3})$')

    ax.set_xlabel('time [h]')
    ax.set_ylabel(r'Collector inlet and outlet temperature [$^\circ$C]')
    ax.set_xticks(list(range(25)))
    ax.set_xlim([0, 24])
    ax.legend()
    ax.grid(True)

    # Save figure to file
    plt.savefig('plot.pdf')
    plt.savefig('plot.png')

    # To show the plot on the screen, uncomment the line below
    # plt.show()


# Main function
if __name__ == '__main__':
    main()
