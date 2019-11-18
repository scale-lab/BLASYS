import numpy as np

def optimization(err_list, area_list, threshold):
    gradient = np.zeros(len(err_list))

    for (idx,(area, err)) in enumerate(zip(area_list, err_list)):
        if err > threshold:
            gradient[idx] = np.inf
        elif err == 0:
            gradient[idx] = -np.inf
        else:
            gradient[idx] = (area - 1) / err

    rank1 = np.argsort(area_list, kind='stable')
    rank2 = np.argsort(gradient[rank1], kind='stable')
    rank3 = rank1[rank2]

    return rank3

def least_error_opt(err_list, area_list, threshold):
    rank1 = np.argsort(area_list, kind='stable')
    rank2 = np.argsort(err_list[rank1], kind='stable')
    rank3 = rank1[rank2]

    return rank3
