from create_tb import create_testbench
from greedyWorker import GreedyWorker, print_banner
from utils import *
import os
import argparse
import yaml

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

    print('Number of partitions', len(modulenames))

    return modulenames, toplevel





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
    with open(os.path.join(app_path, 'params.yml'), 'r') as config_file:
        config = yaml.safe_load(config_file)

    #config['asso'] = ctypes.CDLL( os.path.join(app_path, 'asso.so') )
    config['asso'] = os.path.join(app_path, 'asso.so')

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
    os.mkdir(args.output)

    modulenames, toplevel = recursive_partitioning(args.input, args.output, modulename, config)

    for i in modulenames:
        module_file = os.path.join(args.output, 'partition', i)
        with open(module_file + '_tb.v', 'w') as f:
            create_testbench(module_file+'.v', i, 5000, f)

    file_list = [os.path.join(args.output, 'partition', i+'.v') for i in modulenames]
    tb_list = [os.path.join(args.output, 'partition', i+'_tb.v') for i in modulenames]
    output_list = [os.path.join(args.output, i) for i in modulenames]

    worker_list = []

    for inp, tb, out in zip(file_list, tb_list, output_list):
        worker = GreedyWorker(inp, tb, args.liberty, config)
        worker.create_output_dir(out)
        worker.evaluate_initial()
        worker.recursive_partitioning(30)
        worker_list.append(worker)






if __name__ == '__main__':
    main()
