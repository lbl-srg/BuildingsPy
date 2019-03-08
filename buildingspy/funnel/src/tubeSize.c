/*
 * tubeSize.c
 *
 * Created on: Apr 4, 2018
 * Author: jianjun
 *
 * Functions:
 * ----------
 *   minValue : find minimum value of an array
 *   maxValue : find maximum value of an array
 *   setStandardBaseAndRatio : calculate standard values for baseX, baseY and ratio
 *   setFormerBaseAndRatio : calculate former standard values for baseX, baseY and ratio
 *   tubeSize : calculate tubeSize (half-width and half-height of rectangle)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <math.h>

#include "data_structure.h"
#include "tubeSize.h"

#ifndef max
#define max(a,b) ((a) > (b) ? (a) : (b))
#endif

#ifndef min
#define min(a,b) ((a) < (b) ? (a) : (b))
#endif

#ifndef equ
#define equ(a,b) (fabs(a-b) < 1e-10 ? true : false)
#endif


/*
 * Function: minValue
 * ------------------
 *   find minimum value of an array
 *
 *   array: data array
 *   size: data array size
 *
 *   return: minimum value of the data array
 */
double minValue(double* array, int size) {
  int i;
  double min;
  min = array[0];
  for (i=0; i<size; i++) {
    if (array[i] < min) {
      min = array[i];
    }
  }
  return min;
}

/*
 * Function: maxValue
 * ------------------
 *   find maximum value of an array
 *
 *   array: data array
 *   size: data array size
 *
 *   return: maximum value of the data array
 */
double maxValue(double* array, int size) {
  int i;
  double max;
  max = array[0];
  for (i=0; i<size; i++) {
    if (array[i] > max) {
      max = array[i];
    }
  }
  return max;
}

/*
 * Function: setData
 * -----------------
 *   find maximum values and value ranges in x and y of reference data
 *
 *   refData: CSV data which will be used as reference
 *
 *   return : an array "results" that includes:
 *              rangeX -- value range of x
 *              rangeY -- value range of Y
 *              maxX   -- maximum x
 *              maxY   -- maximum y
 */
double * setData(struct data refData) {
	double rangeX, rangeY;
	double* results = malloc(4 * sizeof(double));

	double maxX = maxValue(refData.x,refData.n);
	double minX = minValue(refData.x,refData.n);

	double maxY = maxValue(refData.y,refData.n);
	double minY = minValue(refData.y,refData.n);

	rangeX = maxX - minX;
	rangeY = maxY - minY;

	results[0] = rangeX;
	results[1] = rangeY;
	results[2] = maxX;
	results[3] = maxY;
	return results;
}


/*
 * Function: tubeSize
 * ------------------
 *   calculate tubeSize (half-width and half-height of rectangle)
 *
 *   refData: CSV data which will be used as reference
 *   tol    : data structure containing absolute tolerance (atolx, atoly)
 *            and relative tolerance (rtolx, rtoly)
 *
 *   return : an array "tubeSize" that includes:
 *                   x  -- half width of rectangle
 *                   y  -- half height of rectangle
 *               rangeX -- value range of x
 *               rangeY -- value range of y
 */
double * tubeSize(struct data refData, struct tolerances tol) {
  double x = 1e-10, y = 1e-10, rangeX, rangeY, maxX, maxY;
  double* tubeSize = malloc(4 * sizeof(double));

  double *standValue;

  standValue = setData(refData);
  rangeX = standValue[0];
  rangeY = standValue[1];
  maxX   = standValue[2];
  maxY   = standValue[3];

  if ((equ(tol.atolx,0) && equ(tol.rtolx, 0)) || (equ(tol.atoly,0) && equ(tol.rtoly, 0))) {
	  fputs("Error: At least one tolerance has to be set for both, x and y.\n", stderr);
	  exit(1);
  }

  if (equ(rangeX, 0)) {
	  x = max(1e-5, 1e-5*fabs(maxX));
  } else {
	  x = max(tol.atolx, tol.rtolx * rangeX);
  }

  if (equ(rangeY, 0)) {
  	  y = max(1e-5, 1e-5*fabs(maxY));
    } else {
  	  y = max(tol.atoly, tol.rtoly * rangeY);
    }

  tubeSize[0] = x;
  tubeSize[1] = y;
  tubeSize[2] = rangeX;
  tubeSize[3] = rangeX;

  return tubeSize;
}
