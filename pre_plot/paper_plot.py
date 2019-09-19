import regex as re
import numpy as np
import matplotlib.pyplot as plt
import sys



error_list_gs = []
area_list_gs = []
with open('adder20/data') as data:
    line = data.readline().rstrip('\n')
    while line:
        tokens = re.split(',',line)
        err = float(tokens[0])
        area = float(tokens[1])
        error_list_gs.append(err)
        area_list_gs.append(area)
        line = data.readline().rstrip('\n')

error_list_gs = np.array(error_list_gs)
area_list_gs = np.array(area_list_gs)



error_list_gs2 = []
area_list_gs2 = []
with open('max150/data') as data:
    line = data.readline().rstrip('\n')
    while line:
        tokens = re.split(',',line)
        err = float(tokens[0])
        area = float(tokens[1])
        error_list_gs2.append(err)
        area_list_gs2.append(area)
        line = data.readline().rstrip('\n')

error_list_gs2 = np.array(error_list_gs2)
area_list_gs2 = np.array(area_list_gs2)

error_list_gs3 = []
area_list_gs3 = []
with open('ctrl5/data') as data:
    line = data.readline().rstrip('\n')
    while line:
        tokens = re.split(',',line)
        err = float(tokens[0])
        area = float(tokens[1])
        error_list_gs3.append(err)
        area_list_gs3.append(area)
        line = data.readline().rstrip('\n')

error_list_gs3 = np.array(error_list_gs3)
area_list_gs3 = np.array(area_list_gs3)

error_list_gs4 = []
area_list_gs4 = []
with open('bar_gs_2/data') as data:
    line = data.readline().rstrip('\n')
    while line:
        tokens = re.split(',',line)
        err = float(tokens[0])
        area = float(tokens[1])
        error_list_gs4.append(err)
        area_list_gs4.append(area)
        line = data.readline().rstrip('\n')

error_list_gs4 = np.array(error_list_gs4)
area_list_gs4 = np.array(area_list_gs4)


plt.plot(error_list_gs, area_list_gs, color='blue', label='Adder')
plt.plot(error_list_gs2, area_list_gs2, color='green', label='Max')

plt.plot(error_list_gs3, area_list_gs3, color='red', label='Alu control unit')
plt.plot(error_list_gs4, area_list_gs4, color='yellow', label='Barrel shifter')


plt.xlim(0,1.0)
plt.ylim(0,1.1)
plt.ylabel('Normalized Design Area Ratio',fontsize='large')
plt.xlabel('Normalized Hamming Distance Error',fontsize='large')
plt.xticks(np.arange(0,1.0,0.1))
plt.yticks(np.arange(0,1.1,0.1))
plt.grid()
plt.legend()
plt.savefig('paper.png')

