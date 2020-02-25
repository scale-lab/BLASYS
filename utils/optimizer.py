import numpy as np

def optimization(err_list, area_list, initial, prev_err, prev_area, threshold):
    gradient = np.zeros(len(err_list))

    for (idx,(area, err)) in enumerate(zip(area_list, err_list)):
        if err > threshold:
            gradient[idx] = np.inf
        elif err == 0:
            gradient[idx] = -np.inf
        else:
            gradient[idx] = (area/initial - 1) / err

    rank1 = np.argsort(area_list, kind='stable')
    rank2 = np.argsort(gradient[rank1], kind='stable')
    rank3 = rank1[rank2]

    return rank3

def nearest_neighbor(err_list, area_list, prev_err, prev_area):
    dist = np.sqrt((err_list - prev_err) ** 2 + (area_list - prev_area) ** 2)
    return dist.argmin()

def least_error_opt(err_list, area_list, threshold):
    rank1 = np.argsort(area_list, kind='stable')
    rank2 = np.argsort(err_list[rank1], kind='stable')
    rank3 = rank1[rank2]

    return rank3

def optimization_1(err_list, area_list, initial, prev_err, prev_area, threshold):
    gradient = np.zeros(len(err_list))    

    for diff in [0.0001, 0.0002, 0.0004, 0.0008, 0.001, 0.005, 0.01, float('inf')]:
        if err_list.min() <= prev_err + diff:
            for (idx,(area, err)) in enumerate(zip(area_list, err_list)):
                if err > prev_err + diff or err > threshold:
                    gradient[idx] = np.inf
                elif area > prev_area:
                    #gradient[idx] = np.sqrt((area-prev_area)**2 + (err-prev_err)**2)
                    gradient[idx] = (area/prev_area - 1) ** 2 / (err - prev_err)
                elif err <= prev_err:
                    gradient[idx] = -np.inf
                #elif err <= prev_err + 0.02:
                else:
                    gradient[idx] = (area/prev_area - 1) / ((err - prev_err) ** 2)


            rank1 = np.argsort(area_list, kind='stable')
            rank2 = np.argsort(gradient[rank1], kind='stable')
            rank3 = rank1[rank2]
            
            return rank3
    #elif err_list.min() <= prev_err + 0.02:
    #    for (idx,(area, err)) in enumerate(zip(area_list, err_list)):
    #        if err > prev_err + 0.02 or err > threshold:
    #            gradient[idx] = np.inf
    #        elif area > prev_area:
    #            gradient[idx] = np.sqrt((area-prev_area)**2 + (err-prev_err)**2)
    #        else:
    #            gradient[idx] = (area/prev_area - 1) / ((err - prev_err) ** 2)

    #    rank1 = np.argsort(area_list, kind='stable')
    #    rank2 = np.argsort(gradient[rank1], kind='stable')
    #    rank3 = rank1[rank2]
        
    #    return rank3

    #else:
    #    for (idx,(area, err)) in enumerate(zip(area_list, err_list)):
    #        if err > threshold:
    #            gradient[idx] = np.inf
    #        elif area > prev_area:
    #            gradient[idx] = np.sqrt((area-prev_area)**2 + (err-prev_err)**2)
    #        else:
    #            gradient[idx] = (area/prev_area - 1) / ((err - prev_err) ** 2)

    #    rank1 = np.argsort(area_list, kind='stable')
    #    rank2 = np.argsort(gradient[rank1], kind='stable')
    #    rank3 = rank1[rank2]
        
    #    return rank3

