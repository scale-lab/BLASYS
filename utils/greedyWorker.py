import regex as re
import sys
import random
import os
import numpy as np
import matplotlib.pyplot as plt
import subprocess
import multiprocessing as mp
import shutil
import time
import ctypes
from .utils import gen_truth, evaluate_design, synth_design, inpout, number_of_cell
from .optimizer import optimization, least_error_opt


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

        self.error_list = [0.0]
        self.area_list = []
        self.iter = 0


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
        os.mkdir(os.path.join(self.output, 'tmp'))
        os.mkdir(os.path.join(self.output, 'truthtable'))
        os.mkdir(os.path.join(self.output, 'result'))
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
        output_synth = os.path.join(self.output, self.modulename)
        input_area = synth_design(self.input, output_synth, self.library, self.script, self.path['yosys'])
        print('Original design area ', str(input_area))
        self.initial_area = input_area
        self.area_list.append(self.initial_area)
        with open(os.path.join(self.output, 'data.csv'), 'w') as data:
            data.write('HD Error,Chip area,Time used\n')
            data.write('{:.6f},{:.6f},{}\n'.format(0, self.initial_area,'Original'))

    def partitioning(self, num_parts):
        #self.num_parts = num_parts

        # Partitioning circuit
        print('Partitioning input circuit...')
        part_dir = os.path.join(self.output, 'partition')
        lsoracle_command = 'read_verilog ' + self.input + '; ' \
                'partitioning ' + str(num_parts) + ' -c '+ self.path['part_config'] +'; ' \
                'get_all_partitions ' + part_dir
        log_partition = os.path.join(self.output, 'lsoracle.log')
        with open(log_partition, 'w') as file_handler:
            subprocess.call([self.path['lsoracle'], '-c', lsoracle_command], stderr=file_handler, stdout=file_handler)

        self.modulenames = [self.modulename + '_' + str(i) for i in range(num_parts) \
                if os.path.exists(os.path.join(part_dir, self.modulename+'_'+str(i)+'.v'))]

        self.truthtable_for_parts()

    def recursive_partitioning(self, num_parts=None):
        self.modulenames = []

        if num_parts is None:
            num_parts = number_of_cell(self.input, self.path['yosys']) // 40 + 1

        print('Partitioning input circuit...')
        part_dir = os.path.join(self.output, 'partition')
        lsoracle_command = 'read_verilog ' + self.input + '; ' \
                'partitioning ' + str(num_parts) + ' -c '+ self.path['part_config'] +'; ' \
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
                        'partitioning 4 -c ' + self.path['part_config'] + '; ' \
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

        self.curr_stream = self.output_list.copy()


    def greedy_opt(self, parallel, step_size = 1, threshold=1.0, use_weight=False):

        print('==================== Starting Approximation by Greedy Search  ====================')
        with open(os.path.join(self.output, 'result', 'result.txt'), 'w') as f:
            f.write('Original chip area {:.2f}\n'.format(self.initial_area))

        while True:
            if self.next_iter(parallel, step_size, threshold, use_weight=use_weight) == -1:
                break


    def next_iter(self, parallel, step_size, threshold=1.0, least_error=False, use_weight=False):
        print('Current stream of factorization degree:', ', '.join(map(str, self.curr_stream)))
        
        if max(self.curr_stream) == 1:
            it = np.argmin(self.area_list)
            source_file = os.path.join(self.output, 'approx_design', 'iter{}.v'.format(it))
            target_file = os.path.join(self.output, 'result', '{}_{}metric.v'.format(self.modulename, round(threshold * 100)))
            shutil.copyfile(source_file, target_file)
            with open(os.path.join(self.output, 'result', 'result.txt'), 'a') as f:
                f.write('{}% error metric chip area {:.2f}\n'.format(round(threshold * 100), self.area_list[it]))
            print('All subcircuits have been approximated to degree 1. Exit approximating.')
            return -1

        print('--------------- Iteration ' + str(self.iter) + ' ---------------')
        before = time.time()
        next_stream, err, area, rank = self.evaluate_iter(self.curr_stream, self.iter, step_size, parallel, threshold, least_error, use_weight)
        after = time.time()


        time_used = after - before
        print('--------------- Finishing Iteration' + str(self.iter) + '---------------')
        part_idx = list(np.nonzero(np.subtract(next_stream, self.curr_stream)))
        print('Partition', *part_idx, 'being approximated')
        msg = 'Approximated HD error: {:.6f}%\tArea percentage: {:.6f}%\tTime used: {:.6f} sec\n'.format(100*err, 100 * area / self.initial_area, time_used)
        print(msg)
        with open(os.path.join(self.output, 'log'), 'a') as log_file:
            log_file.write(str(next_stream))
            log_file.write('\n')
            log_file.write(msg)
        
        with open(os.path.join(self.output, 'data.csv'), 'a') as data:
            data.write('{:.6f},{:.6f},{:.2f}\n'.format(err, area,time_used))

        # Moving approximate result to approx_design
        # for i,r in enumerate(rank):
        #     source_file = os.path.join(self.output, 'tmp', 'iter{}design{}_syn.v'.format(self.iter, r))
        #     target_file = os.path.join(self.output, 'approx_design', 'iter{}_{}_syn.v'.format(self.iter, i))
        #     shutil.move(source_file, target_file)

        #     source_file = os.path.join(self.output, 'tmp', 'iter{}design{}.v'.format(self.iter, r))
        #     target_file = os.path.join(self.output, 'approx_design', 'iter{}_{}.v'.format(self.iter, i))
        #     shutil.move(source_file, target_file)
        
        source_file = os.path.join(self.output, 'tmp', 'iter{}design{}.v'.format(self.iter, rank[0]))
        target_file = os.path.join(self.output, 'approx_design', 'iter{}.v'.format(self.iter))
        shutil.copyfile(source_file, target_file)
        self.curr_stream = next_stream

        if err >= threshold+0.01:
            a = np.array(self.area_list)
            e = np.array(self.error_list)
            a[e > threshold] = np.inf
            it = np.argmin(a)
            source_file = os.path.join(self.output, 'approx_design', 'iter{}.v'.format(it))
            target_file = os.path.join(self.output, 'result', '{}_{}metric.v'.format(self.modulename, round(threshold * 100)))
            shutil.copyfile(source_file, target_file)
            with open(os.path.join(self.output, 'result', 'result.txt'), 'a') as f:
                f.write('{}% error metric chip area {:.2f}\n'.format(round(threshold * 100), self.area_list[it]))
            print('Reach error threshold. Exit approximation.')
            return -1
        
        # source_file = os.path.join(self.output, 'tmp', 'iter{}design{}.v'.format(self.iter, idx))
        # target_file = os.path.join(self.output, 'approx_design', 'iter{}.v'.format(self.iter))
        # shutil.copyfile(source_file, target_file)

        self.iter += 1

        self.error_list.append(err)
        self.area_list.append(area)
        self.plot(self.error_list, self.area_list)

        return 0


    def evaluate_iter(self, curr_k_stream, num_iter, step_size, parallel, threshold, least_error, use_weight):
    
        k_lists = []
        count = 0
        changed = {}

        # Create a set of candidate k_streams
        for i in range(len(curr_k_stream)):
            if curr_k_stream[i] == 1:
                continue

            new_k_stream = list(curr_k_stream)
            new_k_stream[i] = max(new_k_stream[i] - step_size, 1)
            k_lists.append(new_k_stream)

            changed[count] = i
            count += 1

        err_list = []
        area_list = []
    
        # Parallel mode
        if parallel:
            pool = mp.Pool(mp.cpu_count())
            results = [pool.apply_async(evaluate_design,args=(k_lists[i], self, 'iter'+str(num_iter)+'design'+str(i), False, use_weight )) for i in range(len(k_lists))]
            pool.close()
            pool.join()
            for result in results:
                err_list.append(result.get()[0])
                area_list.append(result.get()[1])
        else:
        # Sequential mode
            for i in range(len(k_lists)):
                # Evaluate each list
                print('======== Design number ' + str(i))
                k_stream = k_lists[i]
                err, area = evaluate_design(k_stream, self, 'iter'+str(num_iter)+'design'+str(i))
                err_list.append(err)
                area_list.append(area)

        if least_error:
            rank = least_error_opt(np.array(err_list), np.array(area_list) / self.initial_area, threshold+0.01)
        else:
            rank = optimization(np.array(err_list), np.array(area_list), self.initial_area, self.error_list[-1], self.area_list[-1], threshold+0.01)
        result = k_lists[rank[0]]

        for i,e in enumerate(err_list):
            if e <= self.error_list[-1] and area_list[i] <= self.area_list[-1]:
                result[changed[i]] = k_lists[i][changed[i]]
            
        return result, err_list[rank[0]], area_list[rank[0]], rank

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




