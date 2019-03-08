#include "compare.h"

#include "mkdir_p.h"

/*
 * Function: writeToFile
 * -----------------------
 *   write input data structure to files
 *
 *   outDir: directory to save the output files
 *   fileName: file name for storing base CSV data
 *   data: data to be written
 */
int writeToFile(
  const char *outDir,
  const char* fileName,
  struct data* data) {

  int i = 0;
  const char lastChar = outDir[(strlen(outDir)-1)];
  #ifdef _WIN32
  /* Windows supports forward and backward slash */
    bool addSlash = (lastChar == '/' || lastChar == '\\') ? false : true;
  #else
    bool addSlash = (lastChar == '/') ? false : true;
  #endif

  mkdir_p(outDir);

  char* fname = NULL;
  if (addSlash)
    fname = (char*)malloc((strlen(outDir) + strlen(fileName) + 2) * sizeof(char));
  else
    fname = (char*)malloc((strlen(outDir) + strlen(fileName) + 1) * sizeof(char));

  if (fname == NULL){
    fprintf(stderr, "Error: Failed to allocate memory for fname in writeToFile.\n");
    return -1;
  }

  strcpy(fname, outDir);

  #ifdef _WIN32
  if (addSlash)
    strcat(fname, "\\");
  #else
  if (addSlash)
    strcat(fname, "/");
  #endif

  strcat(fname, fileName);

  FILE *fil = fopen(fname, "w+");
  free(fname);

  if (fil == NULL){
    fprintf(stderr, "Error: Failed to open '%s' in writeToFile.\n", fname);
    return -1;
  }

  fprintf(fil, "%s\n", "x,y");
  for (i = 0; i < data->n; i++) {
    fprintf(fil, "%lf,%lf\n", data->x[i], data->y[i]);
  }

/*  if (data.validateReport.errors.original.n != 0) {
    fprintf(f5, "The test result is invalid.\n");
    fprintf(f5, "There are errors at %zu points.\n", data.validateReport.errors.original.n);
    for (i =0; i < data.validateReport.errors.diff.n; i++){
      fprintf(f5, "%lf,%lf\n",
          data.validateReport.errors.diff.x[i],
          data.validateReport.errors.diff.y[i]);
    }
  }
  else
    fprintf(f5, "The test result is valid.\n");
*/
  fclose(fil);

  return 0;
}

struct data *newData(
  const double x[],
  const double y[],
  size_t n) {

  struct data *retVal = malloc (sizeof (struct data));
  if (retVal == NULL){
    fputs("Error: Failed to allocate memory for data.\n", stderr);
    return NULL;
  }
  // Try to allocate vector data, free structure if fail.

  retVal->x = malloc (n * sizeof (double));
  if (retVal->x == NULL) {
    fputs("Error: Failed to allocate memory for data.x.\n", stderr);
    free (retVal);
    return NULL;
  }
  memcpy(retVal->x, x, sizeof(double)*n);

  retVal->y = malloc (n * sizeof (double));
  if (retVal->y == NULL) {
    fputs("Error: Failed to allocate memory for data.y.\n", stderr);
    free (retVal->x);
    free (retVal);
    return NULL;
  }
  memcpy(retVal->y, y, sizeof(double)*n);

  // Set size and return.
  retVal->n = n;
  return retVal;
}

void freeData (struct data *dat) {
  if (dat != NULL) {
      free (dat->x);
      free (dat->y);
      free (dat);
  }
}

/*
 * Function: compareAndReport
 * -----------------------
 *   This function does the actual computations. It is introduced so that it
 *   can be called from Python in which case the argument parsing of main
 *   is not needed.
 */
int compareAndReport(
  const double* tReference,
  const double* yReference,
  const size_t nReference,
  const double* tTest,
  const double* yTest,
  const size_t nTest,
  const char * outputDirectory,
  const double atolx,
  const double atoly,
  const double rtolx,
  const double rtoly){

  int retVal;

  struct data * baseCSV = newData(tReference, yReference, nReference);
  struct data * testCSV = newData(tTest, yTest, nTest);
  struct tolerances tolerances;
  tolerances.atolx = atolx;
  tolerances.atoly = atoly;
  tolerances.rtolx = rtolx;
  tolerances.rtoly = rtoly;
  // Calculate tube size (half-width and half-height of rectangle)
  //printf("useRelative=%d\n", arguments.useRelativeTolerance);
  double* tube = tubeSize(*baseCSV, tolerances);

  // Calculate the data set of lower and upper curve around base
  struct data lowerCurve = calculateLower(*baseCSV, tube);
  struct data upperCurve = calculateUpper(*baseCSV, tube);

  // Validate test curve and generate error report
  if (lowerCurve.n == 0 || upperCurve.n == 0){
    fputs("Error: lower or upper curve has 0 elements.\n", stderr);
    return 1;
  }
  struct reports validateReport;

  retVal = validate(lowerCurve, upperCurve, *testCSV, &validateReport.errors);
  if (retVal != 0)
    return retVal;

  /* Write data to files */
  retVal = writeToFile(outputDirectory, "reference.csv", baseCSV);
  if (retVal != 0)
    return retVal;
  retVal = writeToFile(outputDirectory, "lowerBound.csv", &lowerCurve);
  if (retVal != 0)
    return retVal;
  retVal = writeToFile(outputDirectory, "upperBound.csv", &upperCurve);
  if (retVal != 0)
    return retVal;
  retVal = writeToFile(outputDirectory, "test.csv", testCSV);
  if (retVal != 0)
    return retVal;
  retVal = writeToFile(outputDirectory, "errors.csv", &validateReport.errors.diff);
  if (retVal != 0)
    return retVal;

  freeData(baseCSV);
  freeData(testCSV);

  return retVal;
}
