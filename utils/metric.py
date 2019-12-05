import numpy as np

def distance(original_path, approximate_path, use_weight=False):
    with open(original_path, 'r') as fo:
        org_line_list = fo.readlines()
    with open(approximate_path, 'r') as fa:
        app_line_list = fa.readlines()
    
    org = [list(filter(lambda a: a != ' ', list(i[:-1]))) for i in org_line_list]
    app = [list(filter(lambda a: a != ' ', list(i[:-1]))) for i in app_line_list]

    if len(org_line_list) != len(app_line_list):
        print('ERROR! sizes of input files are not equal! Aborting...')
        return -1

    if use_weight:
        return Weighted_HD(org, app)
    else:
        return Hamming_Distance(org, app)



def Hamming_Distance(org_line_list, app_line_list):
    org = np.array(org_line_list)
    app = np.array(app_line_list)
    total = org.size
    HD = np.sum(org != app)
    return HD/total

def Weighted_HD(org_line_list, app_line_list):
    err = []
    num_vec = len(org_line_list)
    num_pos = len(org_line_list[0])

    #weight = np.array([2**i for i in range(num_pos)][::-1])
    #org = np.array(org_line_list, dtype=int)
    #app = np.array(app_line_list, dtype=int)
    
    #diff = org != app
    #print(np.sum(org * weight))

    #return np.sum(diff * weight) / (np.sum(weight) * num_vec)
    #print(np.sum((org != app) * weight,axis=1))
    err = []
    #org_list = []
    for i in range(num_vec):
        orgnum = int(''.join(org_line_list[i]), 2)
        appnum = int(''.join(app_line_list[i]), 2)
        
        if orgnum != 0:
            err.append( np.abs(orgnum - appnum) / orgnum )
        #org_list.append(orgnum)
        else:
            err.append(0)
        # err.append(np.sum(weight * (org[i] != app[i])) / np.sum(weight*org[i]) )
        # err.append(np.abs(np.sum(weight * org[i]) - np.sum(weight * app[i])))

    return np.mean(err)

    #return np.sum((org != app) * weight) / np.sum(org* weight)


