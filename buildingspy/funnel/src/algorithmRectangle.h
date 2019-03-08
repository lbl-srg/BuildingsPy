/*
 * algorithmRectangle.h
 *
 *  Created on: May 10, 2018
 *      Author: jianjun
 */

#ifndef ALGORITHMRECTANGLE_H_
#define ALGORITHMRECTANGLE_H_

typedef struct node {
  double val;
  struct node * next;
} node_t;

node_t * createNode();

node_t * addNode(node_t* head, double newVal);

int listLen(node_t* head);

double getNth(node_t* head, int index);

double * getListValues(node_t* head);

void lastNodeDeletion(node_t* head);

struct data calculateLower(struct data reference, double* tubeSize);

struct data calculateUpper(struct data reference, double* tubeSize);

struct data removeLoop(double* x, double* y, int size, int curInd);

double * removeRange(double* array, int size, int staInd, int count);

double * removeAt(double* array, int size, int ind);

double * insertAt(double* array, int size, int index, double item);

#endif /* ALGORITHMRECTANGLE_H_ */
