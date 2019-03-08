/*
 * tube.h
 *
 *  Created on: Apr 5, 2018
 *      Author: jianjun
 */

#ifndef TUBE_H_
#define TUBE_H_

double * interpolateValues(double* sourceX, double* sourceY, int sourceLength, double* targetX, int targetLength);

int compare(double* lower, double* upper, int refLen,
  double* testY, double* testX, int testLen,
  struct errorReport* err);

int validate(
  const struct data lower,
  const struct data upper,
  const struct data test,
  struct errorReport* err);

#endif /* TUBE_H_ */
