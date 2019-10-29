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


#ifndef APPROX
#define APPROX
/* Structures */

struct options_s {
  unsigned int error_max;
  unsigned int cut_size;
  unsigned int noisy_vectors;
  unsigned int iterations;
  unsigned int remove_covered;
  unsigned int seed;
  unsigned int verbose;
  char *original_basis;
  double threshold;
  char majority;
  unsigned int bonus_covered;
  unsigned int penalty_overcovered;
  char *decomp_matrix;
};

/* type definitions */

#ifndef DBP_TYPES /* to make sure that we include these just once*/
#define DBP_TYPES
typedef char * vector;
typedef char ** matrix;
typedef unsigned long int * ivector; /* to save integer vectors */
typedef unsigned long int ** imatrix; /*       "        matrices */
#endif
typedef struct options_s options;

/* procedures */

int approximate(matrix Set, 
		int size, 
		int dim, 
		matrix B, 
		int k, 
		matrix O,
		options *opti);

void approx_help();

#endif
