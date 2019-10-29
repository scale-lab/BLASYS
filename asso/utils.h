/*
Copyright (c) 2007 Pauli Miettinen

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
*/


#ifndef _DBP_UTILS
#define _DBP_UTILS

#include <stdio.h>

#ifndef DBP_TYPES /* to make sure that we typedef these just once */
#define DBP_TYPES
typedef char *vector;
typedef char **matrix;
typedef unsigned long int *ivector; /* to save integer vectors */
typedef unsigned long int **imatrix; /*       "        matrices */
#endif

#define MAX_LINELENGTH 4096 /* Longest line in sparse input matrix */

/* Some new types here... */

struct selestr {
  unsigned int c;
  struct selestr *n;
};

typedef struct selestr selement;
typedef selement **smatrix;

matrix read_matrix(const char *file, int *s, int *d);

matrix read_sparse_matrix(const char *file, int *s, int *d);

int print_matrix(const char *file, matrix S, int s, int d);

int print_sparse_matrix(const char *file, matrix S, int s, int d);

void free_matrix(matrix M, int n);

/* Initials a seed for random number generator and return NULL if 'seed' != 0.
 * Otherwise returns a pointer to random number character device to be used
 * with 'give_rand()'.
 */
FILE * init_seed(unsigned int seed);

/* Returns a random number as an unsigned integer. If 'randdev' is is NULL,
 * uses standard library 'rand()', otherwise uses given character device. */
unsigned int give_rand(FILE *randdev);


#endif
