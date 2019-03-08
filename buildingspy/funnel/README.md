# funnel

[![Build Status](https://travis-ci.org/lbl-srg/funnel.svg?branch=master)](https://travis-ci.org/lbl-srg/funnel)

Software to compare time series within user-specified tolerances.

A funnel is generated around the reference curve and the other curve is checked
to verify if it is inside the funnel. The funnel can be reshaped by resetting
tolerance. One potential application is to verify the development of building
HVAC control sequence. It compares data curves from real operation with
data curves from simulation using developed control sequences, to verify if the
developed control sequences have been implemented correctly so the same behavior
being achieved.

## How to run

To compile the C files, run
```
make build
```
To see usage information, start the tool with command line argument `--help`
```
bin/funnel --help
```
You can set the arguments as:
```
Usage: funnel [OPTIONS...]
  Compares time series within user-specified tolerances.

  --test             Name of CSV file to be tested.
  --reference        Name of CSV file with reference data.
  --output           Directory to save outputs.
  --atolx            Absolute tolerance in x direction.
  --atoly            Absolute tolerance in y direction.
  --rtolx            Relative tolerance in x direction.
  --rtoly            Relative tolerance in y direction.
  --help             Print this help.

  At least one tolerance must be specified for x and y.

  Typical use:
    ./funnel --reference trended.csv --test simulated.csv --atolx 0.002 --atoly 0.002 --output results/

```
To run an example, with `trended.csv` as base data and `simulated.csv` as test
data, run
```
./funnel --reference trended.csv --test simulated.csv --atolx 0.002 --atoly 0.002 --output results/
```

## How to run tests

To run all tests, run
```
make build test
```

## License

Modified 3-clause BSD, see [LICENSE.md](LICENSE.md).

## Copyright

See [copyright notice](COPYRIGHT.md).
