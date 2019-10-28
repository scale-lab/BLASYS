#include "driver.h"
#include "stdlib.h"
//#define DEBUG

/* The Main function */
int asso(char *filename, int k)
{
    // char *filename;	
    // int	k;
    mwSize n, m, t_length, b_length;
    int i, ti, bi, bestBonusCovered, bestPenaltyOvercovered;
    unsigned long int error, bestError;
    double bp, bn, bestThreshold;
    matrix D, S, B, bestS, bestB;
    options opti = {0,     /* error_max */
		10,    /* cut_size */
		0,     /* noisy_vectors */
		0,     /* iterations */
		1,     /* remove_covered */
		0,     /* seed */
		0,     /* verbose */
		NULL,  /* original_basis */
		1.0,   /* threshold */
		0,     /* majority */
		1,     /* bonus_covered */
		1,     /* penalty_overcovered */
		NULL}; /* decomp matrix */  

    /* allocate memory and fill the matrix*/
    FILE *f;
    // filename=argv[1];
    // k=atoi(argv[2]);
    f = fopen(filename, "r");
    if(f==NULL){
        printf("Could not fine the input file...\n");
        return -1;
    }
    D = (matrix)malloc(sizeof(vector));
    int ch;
    n = 0;
    ch = fgetc(f);
    while (ch!=EOF) {
        vector temp = (vector)malloc(sizeof(char));
        //printf("grabbed Line: %c",ch);
        m = 0;
        while (ch!='\n') {
            if(ch=='1' || ch=='0') {
                temp = (vector)realloc(temp,(m+1) * sizeof(char));
                temp[m] = ch-'0';
                m++;
                ch = fgetc(f);
                //printf("%c",ch);


            }
            else{
                printf("Entry %c gave error...\n",ch);
                printf("Entry other than 0 and 1 detected in the truthtable.\n");
                return -1;
            }
        }
        D = (matrix)realloc(D,(n+1) * sizeof(vector));
        D[n] = temp;
        n++;
        ch=fgetc(f);
    }
    fclose(f);

    /* threshold t */
    t_length = 10;
    double t[10] = {0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1};

    b_length = 1;
    double b[1] = {1};

#ifdef DEBUG
    printf("n=%d and m=%d\n",n,m);
    printf("D=\n");
    for(int i=0;i<n;i++){
        printf("  |");
        for(int j=0;j<m;j++){
            printf("%d",D[i][j]);
        }
        printf("|\n");
    }
#endif

    /* Allocate memory for output arguments */

    B = (matrix)malloc(k * sizeof(vector));
    for (i=0; i<k; i++) {
        B[i] = (vector)malloc(m * sizeof(char));
        memset(B[i], 0, m);
    }

    S = (matrix)malloc(n * sizeof(vector));
    for (i=0; i<n; i++) {
        S[i] = (vector)malloc(k * sizeof(char));
        memset(S[i], 0, k);
    }

    bestB = (matrix)malloc(k * sizeof(vector));
    for (i=0; i<k; i++) {
        bestB[i] = (vector)malloc(m * sizeof(char));
        memset(bestB[i], 0, m);
    }

    bestS = (matrix)malloc(n * sizeof(vector));
    for (i=0; i<n; i++) {
        bestS[i] = (vector)malloc(k * sizeof(char));
        memset(bestS[i], 0, k);
    }

    /* make bestError big enough */
    bestError = ULONG_MAX;
    bestThreshold = -1;
    bestBonusCovered = -1;
    bestPenaltyOvercovered = -1;

    /* Iterate over all values of t and bonus */
    for (ti=0; ti<t_length; ti++) {
        /* set threshold */
        opti.threshold = t[ti];
#ifdef DEBUG
        printf("\nTi set to: %f\n",t[ti]);
#endif
        for (bi=0; bi<b_length; bi++) {


            // Divide b to positive and negative bonus, b = bp / bn 
            // bn = modf(b[bi], &bp);
            if (b[bi] >= 0) {bp = b[bi]; bn = 1;}
            else {bp = 1; bn = -1*b[bi];}

            // DEBUG
#ifdef DEBUG
            printf("b[bi] = %f, bn = %f, bp = %f, 1/bn=%f\n", b[bi], bn, bp, 1/bn);
#endif
            opti.bonus_covered = (bp < 1)?1:(int)bp;
            opti.penalty_overcovered = (bn < 1)?1:(int)bn;

            // DEBUG
#ifdef DEBUG
            printf("t = %f, b_covered = %i, b_overcovered = %i\n", opti.threshold,\
		            opti.bonus_covered, opti.penalty_overcovered);
#endif

            if (approximate(D, n, m, B, k, S, &opti) != 1) 
	            printf("Asso failed.\n");

            error = sab(D, S, B, n, m, k, "uniform");

            // DEBUG
#ifdef DEBUG
            printf("bestError = %lu, error = %lu\n", bestError, error);
#endif

            if (error < bestError) {
	            bestError = error;
	            bestThreshold = opti.threshold;
	            bestBonusCovered = opti.bonus_covered;
	            bestPenaltyOvercovered = opti.penalty_overcovered;
	            for (i=0; i<k; i++) {
	                memcpy(bestB[i], B[i], m);
	            }
	            for (i=0; i<n; i++) {
	                memcpy(bestS[i], S[i], k);
	            }
	            // DEBUG
#ifdef DEBUG
	            printf("bestError = %lu was bigger than error = %lu\n", \
		                bestError, error);
#endif

            }

            // Clear B and S
            for (i=0; i<k; i++) memset(B[i], 0, m);
            for (i=0; i<n; i++) memset(S[i], 0, k);

        }
    }

    char w_name[300];
    sprintf(w_name, "%s_w_%d",filename,k);
    f=fopen(w_name,"w");
    for(int i=0;i<n;i++){
        for(int j=0;j<k;j++){
            fprintf(f,"%d ",bestS[i][j]);
        }
        fprintf(f,"\n");
    }
    fclose(f);

    char h_name[300];
    sprintf(h_name, "%s_h_%d",filename,k);
    f=fopen(h_name,"w");
    for(int i=0;i<k;i++){
        for(int j=0;j<m;j++){
            fprintf(f,"%d ",bestB[i][j]);
        }
        fprintf(f,"\n");
    }
    fclose(f);

    char wh_name[300];
    int element;
    sprintf(wh_name, "%s_wh_%d",filename,k);
    f=fopen(wh_name,"w");
    for(int i=0;i<n;i++){
        for(int j=0;j<m;j++){
            element=0;
            for(int l=0;l<k;l++){
                element+=bestS[i][l]*bestB[l][j];
            }
            fprintf(f,"%d ",(element!=0));
        }
        fprintf(f,"\n");
    }
    fclose(f);

    //printf("Finished...\n");
    return 0;
    /* And that's all folks */
}


unsigned long int sab(matrix A, matrix B, matrix C, int n, int m, int k, char* mode) {
    int i, j, l, set;
    unsigned long int error = 0;

    if(strcmp(mode,"uniform")==0){
        for (i=0; i<n; i++) {
            for (j=0; j<m; j++) {
                set = 0;
                for (l=0; l<k; l++) {
	                if (B[i][l] == 1 && C[l][j] == 1) {
	                    if (!A[i][j]) error++; /* A[i,j]=0, (BoC)[i,j] = 1 */
	                    set = 1;
	                    break;
	                }
                }
                if (!set && A[i][j]) error++; /* A[i,j] = 1; (BoC)[i,j] = 0 */
            }
        }
    }
    else if(strcmp(mode,"binary")==0){
        for (i=0; i<n; i++) {
            for (j=0; j<m; j++) {
                set = 0;
                for (l=0; l<k; l++) {
	                if (B[i][l] == 1 && C[l][j] == 1) {
	                    if (!A[i][j]) error=error+pow(2,m-1-j); /* A[i,j]=0, (BoC)[i,j] = 1 */
	                    set = 1;
	                    break;
	                }
                }
                if (!set && A[i][j]) error=error+pow(2,m-1-j); /* A[i,j] = 1; (BoC)[i,j] = 0 */
            }
        }
    }
    else{
        printf("Unsupported mode passed to sab function...\n");
    }
    return error;
}
