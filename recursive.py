from utils.create_tb import create_testbench
from utils.greedyWorker import GreedyWorker, print_banner, optimization
from utils.utils import assess_HD, synth_design
import os
import argparse
import multiprocessing as mp
import numpy as np
import subprocess
import yaml
import sys
import regex as re
import shutil

def number_of_cell(input_file, yosys):
    yosys_command = 'read_verilog ' + input_file + '; ' \
            + 'synth -flatten; opt; opt_clean -purge; techmap; stat;\n'

    num_cell = 0
    output_file = input_file[:-2] + '_syn.log'
    line=subprocess.call(yosys+" -p \'"+ yosys_command+"\' > "+ output_file, shell=True)
    with open(output_file, 'r') as file_handle:
        for line in file_handle:
            if 'Number of cells:' in line:
                num_cell = line.split()[-1]
                break
    os.remove(output_file)
    return int(num_cell)

def recursive_partitioning(inp_file, out_dir, modulename, path):
    modulenames = []
    suggest_part = []

    print('Partitioning input circuit...')
    part_dir = os.path.join(out_dir, 'partition')
    num_parts = number_of_cell(inp_file, path['yosys']) // 2000 + 1
    lsoracle_command = 'read_verilog ' + inp_file + '; ' \
            'partitioning ' + str(num_parts) + '; ' \
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
                    'partitioning ' + str(num_part) + '; ' \
                    'get_all_partitions ' + part_dir
            with open(log_partition, 'a') as file_handler:
                subprocess.call([path['lsoracle'], '-c', lsoracle_command], stderr=file_handler, stdout=file_handler)
            partitioned.extend([mod + '_' + str(i) for i in range(num_parts)])
            
            with open(toplevel, 'a') as top:
                subprocess.call(['cat', mod_path], stdout=top)

            os.remove(mod_path)
        else:
            modulenames.append(mod)
            suggest_part.append(min(30, num_cell // 20 + 1))

    print('Number of partitions', len(modulenames))

    return modulenames, suggest_part, toplevel


def evaluate_design(verilog_list, toplevel, testbench, ground_truth, output, filename, path):

    input_list = verilog_list + [toplevel]

    truth_dir = os.path.join(output, 'truthtable', filename+'.truth')
    subprocess.call([path['iverilog'], '-o', truth_dir[:-5]+'iv', testbench] + input_list)
    with open(truth_dir, 'w') as f:
        subprocess.call([path['vvp'], truth_dir[:-5]+'iv'], stdout=f)
    os.remove(truth_dir[:-5] + 'iv')
    
    output_syn = os.path.join(output, 'approx_design', filename)
    area  = synth_design(' '.join(input_list), output_syn, path['liberty'], path['script'], path['yosys'])

    t, h, f = assess_HD(ground_truth, truth_dir)
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
    parser.add_argument('-tb', help='Testbench verilog file', required=True, dest='testbench')
    parser.add_argument('-n', help='Number of partitions', required=True, type=int, dest='npart')
    parser.add_argument('-o', help='Output directory', default='output', dest='output')
    parser.add_argument('-ts', help='Threshold on error', default=0.9, type=float, dest='threshold')
    parser.add_argument('-lib', help='Liberty file name', default=os.path.join(app_path, 'tsmc65.lib'), dest='liberty')
    parser.add_argument('--parallel', help='Run the flow in parallel mode if specified', dest='parallel', action='store_true')

    args = parser.parse_args()

    print_banner()

    # Load path to yosys, lsoracle, iverilog, vvp, abc
    with open(os.path.join(app_path, 'config', 'params.yml'), 'r') as config_file:
        config = yaml.safe_load(config_file)

    # Create output dir
    print('Generate file directory ...')
    if os.path.isdir(args.output):
        shutil.rmtree(args.output)
    os.mkdir(args.output)
    os.mkdir(os.path.join(args.output, 'approx_design'))
    os.mkdir(os.path.join(args.output, 'truthtable'))
    os.mkdir(os.path.join(args.output, 'result'))
    
    config['part_config'] = os.path.join(app_path, 'config', 'test.ini')
    config['asso'] = os.path.join(app_path, 'asso', 'asso.so')
    # Append liberty and script
    config['liberty'] = args.liberty
    config['script'] = os.path.join(args.output, 'abc.script')
    with open(config['script'], 'w') as f:
        f.write('strash;fraig;refactor;rewrite -z;scorr;map')

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

    # Generate ground truth table
    print('Generate truthtable for input verilog ...')
    ground_truth = os.path.join(args.output, modulename+'.truth')
    subprocess.call([config['iverilog'], '-o', ground_truth[:-5]+'iv', args.input, args.testbench])
    with open(ground_truth, 'w') as f:
        subprocess.call([config['vvp'], ground_truth[:-5]+'iv'], stdout=f)
    os.remove(ground_truth[:-5] + 'iv')
    
    print('Synthesizing input design with original partitions...')
    output_synth = os.path.join(args.output, modulename)
    input_area = synth_design(args.input, output_synth, args.liberty, config['script'], config['yosys'])
    print('Original design area ', str(input_area))
    initial_area = input_area

    modulenames, suggest_part, toplevel = recursive_partitioning(args.input, args.output, modulename, config)

    for i in modulenames:
        module_file = os.path.join(args.output, 'partition', i)
        with open(module_file + '_tb.v', 'w') as f:
            create_testbench(module_file+'.v', i, 5000, f)

    file_list = [os.path.join(args.output, 'partition', i+'.v') for i in modulenames]
    tb_list = [os.path.join(args.output, 'partition', i+'_tb.v') for i in modulenames]
    output_list = [os.path.join(args.output, i) for i in modulenames]

    worker_list = []

    for inp, tb, out, p in zip(file_list, tb_list, output_list, suggest_part):
        worker = GreedyWorker(inp, tb, args.liberty, config)
        worker.create_output_dir(out)
        worker.evaluate_initial()
        worker.recursive_partitioning(p)
        worker_list.append(worker)
    
    err_summary = []
    area_summary = []
    curr_iter_list = [-1 for i in modulenames]
    max_iter_list = [-1 for i in modulenames]
    curr_file_list = file_list.copy()
    it = 0


    m5 = True
    m10 = True
    m15 = True
    m20 = True



    while 1:
        err_list = []
        area_list = []

        candidate_list = []
        candidate_iter_num = []

        for i,(w,d) in enumerate(zip(worker_list, output_list)):
            if max(w.curr_stream) == 1:
                curr_iter_list[i] = -1
            else:
                i_list = curr_iter_list.copy()
                i_list[i] += 1
                candidate_iter_num.append(i_list)
                if i_list[i] > max_iter_list[i]:
                    w.next_iter(3, args.parallel)
                    max_iter_list[i] += 1
                k_list = curr_file_list.copy()
                k_list[i] = os.path.join(d, 'result', 'iter{}.v'.format(i_list[i]))
                candidate_list.append(k_list)
        

        if len(candidate_list) == 0:
            a = np.array(area_summary)
            i = np.argmin(a)
            source_file = os.path.join(args.output, 'result', 'iter{}.v'.format(i))
            target_file = os.path.join(args.output, '{}_{}metric.v'.format(modulename, 'rest'))
            shutil.copyfile(source_file, target_file)
            with open(os.path.join(args.output, 'result.txt'), 'a') as f:
                f.write('{}% error metric chip area {:.2f}\n'.format('REST', area_summary[i]))

            sys.exit(0)






        pool = mp.Pool(mp.cpu_count())
        results = [pool.apply_async(evaluate_design,args=(candidate_list[i], toplevel, args.testbench, ground_truth, args.output, 'iter'+str(it)+'design'+str(i), config )) for i in range(len(candidate_list))]
        pool.close()
        pool.join()
        for result in results:
            err_list.append(result.get()[0])
            area_list.append(result.get()[1])

        idx = optimization(np.array(err_list), np.array(area_list) / initial_area , 1)
        err_summary.append(err_list[idx])
        area_summary.append(area_list[idx])
        shutil.copyfile(os.path.join(args.output, 'approx_design', 'iter{}design{}_syn.v'.format(it, idx)), os.path.join(args.output, 'result', 'iter{}.v'.format(it)))

        curr_file_list = candidate_list[idx]
        curr_iter_list = candidate_iter_num[idx]

        with open(os.path.join(args.output, 'data'), 'a') as data:
            data.write('{:.6f},{:.6f}\n'.format(err_list[idx], area_list[idx]))
            data.flush()



        if err_list[idx] >= 0.05+0.02 and m5:
            m5 = False
            a = np.array(area_summary)
            e = np.array(err_summary)
            a[e > 0.05] = np.inf
            i = np.argmin(a)
            source_file = os.path.join(args.output, 'result', 'iter{}.v'.format(i))
            target_file = os.path.join(args.output, '{}_{}metric.v'.format(modulename, 5))
            shutil.copyfile(source_file, target_file)
            with open(os.path.join(args.output, 'result.txt'), 'w') as f:
                f.write('{}% error metric chip area {:.2f}\n'.format(5, area_summary[i]))
                f.flush()


        if err_list[idx] >= 0.10+0.02 and m10:
            m10 = False
            a = np.array(area_summary)
            e = np.array(err_summary)
            a[e > 0.10] = np.inf
            i = np.argmin(a)
            source_file = os.path.join(args.output, 'result', 'iter{}.v'.format(i))
            target_file = os.path.join(args.output, '{}_{}metric.v'.format(modulename, 10))
            shutil.copyfile(source_file, target_file)
            with open(os.path.join(args.output, 'result.txt'), 'a') as f:
                f.write('{}% error metric chip area {:.2f}\n'.format(10, area_summary[i]))
                f.flush()


        if err_list[idx] >= 0.15+0.02 and m15:
            m15 = False
            a = np.array(area_summary)
            e = np.array(err_summary)
            a[e > 0.15] = np.inf
            i = np.argmin(a)
            source_file = os.path.join(args.output, 'result', 'iter{}.v'.format(i))
            target_file = os.path.join(args.output, '{}_{}metric.v'.format(modulename, 15))
            shutil.copyfile(source_file, target_file)
            with open(os.path.join(args.output, 'result.txt'), 'a') as f:
                f.write('{}% error metric chip area {:.2f}\n'.format(15, area_summary[i]))
                f.flush()



        if err_list[idx] >= 0.20+0.02 and m20:
            m20 = False
            a = np.array(area_summary)
            e = np.array(err_summary)
            a[e > 0.20] = np.inf
            i = np.argmin(a)
            source_file = os.path.join(args.output, 'result', 'iter{}.v'.format(i))
            target_file = os.path.join(args.output, '{}_{}metric.v'.format(modulename, 20))
            shutil.copyfile(source_file, target_file)
            with open(os.path.join(args.output, 'result.txt'), 'a') as f:
                f.write('{}% error metric chip area {:.2f}\n'.format(20, area_summary[i]))
                f.flush()

            sys.exit(0)

        it += 1






if __name__ == '__main__':
    main()
