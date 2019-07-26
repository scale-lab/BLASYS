import regex as re
import sys
import random
import os
import numpy as np
import subprocess
import shutil
import yaml
from utils import assess_HD, gen_truth, create_wh, synth_design, approximate


def evaluate_design(k_stream, list_num_input, list_num_output, config, approx_area):

    print('Evaluating Design ', k_stream)

    num_part = len(k_stream)
    area = 0

    tmp_verilog = os.path.join(config['output_dir'], 'temp.v')
    toplevel_file = os.path.join(config['output_dir'], 'partition', config['toplevel'] + '.v')
    os.system('cat ' + toplevel_file + ' > ' + tmp_verilog)

    for i in range(num_part):

        approx_degree = k_stream[i]

        if approx_degree == list_num_output[i]:
            part_verilog = os.path.join(config['output_dir'], 'partition', config['toplevel'] + '_' + str(i) + '.v')
            os.system('cat ' + part_verilog + ' >> ' + tmp_verilog)
            area += approx_area[i][approx_degree]
            continue
        
        part_verilog = os.path.join(config['output_dir'], config['toplevel'] + '_' + str(i), config['toplevel'] + '_' + str(i) + '_approx_k=' + str(approx_degree) + '.v')
        if approx_area[i][approx_degree] != 0:
            os.system('cat ' + part_verilog + ' >> ' + tmp_verilog)
            area += approx_area[i][approx_degree]
        else:
            print('Approximating part ' + str(i) + ' to degree ' + str(approx_degree))

            directory = os.path.join(config['output_dir'], config['toplevel'] + '_' + str(i), config['toplevel'] + '_' + str(i))
            approximate(directory, approx_degree, list_num_input[i], list_num_output[i], config['liberty_file'], config['toplevel'] + '_' + str(i))
            os.system('cat ' + part_verilog + ' >> ' + tmp_verilog)
            part_area = synth_design(part_verilog, part_verilog[:-2]+'_syn', config['liberty_file'], True)
            approx_area[i][approx_degree] = part_area
            area += part_area

    os.system('iverilog -o tmp.iv ' + tmp_verilog + ' ' + config['testbench'])
    truth_dir = os.path.join(config['output_dir'], 'tmp.truth')
    os.system('vvp tmp.iv > ' + truth_dir)
    os.system('rm tmp.iv')

    ground_truth = os.path.join(config['output_dir'], config['toplevel'] + '.truth')

    t, h, f = assess_HD(ground_truth, truth_dir)
    print('Simulation error: ' + str(f) + '\tCircuit area: ' + str(area))
    return f, area



def evaluate_iter(curr_k_stream, list_num_input, list_num_output, config, approx_area):
    
    k_lists = []

    for i in range(len(curr_k_stream)):
        new_k_stream = list(curr_k_stream)
        new_k_stream[i] = new_k_stream[i] - 1
        if new_k_stream[i] != 0:
            k_lists.append(new_k_stream)
    
    if len(k_lists) == 0:
        return False

    num_list = len(k_lists)
    err_list = []
    area_list = []

    for i in range(num_list):
        # Evaluate each list
        k_stream = k_lists[i]
        err, area = evaluate_design(k_stream, list_num_input, list_num_output, config, approx_area)
        err_list.append(err)
        area_list.append(area)

    if np.min(err_list) > config['threshold']:
        return False

    np_area = np.array(area_list)
    order = np.argsort(np_area)

    for i in order:
        if err_list[i] > config['threshold']:
            continue
        return k_lists[i]



def print_usage():
    print('BLASYS -- Approximate Logic Synthesis Using Boolean Matrix Factorization')
    print('The usage is:')
    print('    python3 run_blasys_flow.py [PATH_TO_PARAMS.YML]')


def print_banner():
    print('/----------------------------------------------------------------------------\\')
    print('|                                                                            |')
    print('|  BLASYS -- Approximate Logic Synthesis Using Boolean Matrix Factorization  |')
    print('|  Version: 0.1.0                                                            |')
    print('|                                                                            |')
    print('|  Copyright (C) 2019  SCALE Lab, Brown University                           |')
    print('|                                                                            |')
    print('|  Permission to use, copy, modify, and/or distribute this software for any  |')
    print('|  purpose with or without fee is hereby granted, provided that the above    |')
    print('|  copyright notice and this permission notice appear in all copies.         |')
    print('|                                                                            |')
    print('|  THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES  |')
    print('|  WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF          |')
    print('|  MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR   |')
    print('|  ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES    |')
    print('|  WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN     |')
    print('|  ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF   |')
    print('|  OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.            |')
    print('|                                                                            |')
    print('\\----------------------------------------------------------------------------/')



######################
#        MAIN        #
######################

if len(sys.argv) == 2:
    arg = sys.argv[1]
    if arg == '--version' or arg == '-v':
        print('BLASYS Approximate Logic Synthesis Framework')
        print('Version 0.2.0')
        sys.exit()
    elif arg == '--help' or arg == '-h':
        print_usage()
        sys.exit()
    elif arg[-4:] == '.yml':
        yaml_file = arg
    else:
        print_usage()
        sys.exit()
else:
    print_usage()
    sys.exit()

print_banner()

with open(yaml_file, 'r') as config_file:
    config = yaml.safe_load(config_file)

# Create temporary output directory
output_dir_path = config['output_dir']
if os.path.isdir(output_dir_path):
    shutil.rmtree(output_dir_path)
os.mkdir(output_dir_path)

# Parse information from yaml file
input_file = config['input_file']
testbench = config['testbench']
toplevel = config['toplevel']
err_thresh = config['err_thresh']
lsoracle = config['lsoracle_path']
yosys = config['yosys_path']
iverilog = config['iverilog_path']
vvp = config['vvp_path']
library = config['liberty_file']
num_parts = config['partition_count']

# Evaluate input circuit
print('Simulating truth table on input design...')
os.system(iverilog + ' -o '+ toplevel + '.iv ' + input_file + ' ' + testbench )
output_truth = os.path.join(output_dir_path, toplevel+'.truth')
os.system(vvp + ' ' + toplevel + '.iv > ' + output_truth)
os.system('rm ' + toplevel + '.iv')
print('Synthesizing input design...')
output_synth = os.path.join(output_dir_path, toplevel+'_syn')
input_area = synth_design(input_file, output_synth, library, False)
print('Original design area', str(input_area))

# Partitioning circuit
part_dir = os.path.join(output_dir_path, 'partition')
os.system('cp ' + input_file + ' ./')
lsoracle_command = 'read_verilog ' + os.path.basename(input_file) + '; ' \
        'partitioning ' + str(num_parts) + '; ' \
        'get_all_partitions ' + part_dir
log_partition = os.path.join(output_dir_path, 'lsoracle.log')
with open(log_partition, 'w') as file_handler:
    file_handler.write(lsoracle_command)
    subprocess.call([lsoracle, '-c', lsoracle_command], stderr=file_handler, stdout=file_handler)

# Generate truth table for each partitions
approx_area = []
list_part_output_dir = []
list_num_input = []
list_num_output = []
for i in range(num_parts):
    modulename = toplevel + '_' + str(i)

    # Create testbench for partition
    print('Create testbench for partition '+str(i))
    file_path = os.path.join(part_dir, modulename)
    n, m = gen_truth(file_path, modulename)
    list_num_input.append( n )
    list_num_output.append( m )

    # Generate truthtable
    print('Generate truth table for partition '+str(i))
    part_output_dir = os.path.join(output_dir_path, modulename)
    list_part_output_dir.append(part_output_dir)
    os.mkdir(part_output_dir)
    os.system(iverilog + ' -o ' + file_path + '.iv ' + file_path + '.v ' + file_path + '_tb.v')
    truth_dir = os.path.join(part_output_dir, modulename + '.truth')
    os.system(vvp + ' ' + file_path + '.iv > ' + truth_dir)

    # Evaluate partition area
    print('Evaluate partition area ' + str(i))
    part_synth = os.path.join(part_output_dir, modulename + '_syn')
    part_area = synth_design(file_path + '.v', part_synth, library, True)
    print('Partition area ' + str(part_area))
    approx_area.append([0] * m + [part_area])

print('==================== Starting Approximation by Greedy Search  ====================')


# test with 2
# directory = os.path.join(list_part_output_dir[1], 'adder_1')
# approximate(directory, list_num_output[1] - 1, list_num_input[1], list_num_output[1], library, toplevel + '_1')

# f = evaluate_design([4]*len(list_num_output), list_num_input,list_num_output,config,approx_area)
# print('error ' + str(f))
count_iter = 1
curr_stream = []

while True:
    if count_iter == 1:
        curr_stream = list_num_output

    print('############### Current k_stream: ', curr_stream)
    print('--------------- Iteration ' + str(count_iter) + ' ---------------')

    tmp = evaluate_iter(curr_stream, list_num_input, list_num_output, config, approx_area )
     
    if tmp == False:
        break

    curr_stream = tmp



    count_iter += 1






#k=int(sys.argv[2])
# generate the input side of the truth of the module	
#print('Creating truth table testbench...')
#n, m =gen_truth(sys.argv[1])
# simulate the module to generate the output side of the truth table
#print('Simulating truth table on input design...')
#os.system('iverilog -o '+ sys.argv[1] + '.iv ' + sys.argv[1]+ '.v '+sys.argv[1] + '_tb.v')
#os.system('vvp '+sys.argv[1]+'.iv >'+sys.argv[1]+'.truth')
#print('Synthesizing input design...')
#area = synth_design(sys.argv[1]+'.v', sys.argv[1]+'_syn', sys.argv[2])
#print('Original design area', str(area))
# run BMF on the output side of the truth table
#for k in range(m-1, 1, -1):
#    print('Executing BMF with k =', str(k), '...')
#    os.system('../asso '+sys.argv[1]+'.truth '+str(k))
#    W=np.loadtxt(sys.argv[1]+'.truth_w_'+str(k), dtype=int)
#    H=np.loadtxt(sys.argv[1]+'.truth_h_'+str(k), dtype=int)
#    print('Writing approximate design...')
#    create_wh(n, m, k, W, H, sys.argv[1])
#    print('Simulating truth table on approximate design...')
#    os.system('iverilog -o '+ sys.argv[1]+'_approx_k='+str(k)+'.iv ' + sys.argv[1]+'_approx_k='+str(k)+'.v '+ sys.argv[1] + '_tb.v')
#    os.system('vvp '+sys.argv[1]+'_approx_k='+str(k)+'.iv > ' + sys.argv[1]+'_approx_k='+str(k)+'.truth')
#    t, h, f = assess_HD(sys.argv[1]+'.truth', sys.argv[1]+'_approx_k='+str(k)+'.truth')
#    print('Synthesizing approximate design...')
#    area_ap = synth_design(sys.argv[1]+'_approx_k='+str(k)+'.v', sys.argv[1]+'_approx_k='+str(k)+'_syn', sys.argv[2])
#    print('Metrics HD - total bits:'+str(t)+' flipped: '+str(h)+' percent: '+str(100*f)+'%'+ ' Area: '+str(area_ap)+ ' percent: '+str(100*(area-area_ap)/area))
