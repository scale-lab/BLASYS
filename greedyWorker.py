import regex as re
import sys
import random
import os
import numpy as np
import matplotlib.pyplot as plt
import subprocess
import multiprocessing as mp
import shutil
import argparse
import yaml
import time
import ctypes
from utils import assess_HD, gen_truth, evaluate_design, synth_design, inpout

def optimization(err_list, area_list, threshold):

    # Compute ratio
    #np_area = np.array(area_list)
    #np_err = np.array(err_list)
    #grad = np.true_divide(np_area - 1, np_err)
    # Solving division by 0 issue
    #grad[np.isnan(grad)] = -np.inf
    #print(grad)
    # Finding optimum
    #index_min, = np.where(grad == grad.min())
    #area_min_grad = np_area[index_min]
    
    #return index_min[area_min_grad.argmin()]

    gradient = np.zeros(len(err_list))

    for (idx,(area, err)) in enumerate(zip(area_list, err_list)):
        if err > threshold:
            gradient[idx] = np.inf
        elif err == 0:
            gradient[idx] = -np.inf
        else:
            gradient[idx] = (area - 1) / err

    index_min_grad, = np.where(gradient == gradient.min())
    area_min_grad = np.array(area_list)[index_min_grad]

    return index_min_grad[area_min_grad.argmin()]

    



class GreedyWorker():
    def __init__(self, input_circuit, testbench, library, path):
        # Check executable
        assert shutil.which(path['iverilog']), 'Cannot find iverilog'
        assert shutil.which(path['vvp']), 'Cannot find vvp'
        assert shutil.which(path['abc']), 'Cannot find abc'
        assert shutil.which(path['lsoracle']), 'Cannot find lsoracle'
        assert shutil.which(path['yosys']), 'Cannot find yosys'
    
        # Check library file
        assert os.path.exists(library), 'Cannot find liberty file'

        self.input = input_circuit
        self.testbench = testbench
        self.library = library
        self.path = path

        # Get modulename
        with open(self.input) as file:
            line = file.readline()
            while line:
                tokens = re.split('[ (]', line)
                for i in range(len(tokens)):
                    if tokens[i] == 'module':
                        self.modulename = tokens[i+1]
                        break
                line = file.readline()


    def create_output_dir(self, output):

        print('Create output directory...')
        self.output = output

        if os.path.isdir(self.output):
            shutil.rmtree(self.output)
        os.mkdir(self.output)

        os.mkdir(os.path.join(self.output, 'approx_design'))
        os.mkdir(os.path.join(self.output, 'truthtable'))
        # Write script
        self.script = os.path.join(self.output, 'abc.script')
        with open(self.script, 'w') as file:
            file.write('strash;fraig;refactor;rewrite -z;scorr;map')


    def evaluate_initial(self):
        print('Simulating truth table on input design...')
        subprocess.call([self.path['iverilog'], '-o', self.modulename+'.iv', self.input, self.testbench ])
        output_truth = os.path.join(self.output, self.modulename+'.truth')
        with open(output_truth, 'w') as f:
            subprocess.call([self.path['vvp'], self.modulename+'.iv'], stdout=f)
        os.remove(self.modulename + '.iv')

        print('Synthesizing input design with original partitions...')
        output_synth = os.path.join(self.output, self.modulename+'_syn')
        input_area = synth_design(self.input, output_synth, self.library, self.script, self.path['yosys'])
        print('Original design area ', str(input_area))
        self.initial_area = input_area


    def partitioning(self, num_parts):
        #self.num_parts = num_parts

        # Partitioning circuit
        print('Partitioning input circuit...')
        part_dir = os.path.join(self.output, 'partition')
        lsoracle_command = 'read_verilog ' + self.input + '; ' \
                'partitioning ' + str(num_parts) + '; ' \
                'get_all_partitions ' + part_dir
        log_partition = os.path.join(self.output, 'lsoracle.log')
        with open(log_partition, 'w') as file_handler:
            subprocess.call([self.path['lsoracle'], '-c', lsoracle_command], stderr=file_handler, stdout=file_handler)

        self.modulenames = [self.modulename + '_' + str(i) for i in range(num_parts) \
                if inpout(os.path.join(part_dir, self.modulename+'_'+str(i)+'.v'))[0] != 0]

        self.truthtable_for_parts()

    def recursive_partitioning(self, num_parts):
        self.modulenames = []

        print('Partitioning input circuit...')
        part_dir = os.path.join(self.output, 'partition')
        lsoracle_command = 'read_verilog ' + self.input + '; ' \
                'partitioning ' + str(num_parts) + '; ' \
                'get_all_partitions ' + part_dir
        
        log_partition = os.path.join(self.output, 'lsoracle.log')
        with open(log_partition, 'w') as file_handler:
            subprocess.call([self.path['lsoracle'], '-c', lsoracle_command], stderr=file_handler, stdout=file_handler)

        partitioned = [self.modulename + '_' + str(i) for i in range(num_parts)]

        toplevel = os.path.join(part_dir, self.modulename+'.v')

        while len(partitioned) > 0:
            mod = partitioned.pop()
            mod_path = os.path.join(part_dir, mod+'.v')
            if not os.path.exists(mod_path):
                continue

            inp, out = inpout(mod_path)
            if inp > 16:
                lsoracle_command = 'read_verilog ' + mod_path + '; ' \
                        'partitioning ' + str(num_parts) + '; ' \
                        'get_all_partitions ' + part_dir
                with open(log_partition, 'a') as file_handler:
                    subprocess.call([self.path['lsoracle'], '-c', lsoracle_command], stderr=file_handler, stdout=file_handler)
                partitioned.extend([mod + '_' + str(i) for i in range(num_parts)])
                
                with open(toplevel, 'a') as top:
                    subprocess.call(['cat', mod_path], stdout=top)

                os.remove(mod_path)
            elif 0 < inp <= 16:
                self.modulenames.append(mod)

        print('Number of partitions', len(self.modulenames))


        self.truthtable_for_parts()
     

    def truthtable_for_parts(self):
        # Generate truth table for each partitions
        self.input_list = []
        self.output_list = []
        #for i in range(num_parts):
            #modulename = self.modulename + '_' + str(i)
        for i, modulename in enumerate(self.modulenames):
            file_path = os.path.join(self.output, 'partition', modulename)
            #if not os.path.exists(file_path + '.v'):
             #   print('Submodule ' + str(i) + ' is empty')
              #  self.input_list.append(-1)
               # self.output_list.append(-1)
               # continue

            # Create testbench for partition
            print('Create testbench for partition '+str(i))
            n, m = gen_truth(file_path, modulename)
            self.input_list.append( n )
            self.output_list.append( m )

            # Generate truthtable
            print('Generate truth table for partition '+str(i))
            part_output_dir = os.path.join(self.output, modulename)
            os.mkdir(part_output_dir)
            subprocess.call([self.path['iverilog'], '-o', file_path+'.iv', file_path+'.v', file_path+'_tb.v'])
            with open( os.path.join(part_output_dir, modulename + '.truth'), 'w') as f:
                subprocess.call([self.path['vvp'], file_path+'.iv'], stdout=f)
                os.remove(file_path+'.iv')


    def greedy_opt(self, threshold, parallel, step_size = 1):
        self.threshold = threshold
        self.parallel = parallel

        print('==================== Starting Approximation by Greedy Search  ====================')
        error_list = []
        area_list = []
        count_iter = 1
        curr_stream = self.output_list.copy()

        while True:

            if max(curr_stream) == 1:
                print('All subcircuits have been approximated to degree 1. Exit approximating.')
                sys.exit(0)

            print('--------------- Iteration ' + str(count_iter) + ' ---------------')
            before = time.time()
            next_stream, err, area = self.evaluate_iter(curr_stream, count_iter, step_size)
            after = time.time()
    
            if next_stream == False:
                break

            time_used = after - before
            print('--------------- Finishing Iteration' + str(count_iter) + '---------------')
            msg = 'Approximated HD error: {:.6f}%\tArea percentage: {:.6f}%\tTime used: {:.6f} sec\n'.format(100*err, 100*area, time_used)
            print(msg)
            with open(os.path.join(self.output, 'log'), 'a') as log_file:
                log_file.write(str(next_stream))
                log_file.write('\n')
                log_file.write(msg)
            
            with open(os.path.join(self.output, 'data'), 'a') as data:
                data.write('{:.6f},{:.6f},{:.2f}\n'.format(err, area,time_used))

            curr_stream = next_stream

            count_iter += 1

            error_list.append(err)
            area_list.append(area)
            self.plot(error_list, area_list)


    def evaluate_iter(self, curr_k_stream, num_iter, step_size):
    
        k_lists = []

        # Create a set of candidate k_streams
        for i in range(len(curr_k_stream)):
            if curr_k_stream[i] == 1:
                continue

            new_k_stream = list(curr_k_stream)
            new_k_stream[i] = max(new_k_stream[i] - step_size, 1)
            k_lists.append(new_k_stream)

        err_list = []
        area_list = []
    
        # Parallel mode
        if self.parallel:
            pool = mp.Pool(mp.cpu_count())
            results = [pool.apply_async(evaluate_design,args=(k_lists[i], self, num_iter, i)) for i in range(len(k_lists))]
            pool.close()
            pool.join()
            for result in results:
                err_list.append(result.get()[0])
                area_list.append(result.get()[1] / self.initial_area)
        else:
        # Sequential mode
            for i in range(len(k_lists)):
                # Evaluate each list
                print('======== Design number ' + str(i))
                k_stream = k_lists[i]
                err, area = evaluate_design(k_stream, self, num_iter, i)
                err_list.append(err)
                area_list.append(area/self.initial_area)

        if np.min(err_list) > self.threshold:
            return False, 0, 0


        idx = optimization(err_list, area_list, self.threshold)

        return k_lists[idx], err_list[idx], area_list[idx]

    def plot(self, error_list, area_list):

        error_np = np.array(error_list)
        area_np = np.array( area_list )
        c = np.random.rand(len(error_list))

        plt.scatter(error_np, area_np, c='r', s=6)
        plt.plot(error_np, area_np, c='b', linewidth=3)
        plt.xlim(0,1.0)
        plt.ylim(0,1.1)
        plt.ylabel('Area ratio')
        plt.xlabel('HD Approximation Error')
        plt.xticks(np.arange(0,1,0.1))
        plt.yticks(np.arange(0,1.1,0.1))
        plt.title('Greedy search on ' + self.modulename)
        plt.savefig(os.path.join(self.output, 'visualization.png'))



def print_banner():
    print('/----------------------------------------------------------------------------\\')
    print('|                                                                            |')
    print('|  BLASYS -- Approximate Logic Synthesis Using Boolean Matrix Factorization  |')
    print('|  Version: 0.2.0                                                            |')
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

    worker = GreedyWorker(args.input, args.testbench, args.liberty, config)
    worker.create_output_dir(args.output)
    worker.evaluate_initial()
    worker.recursive_partitioning(args.npart)
    worker.greedy_opt(args.threshold, args.parallel)


if __name__ == '__main__':
    main()
