/*
 * tube.c
 *
 * Created on: Apr 5, 2018
 * Author: jianjun
 *
 * Functions:
 * ----------
 *   interpolateValues: interpolate sources data points
 *   compare: compare test value with tube
 *   validate: validate test curve and generate error report
 */


#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#include "data_structure.h"
#include "tubeSize.h"
#include "tube.h"

#ifndef min
#define min(a,b) ((a) < (b) ? (a) : (b))
#endif

#ifndef equ
#define equ(a,b) (fabs(a-b) < 1e-10 ? true : false)
#endif

/*
 * Function: interpolateValues
 * ---------------------------
 *   interpolate sources data points,
 *                                 sourceY[j] - sourceY[j-1]
 *     targetY[i] = sourceY[j-1] + ------------------------- * (targetX[i] - sourceX[j-1])
 *                                 sourceX[j] - sourceX[j-1]
 *
 *   sourceX: source data x value
 *   sourceY: source data y value
 *   sourceLength: total source data points
 *   targetX: target data x value
 *   targetLength: total target data points
 *
 *   return: targetY -- target data y value
 */
double * interpolateValues(double* sourceX, double* sourceY, int sourceLength, double* targetX, int targetLength) {
  if (sourceY == NULL || sourceLength == 0) {
    return sourceY;
  }
  int i;
  double* targetY = malloc(targetLength * sizeof(double));
  if (targetY == NULL){
  	  fputs("Error: Failed to allocate memory for targetY.\n", stderr);
  	  exit(1);
  }
  int j = 1;
  double x, x0, x1, y0, y1;

  for (i=0; i<targetLength; i++) {
    // Prevent extrapolating
    if (targetX[i] > sourceX[sourceLength-1]) {
      double *tmp = realloc(targetY, sizeof(double)*i);
      if (tmp == NULL){
    	  fputs("Error: Failed to reallocate memory for tmp.\n", stderr);
    	  exit(1);
      }
      targetY = tmp;
      break;
    }

    x = targetX[i];
    x1 = sourceX[j];
    y1 = sourceY[j];

    // Step sourceX to current targetX
    while ((x1<x) && (j+1 < sourceLength)) {
      j++;
      x1 = sourceX[j];
      y1 = sourceY[j];
    }

    x0 = sourceX[j-1];
    y0 = sourceY[j-1];

    // Prevent NaN -> division by zero
    if (!equ((x1-x0)*(x-x0), 0)) {
      targetY[i] = y0 + (((y1 - y0) / (x1 - x0)) * (x - x0));
    } else {
      targetY[i] = y0;
    }
  }

  return targetY;
}

/*
 * Function: compare
 * -------------------
 *   compare test value with data tube
 *
 *   lower: lower tube curve value
 *   upper: upper tube curve value
 *   refLen: total data points in tube curve
 *   testY: test curve value
 *   testX: test curve time value
 *   testLen: total data points in test curve
 *
 *   return: errorReport, data structure which includes;
 *              err->x -- time when there is error
 *              err->y -- error value
 *           err->n -- total time moment when there is error
 */
int compare(double* lower, double* upper, int refLen,
  double* testY, double* testX, int testLen,
  struct errorReport* err) {
  int i;
  int errArrSize = 1;
  err->original.n = 0;
  err->original.x = malloc(errArrSize * sizeof(double));
  if (err->original.x == NULL){
    fputs("Error: Failed to allocate memory for err->original.x.\n", stderr);
    return -1;
  }
  err->original.y = malloc(errArrSize * sizeof(double));
  if (err->original.y == NULL){
    fputs("Error: Failed to allocate memory for err->original.y.\n", stderr);
    return -1;
  }


  err->diff.n = min(testLen, refLen);
  err->diff.x = malloc(err->diff.n * sizeof(double));
  if (err->diff.x == NULL){
    fputs("Error: Failed to allocate memory for err->diff.x.\n", stderr);
    return -1;
  }
  err->diff.y = malloc(err->diff.n * sizeof(double));
  if (err->diff.y == NULL){
    fputs("Error: Failed to allocate memory for err->diff.y.\n", stderr);
    return -1;
  }

  for (i=0; i < err->diff.n; i++) {
    if (testY[i] < lower[i] || testY[i] > upper[i]) {
      err->original.x[err->original.n] = testX[i];
      if (testY[i] < lower[i]) {
        err->original.y[err->original.n] = lower[i]-testY[i];
      } else {
        err->original.y[err->original.n] = testY[i]-upper[i];
      }
      err->diff.y[i] = err->original.y[err->original.n];
      err->original.n++;
    } else {
      err->diff.y[i] = 0.0;
    }
    err->diff.x[i] = testX[i];
    // resize error arrays
    if (err->original.n == errArrSize) {
      errArrSize += 10;
      err->original.x = realloc(err->original.x, sizeof(double)*errArrSize);
      if (err->original.x == NULL){
        fputs("Error: Failed to reallocate memory for err->original.x.\n", stderr);
        return -1;
      }

      err->original.y = realloc(err->original.y, sizeof(double)*errArrSize);
      if (err->original.y == NULL){
        fputs("Error: Failed to reallocate memory for err->original.y.\n", stderr);
        return -1;
      }
    }
  }
  return 0;
}


/*
 * Function: validate
 * ------------------
 *   validate test curve and generate error report
 *
 *   lower: data structure for lower curve
 *   upper: data structure for upper curve
 *   test: data structure for test curve
 *
 *   return: 0 if there was success
 */
int validate(
  const struct data lower,
  const struct data upper,
  const struct data test,
  struct errorReport* err) {
  double* newLower = interpolateValues(lower.x, lower.y, lower.n, test.x, test.n);
  double* newUpper = interpolateValues(upper.x, upper.y, upper.n, test.x, test.n);
  int retVal = compare(newLower, newUpper, test.n, test.y, test.x, test.n, err);
  return retVal;
}
