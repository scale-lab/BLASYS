#ifndef _DBP_DRIVER
#define _DBP_DRIVER
#include <string.h>
#include <math.h>
#include <limits.h>
#include <stdlib.h>
#include "approx.h"
#include "utils.h"

//#define DEBUG

/*
 * Helping function sab, computes error
 */
typedef unsigned int mwSize;

unsigned long int sab(matrix A, matrix B, matrix C, int n, int m, int k, char *mode);
int asso(char* filename, int k);

#endif
