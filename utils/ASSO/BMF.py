import numpy as np
import os
import shutil
from .utils import *

def BMF(truthtable, k, binary = False):
    # Read in input truthtable
    input_truth = get_matrix(truthtable)
    row, col = input_truth.shape
    
    # Output path
    B_path = truthtable + '_h_' + str(k)
    S_path = truthtable + '_w_' + str(k)
    mult_path = truthtable + '_wh_' + str(k)

    # Best pair
    best_B = -1
    best_S = -1
    best_result = -1
    best_score = float('inf')

    threshold_list = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

    for threshold in threshold_list:
        association = calculate_association(input_truth, threshold)
        S, B, result = solve_basis(input_truth, k, association, 1, -1, binary)
        if binary:
            score = weighted_HD(input_truth, result)
        else:
            score = HD(input_truth, result)

        if score < best_score:
            best_B = B
            best_S = S
            best_result = result
            best_score = score
    
    # Enumerate possible columns
    column_list = []
    multi_list = []
    for i in range(2**k):
        binary_str = '{0:0>{1}}'.format(bin(i)[2:], k)
        column = np.array(list(binary_str)).astype(np.uint8)
        column_list.append(column)
        prod = np.matmul(best_S, column)
        prod = prod % 2
        multi_list.append(prod)
    
    # Brute force best column in B
    for i in range(col):
        ground_truth = input_truth[:, i]
        best_similar = 0
        best_idx = -1
        for j in range(2**k):
            similar = sum(multi_list[j] == ground_truth)
            if similar > best_similar:
                best_idx = j
                best_similar = similar
        best_B[:, i] = column_list[best_idx]

    
    write_matrix(best_B, B_path)
    write_matrix(best_S, S_path)
    new_best_result = np.matmul(best_S, best_B)
    new_best_result = new_best_result % 2
    write_matrix(new_best_result, mult_path)