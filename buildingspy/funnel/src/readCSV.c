/*
 * readCSV.c
 *
 * Created on: Apr 4, 2018
 * Author: jianjun
 *
 * Functions:
 * ----------
 *   readCSV : reads in CSV file and returns data structure
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "data_structure.h"
#include "readCSV.h"

/*
 * Function: readCSV
 * -----------------
 *   read in CSV file and returns data structure. The CSV file should be two columns, delimited by comma or semicolon.
 *
 *   filename: path to the CSV file
 *   skipLines: number of head lines to be skipped
 *
 *   returns: the data structure "inputs", which includes fist and second data set, and the number of rows
 */
struct data readCSV(const char * filename, int skipLines) {
  int i;
  struct data inputs;
  double *time;
  double *value;
  int arraySize = 1;
  int rowCount = 0;
  char buf[100];

  FILE *fp = fopen(filename, "r");

  time = malloc(sizeof(double) * arraySize);
  if (time == NULL){
  	  fputs("Error: Failed to allocate memory for time.\n", stderr);
  	  exit(1);
  }
  value = malloc(sizeof(double) * arraySize);
  if (value == NULL){
	  fputs("Error: Failed to allocate memory for value.\n", stderr);
	  exit(1);
  }

  memset(time,0,sizeof(double)*arraySize);
  memset(value,0,sizeof(double)*arraySize);

  for (i=0; i<skipLines; i++) {
    fgets(buf,100,fp); // skip the first "skipLines" lines
  }

  while (fscanf(fp, "%lf%*[,;]%lf\n", &time[rowCount], &value[rowCount]) == 2) {
    if (rowCount == arraySize ) {
      // need more space
      arraySize += 5;
      double *time_tmp = realloc(time, sizeof(double)*(arraySize+1));
      double *value_tmp = realloc(value, sizeof(double)*(arraySize+1));
      if (time_tmp == NULL || value_tmp == NULL) {
        fputs("Fatal error -- out of memory!\n", stderr);
        exit(1);
      }
      time = time_tmp;
      value = value_tmp;
    }
    rowCount++;
  }
  fclose(fp);

  inputs.x = time;
  inputs.y = value;
  inputs.n = rowCount;

  return inputs;
}
