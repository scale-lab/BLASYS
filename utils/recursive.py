from .create_tb import create_testbench
from .greedyWorker import GreedyWorker, optimization
from .banner import print_banner
from .utils import assess_HD, synth_design, number_of_cell
import os
import argparse
import multiprocessing as mp
import numpy as np
import subprocess
import yaml
import sys
import regex as re
import shutil


def recursive_partitioning(inp_file, out_dir, modulename, path):
    '''
    Partition input circuit recursively until # of cells less than 2000
    '''

    modulenames = []

    print('Partitioning input circuit...')
    part_dir = os.path.join(out_dir, 'partition')
    num_parts = number_of_cell(inp_file, path['yosys']) // 1500 + 1
    lsoracle_command = 'read_verilog ' + inp_file + '; ' \
            'partitioning ' + str(num_parts) + ' -c '+ path['part_config'] +'; ' \
            'get_all_partitions ' + part_dir
    
    log_partition = os.path.join(out_dir, 'lsoracle.log')
    with open(log_partition, 'w') as file_handler:
        subprocess.call([path['lsoracle'], '-c', lsoracle_command], stderr=file_handler, stdout=file_handler)

    partitioned = [modulename + '_' + str(i) for i in range(num_parts)]

    toplevel = os.path.join(part_dir, modulename+'.v')

    while len(partitioned) > 0:
        mod = partitioned.pop()
        mod_path = os.path.join(part_dir, mod+'.v')
        if not os.path.exists(mod_path):
            continue

        #inp, out = inpout(mod_path)
        num_cell = number_of_cell(mod_path, path['yosys'])
        if num_cell > 2000:
            num_part = num_cell // 2000 + 1
            lsoracle_command = 'read_verilog ' + mod_path + '; ' \
                    'partitioning ' + str(num_part) + ' -c '+ path['part_config'] +'; ' \
                    'get_all_partitions ' + part_dir
            with open(log_partition, 'a') as file_handler:
                subprocess.call([path['lsoracle'], '-c', lsoracle_command], stderr=file_handler, stdout=file_handler)
            partitioned.extend([mod + '_' + str(i) for i in range(num_parts)])
            
            with open(toplevel, 'a') as top:
                subprocess.call(['cat', mod_path], stdout=top)

            os.remove(mod_path)
        else:
            modulenames.append(mod)

    print('Number of partitions', len(modulenames))

    return modulenames, toplevel


def evaluate_design(input_list, testbench, ground_truth, output, filename, path, liberty):
    '''
    Return estimated area and HD error of approximated circuit
    '''

    truth_dir = os.path.join(output, 'truthtable', filename+'.truth')
    subprocess.call([path['iverilog'], '-o', truth_dir[:-5]+'iv', testbench] + input_list)
    with open(truth_dir, 'w') as f:
        subprocess.call([path['vvp'], truth_dir[:-5]+'iv'], stdout=f)
    os.remove(truth_dir[:-5] + 'iv')
    
    output_syn = os.path.join(output, 'approx_design', filename)
    area  = synth_design(' '.join(input_list), output_syn, liberty, path['script'], path['yosys'])

    f = assess_HD(ground_truth, truth_dir)
    print('Simulation error: ' + str(f) + '\tCircuit area: ' + str(area))
    return f, area



######################
#        MAIN        #
######################
def main():
    app_path = os.path.dirname(os.path.realpath(__file__))
    
    # Parse command-line args
    parser = argparse.ArgumentParser(description='BLASYS -- Approximate Logic Synthesis Using Boolean Matrix Factorization')
    parser.add_argument('-i', help='Input verilog file', required=True, dest='input')
    parser.add_argument('-tb', '--testbench', help='Testbench verilog file', required=True, dest='testbench')
    parser.add_argument('-o', help='Output directory', default='output', dest='output')
    parser.add_argument('-ts', '--threshold', help='Threshold on error', default=0.9, type=float, dest='threshold')
    parser.add_argument('-lib', '--liberty', help='Liberty file name', required=True, dest='liberty')
    parser.add_argument('-ss', '--stepsize', help='Step size in optimization process', default=1, type=int, dest='stepsize')
    parser.add_argument('--parallel', help='Run the flow in parallel mode if specified', dest='parallel', action='store_true')

    args = parser.parse_args()

    print_banner()


    # Get modulename
    with open(args.input) as file:
        line = file.readline()
        while line:
            tokens = re.split('[ (]', line)
            for i in range(len(tokens)):
                if tokens[i] == 'module':
                    modulename = tokens[i+1]
                    break
            line = file.readline()

    # Create output dir
    print('Generate file directory ...')
    if os.path.isdir(args.output):
        shutil.rmtree(args.output)
    os.mkdir(args.output)
    os.mkdir(os.path.join(args.output, 'approx_design'))
    os.mkdir(os.path.join(args.output, 'truthtable'))
    os.mkdir(os.path.join(args.output, 'result'))
    
    # Load path to yosys, lsoracle, iverilog, vvp, abc
    with open(os.path.join(app_path, 'config', 'params.yml'), 'r') as config_file:
        config = yaml.safe_load(config_file)
    
    config['part_config'] = os.path.join(app_path, 'config', 'test.ini')
    config['script'] = os.path.join(args.output, 'abc.script')
    print(config['script'])
    with open(config['script'], 'w') as f:
        f.write('strash;fraig;refactor;rewrite -z;scorr;map')   

    # Generate ground truth table
    print('Generate truthtable for input verilog ...')
    ground_truth = os.path.join(args.output, modulename+'.truth')
    subprocess.call([config['iverilog'], '-o', ground_truth[:-5]+'iv', args.input, args.testbench])
    with open(ground_truth, 'w') as f:
        subprocess.call([config['vvp'], ground_truth[:-5]+'iv'], stdout=f)
    os.remove(ground_truth[:-5] + 'iv')
    
    # Get original chip area
    print('Synthesizing input design with original partitions...')
    output_synth = os.path.join(args.output, modulename)
    input_area = synth_design(args.input, output_synth, args.liberty, config['script'], config['yosys'])
    print('Original design area ', str(input_area))
    initial_area = input_area
    with open(os.path.join(args.output, 'result', 'result.txt'), 'w') as f:
        f.write('Original chip area {:.2f}\n'.format(initial_area))
        f.flush()

    # Partition into subcircuit with < 2000 cells
    modulenames, toplevel = recursive_partitioning(args.input, args.output, modulename, config)

    print('Generate testbench for each partition ...')
    for i in modulenames:
        module_file = os.path.join(args.output, 'partition', i)
        with open(module_file + '_tb.v', 'w') as f:
            create_testbench(module_file+'.v', 5000, f)

    file_list = [os.path.join(args.output, 'partition', i+'.v') for i in modulenames]
    tb_list = [os.path.join(args.output, 'partition', i+'_tb.v') for i in modulenames]
    output_list = [os.path.join(args.output, i) for i in modulenames]

    worker_list = []

    # Initialize greedyWorker for each subcircuit
    for inp, tb, out in zip(file_list, tb_list, output_list):
        worker = GreedyWorker(inp, tb, args.liberty, config)
        worker.create_output_dir(out)
        worker.evaluate_initial()
        worker.recursive_partitioning()
        worker_list.append(worker)
    
    err_summary = [0.0]
    area_summary = [initial_area]
    curr_iter_list = [-1 for i in modulenames]
    max_iter_list = [-1 for i in modulenames]
    curr_file_list = file_list
    it = 0

    while 1:
        err_list = []
        area_list = []

        candidate_list = []
        candidate_iter_num = []

        changed = {}
        count = 0

        for i,(w,d) in enumerate(zip(worker_list, output_list)):
            if max(w.curr_stream) == 1:
                curr_iter_list[i] = -1
            else:
                i_list = curr_iter_list.copy()
                i_list[i] += 1
                if i_list[i] > max_iter_list[i]:
                    w.next_iter(args.parallel, args.stepsize, least_error=True)
                    max_iter_list[i] += 1

                objective = os.path.join(d, 'approx_design', 'iter{}.v'.format(i_list[i]))
                k_list = curr_file_list.copy()
                k_list[i] = objective
                candidate_iter_num.append(i_list)
                candidate_list.append(k_list)
                changed[count] = i
                count += 1
        

        if len(candidate_list) == 0:
            a = np.array(area_summary)
            i = np.argmin(a)
            source_file = os.path.join(args.output, 'approx_design', 'iter{}.v'.format(i))
            target_file = os.path.join(args.output, 'result', '{}_{}metric.v'.format(modulename, round(100*args.threshold)))
            shutil.copyfile(source_file, target_file)
            with open(os.path.join(args.output, 'result', 'result.txt'), 'a') as f:
                f.write('{}% error metric chip area {:.2f}\n'.format('REST', area_summary[i]))

            sys.exit(0)

        if args.parallel:
            pool = mp.Pool(mp.cpu_count())
            results = [pool.apply_async(evaluate_design,args=(candidate_list[i] + [toplevel], args.testbench, ground_truth, args.output, 'iter'+str(it)+'design'+str(i), config, args.liberty )) for i in range(len(candidate_list))]
            pool.close()
            pool.join()
            for result in results:
                err_list.append(result.get()[0])
                area_list.append(result.get()[1])
        else:
            for i,l in enumerate(candidate_list):
                err, area = evaluate_design(l+[toplevel], args.testbench, ground_truth, args.output, 'iter'+str(it)+'design'+str(i), config, args.liberty)
                err_list.append(err)
                area_list.append(area)

        rank = optimization(np.array(err_list), np.array(area_list) / initial_area , args.threshold + 0.01)
        idx = rank[0]
        err_summary.append(err_list[idx])
        area_summary.append(area_list[idx])
        shutil.copyfile(os.path.join(args.output, 'approx_design', 'iter{}design{}_syn.v'.format(it, idx)), os.path.join(args.output, 'approx_design', 'iter{}.v'.format(it)))

        curr_file_list = candidate_list[idx]
        curr_iter_list = candidate_iter_num[idx]

        for i,e in enumerate(err_list):
            if e <= err_summary[-2] and area_list[i] <= area_summary[-2]:
                curr_file_list[changed[i]] = candidate_list[i][changed[i]]
                curr_iter_list[changed[i]] = candidate_iter_num[i][changed[i]]

        with open(os.path.join(args.output, 'data.csv'), 'a') as data:
            data.write('{:.6f},{:.6f}\n'.format(err_list[idx], area_list[idx]))
            data.flush()


        if err_list[idx] >= args.threshold + 0.01:
            a = np.array(area_summary)
            e = np.array(err_summary)
            a[e > args.threshold] = np.inf
            i = np.argmin(a)
            source_file = os.path.join(args.output, 'approx_design', 'iter{}.v'.format(i))
            target_file = os.path.join(args.output, 'result', '{}_{}metric.v'.format(modulename, round(100*args.threshold)))
            shutil.copyfile(source_file, target_file)
            with open(os.path.join(args.output, 'result', 'result.txt'), 'a') as f:
                f.write('{:.1f}% error metric chip area {:.2f}\n'.format(100*args.threshold, area_summary[i]))
                f.flush()

            sys.exit(0)

        it += 1



if __name__ == '__main__':
    main()
