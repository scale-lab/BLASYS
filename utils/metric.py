import numpy as np

def Hamming_Distance(org_line_list, app_line_list):
    #HD=0
    #total=0
    #for n in range(len(org_line_list)):
    #    l1=org_line_list[n]
    #    l2=app_line_list[n]
    #    for k in range(len(l1)):
    #        total+=1
    #        if l1[k] != l2[k]:
    #            HD+=1
    org = np.array(org_line_list)
    app = np.array(app_line_list)
    total = org.size
    HD = np.sum(org != app)
    return HD/total

def Weighted_HD(org_line_list, app_line_list):
    err = []
    num_vec = len(org_line_list)
    num_pos = len(org_line_list[0])

    weight = np.array([2**i for i in range(num_pos)][::-1])
    org = np.array(org_line_list)
    app = np.array(app_line_list)
    
    diff = org != app

    return np.sum(diff * weight) / (np.sum(weight) * num_vec)


