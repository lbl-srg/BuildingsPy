/*
 * tubeSize.h
 *
 *  Created on: Apr 5, 2018
 *      Author: jianjun
 */

#include "stdbool.h"

#ifndef TUBESIZE_H_
#define TUBESIZE_H_

double minValue(double* array, int size);

double maxValue(double* array, int size);

double * tubeSize(struct data refData, struct tolerances tol);

#endif /* TUBESIZE_H_ */
