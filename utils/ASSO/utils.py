import numpy as np


def get_matrix(file_path):
    with open(file_path) as f:
        lines = f.readlines()
    mat = [list(i.strip().replace(' ', '')) for i in lines]
    return np.array(mat, dtype=np.uint8)


def write_matrix(mat, file_path):
    with open(file_path, 'w') as f:
        for row in mat:
            for ele in row:
                f.write('{} '.format(ele))
            f.write('\n')


def HD(org, app):
    assert org.shape == app.shape
    return np.sum(org != app)


def weighted_HD(org, app):
    assert org.shape == app.shape
    row, col = org.shape
    weight = np.array([2**e for e in range(col-1, -1, -1)])
    HD = (org != app)
    return np.sum(HD * weight)



# Compute association matrix
def calculate_association(matrix, threshold=0.5):
    row, col = matrix.shape
    ASSO = np.zeros((col, col))
    for i in range(col):
        idx = (matrix[:, i] == 1)
        for j in range(col):
            ASSO[i, j] = sum(matrix[:, j][idx])
        if ASSO[i, i] != 0:
            ASSO[i, :] = ASSO[i, :] / ASSO[i, i]
    
    ASSO[ASSO >= threshold] = 1
    ASSO[ASSO < threshold] = 0

    return ASSO.astype(np.uint8)


def solve_basis(matrix, k, asso, bonus, penalty, binary=False):

    row, col = matrix.shape

    # Mark whether an entry is already covered
    covered = np.zeros((row, col)).astype(np.uint8)

    # Coefficient matrix for bonux or penalty
    coef = np.zeros(matrix.shape)
    coef[matrix == 0] = penalty
    coef[matrix == 1] = bonus

    # If in binary mode, make coef exponential
    if binary:
        coef *= np.array([2**e for e in range(col-1, -1, -1)])

    for i in range(k):

        best_basis = np.zeros((1, col)).astype(np.uint8)
        best_solver = np.zeros((row, 1)).astype(np.uint8)
        best_score = 0

        for b in range(col):
            # Candidate pair of basis and solver
            basis = asso[b, :]
            solver = np.zeros((row, 1)).astype(np.uint8)
            
            # Compute score for each row
            not_covered = 1 - covered
            score_matrix = coef * not_covered * basis
            score_per_row = np.sum(score_matrix, axis=1)

            # Compute solver
            solver[score_per_row > 0] = 1

            # Compute accumulate point
            score = np.sum(score_per_row[score_per_row > 0])

            if score > best_score:
                best_basis = basis
                best_solver = solver
                best_score = score
        
        # Stack matrix B and S
        if i == 0:
            B = best_basis.reshape((1, -1))
            S = best_solver.copy()
        else:
            B = np.vstack((B, best_basis))
            S = np.hstack((S, best_solver))
        
        # Update covered matrix
        covered = np.matmul(S, B)
        covered[covered > 1] = 1
    
    return S, B, covered




