#!/usr/bin/env python
#############################################################
import csv
import matplotlib as mpl
mpl.use('Agg') # Needed for headless testing
import matplotlib.pyplot as plt
import numpy as np

def readCSVFile(filename):
    time = []
    value = []
    with open(filename) as csvDataFile:
        # csvReader = csv.reader(csvDataFile, quoting=csv.QUOTE_NONNUMERIC)
        csvReader = csv.reader(csvDataFile)
        for row in csvReader:
            try:
                time.append(float(row[0])/3600.0)
                value.append(float(row[1]))
            except ValueError:
                continue
    return time, value

if __name__=='__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description = 'Generate profile including curves for reference, test, and funnel data.',
        epilog = 'Use as processData.py '
    )
    parser.add_argument(\
                        '--reference_csv',
                        help='CSV file containing reference data set',
                        dest='ref')
    parser.add_argument(\
                        '--test_csv',
                        help='CSV file containing test data set',
                        dest='tes')
    parser.add_argument(\
                        '--lower_csv',
                        help='CSV file containing data set of lower curve of funnel',
                        dest='low')
    parser.add_argument(\
                        '--upper_csv',
                        help='CSV file containing data set of upper curve of funnel',
                        dest='upp')
    args = parser.parse_args()

    # ------- retrieve data sets from CSV files --------
    refTime, refValue = readCSVFile(args.ref)
    testTime, testValue = readCSVFile(args.tes)
    lowerTime, lowerValue = readCSVFile(args.low)
    upperTime, upperValue = readCSVFile(args.upp)

    fig = plt.figure(figsize=(20, 6))
    # plt.title('Data compare with funnel', fontweight='bold')
    plt.plot(testTime, testValue, 'b-', label='Test data', lw=1)
    plt.plot(refTime, refValue, 'r-', label='Reference data', lw=1)
    plt.plot(lowerTime, lowerValue, 'c-', label='_nolegend_', lw=0.5)
    plt.plot(upperTime, upperValue, 'c-', label='_nolegend_', lw=0.5)
    plt.legend(loc='best',fontsize='small')
    plt.xlabel('time [h]')
    plt.ylabel('Value')
    plt.xlim([np.min(testTime),np.max(testTime)])
    plt.ylim([np.min(lowerValue),np.max(upperValue)])
    plt.grid()
    fig.savefig("processData.pdf")
