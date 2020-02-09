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
from .utils import gen_truth, evaluate_design, synth_design, inpout, number_of_cell, write_aiger, get_delay, get_power, approximate, create_wrapper, module_info
from .optimizer import optimization, least_error_opt
from .create_tb import create_testbench
from . import metric


class GreedyWorker():
    def __init__(self, input_circuit, library, path, testbench, err_metric, sta):
        # Check executable
        print('Checking software dependency ...')
        assert shutil.which(path['iverilog']), 'Cannot find iverilog'
        assert shutil.which(path['vvp']), 'Cannot find vvp'
        assert shutil.which(path['abc']), 'Cannot find abc'
        assert shutil.which(path['lsoracle']), 'Cannot find lsoracle'
        assert shutil.which(path['yosys']), 'Cannot find yosys'
        if sta:
            assert shutil.which(path['OpenSTA']), 'Cannot find OpenSTA'
    
        # Check library file
        assert os.path.exists(library), 'Cannot find liberty file'

        self.input = input_circuit
        self.testbench = testbench
        self.library = library
        self.path = path
        self.sta = sta

        self.error_list = [0.0]
        #self.metric_list = [[.0, .0, .0]]
        self.area_list = []
        self.power_list = []
        self.delay_list = []
        self.design_list = []
        self.iter = 0

        # Get metric function
        try:
            self.metric = getattr(metric, err_metric)
        except AttributeError:
            print('[Error] Metric function {}() not found in utils/metric.py.'.format(err_metric))
            sys.exit(1)

        # Get module name
        self.modulename = None
        with open(self.input) as file:
            line = file.readline()
            while line:
                tokens = re.split('[ (]', line)
                for i in range(len(tokens)):
                    if tokens[i] == 'module':
                        self.modulename = tokens[i+1]
                        break
                if self.modulename is not None:
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
            #file.write('strash;fraig;refactor;rewrite -z;scorr;map') 
            #file.write('bdd;collapse;strash;map')
            #file.write('bdd;collapse;order;map')
            #file.write('strash;fraig')
            #for i in range(30):
                #file.write(';rewrite;refactor;resub;balance')
            #file.write(';map')
            file.write('strash;ifraig;dc2;fraig;rewrite;refactor;resub;rewrite;refactor;resub;rewrite;rewrite -z;rewrite -z;rewrite -z;')
            file.write('balance;refactor -z;refactor -N 11;resub -K 10;resub -K 12;resub -K 14;resub -K 16;refactor;balance;map -a')

    def convert2aig(self):
        print('Parsing input verilog into aig format ...')
        self.aig = os.path.join(self.output, self.modulename + '.aig')
        mapping = os.path.join(self.output, self.modulename + '.map')
        write_aiger(self.input, self.path['yosys'], self.aig, mapping)
        # self.testbench = os.path.join(self.output, self.modulename+'_aig_tb.v')
        # with open(self.testbench_v) as f:
            # bench = f.readlines()
        # with open(self.testbench, 'w') as f:
            # for i, content in enumerate(bench):
                # if i != 3:
                    # f.write(content)
                # else:
                    # f.write(self.modulename+' dut(')

                    # f.write('pi[{}]'.format(inp_map[0]))
                    # for i in range(1, len(inp_map)):
                        # f.write(', pi[{}]'.format(inp_map[i]))
                    # for i in range(len(out_map)):
                        # f.write(', po[{}]'.format(out_map[i]))
                    # f.write(');\n')

    def blasys(self):
        # inp, out = inpout(self.input)
        info = module_info(self.input, self.path['yosys'])
        inp, out = info[3], info[5]
        if inp > 16:
            print('Too many input to directly factorize. Please use partitioning mode.')
            return 1
        self.input_list = [inp]
        self.output_list = [out]
        self.modulenames = [self.modulename]
        os.mkdir(os.path.join(self.output, self.modulename))
        truth_dir = os.path.join(self.output, self.modulename)
        
        if self.sta:
            sta_script = os.path.join(self.output, 'sta.script')
            sta_output = os.path.join(self.output, 'sta.out')
            synth_input = os.path.join(self.output, self.modulename+'_syn.v')
            self.delay = get_delay(self.path['OpenSTA'], sta_script, self.library, synth_input, self.modulename, sta_output)
            power = get_power(self.path['OpenSTA'], sta_script, self.library, synth_input, self.modulename, sta_output, self.delay)
        else:
            self.delay = float('nan')
            power = float('nan')


        f = open(os.path.join(self.output, 'data.csv'), 'a')
        f.write('{},{},{},{},{}\n'.format('Iter','Metric', 'Area(um^2)', 'Power(uW)', 'Delay(ns)') )
        f.write('{},{:<.6f},{:.2f},{:.6f},{:.6f}\n'.format('Org', 0, self.initial_area, power, self.delay) )

        err_list = []
        area_list = []
        for k in range(out-1, 0,-1):
            # Approximate
            approximate(truth_dir, k, self, 0)
            in_file = os.path.join(self.output, self.modulename+'_approx_k='+str(k)+'.v')
            out_file = os.path.join(self.output, self.modulename, self.modulename+'_approx_k='+str(k))
            gen_truth = os.path.join(self.output, self.modulename+'.truth_wh_'+str(k))
            area = synth_design(in_file, out_file, self.library, self.script, self.path['yosys'])
            err = self.metric(truth_dir+'.truth', gen_truth)
            err_list.append(err)
            area_list.append(area/self.initial_area)
            # print('Factorization level {}, Area {}, Error {}\n'.format(k, area, err))
            # f.write('{:.6f},{:.6f},Level{}'.format(err, area, k))
            if self.sta:
                sta_script = os.path.join(self.output, 'sta.script')
                sta_output = os.path.join(self.output, 'sta.out')
                delay_iter = get_delay(self.path['OpenSTA'], sta_script, self.library, out_file+'_syn.v', self.modulename, sta_output)
                power_iter = get_power(self.path['OpenSTA'], sta_script, self.library, out_file+'_syn.v', self.modulename, sta_output, self.delay)
                print('Factorization degree {}, Metric {:.6%}, Area {:.2f}, Power {:.4f}, Delay {:.4f}'.format(k, err, area, power_iter, delay_iter))
            else:
                delay_iter = float('nan')
                power_iter = float('nan')
                print('Factorization degree {}, Metric {:.6%}, Area {:.2f}'.format(k, err, area))
            f.write('{},{:.6f},{:.2f},{:.6f},{:.6f}\n'.format(k, err, area, power_iter, delay_iter) )

        self.plot(err_list, area_list)
        f.close()




    def evaluate_initial(self):
       #  if self.testbench is None:
            # self.testbench_v = os.path.join(self.output, self.modulename+'_tb.v')
            # with open(self.testbench_v, 'w') as f:
                # create_testbench(self.input, tb_size, f)

        #self.testbench = self.testbench_v
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


        # return inpout(self.input)

    def partitioning(self, num_parts):
        #self.num_parts = num_parts

        # Partitioning circuit
        print('Partitioning input circuit...')
        part_dir = os.path.join(self.output, 'partition')
        lsoracle_command = 'read_aig ' + self.aig + '; ' \
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
            num_parts = number_of_cell(self.input, self.path['yosys']) // 30 + 1

        print('Partitioning input circuit...')
        part_dir = os.path.join(self.output, 'partition')
        lsoracle_command = 'read_aig ' + self.aig + '; ' \
                'partitioning ' + str(num_parts) + ' -c '+ self.path['part_config'] +'; ' \
                'get_all_partitions ' + part_dir
        
        log_partition = os.path.join(self.output, 'lsoracle.log')
        with open(log_partition, 'w') as file_handler:
            subprocess.call([self.path['lsoracle'], '-c', lsoracle_command], stderr=subprocess.STDOUT, stdout=file_handler)

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
                        'partitioning 3 -c ' + self.path['part_config'] + '; ' \
                        'get_all_partitions ' + part_dir
                with open(log_partition, 'a') as file_handler:
                    subprocess.call([self.path['lsoracle'], '-c', lsoracle_command], stderr=subprocess.STDOUT, stdout=file_handler)
                partitioned.extend([mod + '_' + str(i) for i in range(3)])
                
                with open(toplevel, 'a') as top:
                    subprocess.call(['cat', mod_path], stdout=top)

                os.remove(mod_path)
            elif 0 < inp <= 16:
                self.modulenames.append(mod)

        print('Number of partitions', len(self.modulenames))


        self.truthtable_for_parts()

        # Rewrite top-level
        mapping = os.path.join(self.output, self.modulename + '.map')
        outfile = os.path.join(self.output, 'out.v')
        topfile = os.path.join(self.output, 'partition', self.modulename + '.v')
        create_wrapper(self.input, outfile, topfile, mapping, self)
     

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
        self.curr_streams = [self.output_list.copy()]
        self.explored_streams = [self.output_list.copy()]


    def greedy_opt(self, parallel, step_size = 1, threshold=[1000000.], track=3):
        threshold.sort()
        while True:
            if self.next_iter(parallel, step_size, threshold, track=track) == -1:
                break


    def next_iter(self, parallel, step_size, threshold=[1000000.], least_error=False, track=3):

        if self.iter == 0:
            print('==================== Starting Approximation by Greedy Search  ====================')
            with open(os.path.join(self.output, 'result', 'result.txt'), 'w') as f:

                if self.sta:
                    sta_script = os.path.join(self.output, 'sta.script')
                    sta_output = os.path.join(self.output, 'sta.out')
                    synth_input = os.path.join(self.output, self.modulename+'_syn.v')
                    self.delay = get_delay(self.path['OpenSTA'], sta_script, self.library, synth_input, self.modulename, sta_output)
                    power = get_power(self.path['OpenSTA'], sta_script, self.library, synth_input, self.modulename, sta_output, self.delay) 
                else:
                    self.delay = float('nan')
                    power = float('nan')

                f.write('{:<10}{:<15}{:<15}{:<15}\n'.format('Metric', 'Area(um^2)', 'Power(uW)', 'Delay(ns)') )
                f.write('{:<10.2f}{:<15.2f}{:<15.6f}{:<15.6f}\n'.format(0, self.initial_area, power, self.delay) )
            self.power_list.append(power)
            self.delay_list.append(self.delay)
            with open(os.path.join(self.output, 'data.csv'), 'a') as data:
                data.write('{},{},{},{},{}\n'.format('Iter','Metric', 'Area(um^2)', 'Power(uW)', 'Delay(ns)') )
                data.write('{},{:.6f},{:.2f},{:.6f},{:.6f}\n'.format('Org', 0, self.initial_area, power, self.delay) )


        print('Current stream of factorization degree:\n','\n'.join(map(str, self.curr_streams)))
        
        if len(self.curr_streams) == 1 and max(self.curr_streams[0]) == 1:

            a = np.array(self.area_list)
            e = np.array(self.error_list)
            a[e > threshold[0]] = np.inf
            idx = np.argmin(a)
            source_file = os.path.join(self.output, 'tmp', '{}_syn.v'.format(self.design_list[idx]))
            target_file = os.path.join(self.output, 'result', '{}_{}metric.v'.format(self.modulename, 'REST'))
            shutil.copyfile(source_file, target_file)
            with open(os.path.join(self.output, 'result', 'result.txt'), 'a') as f:
                # sta_script = os.path.join(self.output, 'sta.script')
                # sta_output = os.path.join(self.output, 'sta.out')
                # app_delay = get_delay(self.path['OpenSTA'], sta_script, self.library, source_file, self.modulename, sta_output)
                # power = get_power(self.path['OpenSTA'], sta_script, self.library, source_file, self.modulename, sta_output, self.delay) * 1e6
                # f.write('{}% error metric chip area {:.2f}, delay {:.2f}, power {:.2f}\n'.format('REST', self.area_list[it-1], app_delay, power))
                f.write('{:<10.6f}{:<15.2f}{:<15.6f}{:<15.6f}\n'.format(self.error_list[idx], self.area_list[idx], self.power_list[idx], self.delay_list[idx]) )

            print('All subcircuits have been approximated to degree 1. Exit approximating.')
            return -1

        print('--------------- Iteration ' + str(self.iter) + ' ---------------')
        before = time.time()
        next_stream, streams, err, area, delay, power, name_list, rank = self.evaluate_iter(self.curr_streams, self.iter, step_size, parallel, threshold[0], least_error)
        after = time.time()


        time_used = after - before
        print('--------------- Finishing Iteration' + str(self.iter) + '---------------')
        part_idx = list(np.nonzero(np.subtract(next_stream, self.curr_stream)))
        print('Partition', *part_idx, 'being approximated')

        msg = 'Approximated error: {:.6f}%\tArea percentage: {:.6f}%\tTime used: {:.6f} sec\n'.format(100*err[rank[0]], 100 * area[rank[0]] / self.initial_area, time_used)
        print(msg)
        with open(os.path.join(self.output, 'log'), 'a') as log_file:
            log_file.write(str(next_stream))
            log_file.write('\n')
            log_file.write(msg)
        
        # with open(os.path.join(self.output, 'data.csv'), 'a') as data:
            # data.write('{:.6f},{:.6f},{:.2f}\n'.format(err, area,time_used))

        # Moving approximate result to approx_design
        # for i,r in enumerate(rank):
        #     source_file = os.path.join(self.output, 'tmp', 'iter{}design{}_syn.v'.format(self.iter, r))
        #     target_file = os.path.join(self.output, 'approx_design', 'iter{}_{}_syn.v'.format(self.iter, i))
        #     shutil.move(source_file, target_file)

        #     source_file = os.path.join(self.output, 'tmp', 'iter{}design{}.v'.format(self.iter, r))
        #     target_file = os.path.join(self.output, 'approx_design', 'iter{}_{}.v'.format(self.iter, i))
        #     shutil.move(source_file, target_file)
        
        # source_file = os.path.join(self.output, 'tmp', 'iter{}design{}.v'.format(self.iter, rank[0]))
        # target_file = os.path.join(self.output, 'approx_design', 'iter{}.v'.format(self.iter))
        # shutil.copyfile(source_file, target_file)

        # for i, n in enumerate(name_list):
            # source_file = os.path.join(self.output, 'tmp', '{}_syn.v'.format(n))
            # target_file = os.path.join(self.output, 'approx_design', 'iter{}_syn.v'.format(self.iter))
            # shutil.copyfile(source_file, target_file)
        
        self.curr_streams = [streams[i] for i in rank[:track]]

            # sta_script = os.path.join(self.output, 'sta.script')
            # sta_output = os.path.join(self.output, 'sta.out')
            # delay_design = get_delay(self.path['OpenSTA'], sta_script, self.library, source_file, self.modulename, sta_output)
            # power_design = get_power(self.path['OpenSTA'], sta_script, self.library, source_file, self.modulename, sta_output, self.delay) * 1e6
            
            # self.power_list.append(power_design)
            # self.delay_list.append(delay_design)
            
            # if i == rank[0]:
        with open(os.path.join(self.output, 'data.csv'), 'a') as data:
            data.write('{},{:.6%},{:.2f},{:.6f},{:.6f}\n'.format(self.iter, err[rank[0]], area[rank[0]], power[rank[0]], delay[rank[0]]) )

        self.iter += 1

        self.error_list += err
        self.area_list += area
        self.design_list += name_list
        self.power_list += power
        self.delay_list += delay

        if err[rank[0]] >= threshold[0]+0.01:
            ts = threshold.pop(0)
            print('Reach threshold on', ts)
            a = np.array(self.area_list)
            e = np.array(self.error_list)
            a[e > ts] = np.inf
            idx = np.argmin(a)
            source_file = os.path.join(self.output, 'tmp', '{}_syn.v'.format(self.design_list[idx]))
            target_file = os.path.join(self.output, 'result', '{}_{}metric.v'.format(self.modulename, int(ts*100)))
            shutil.copyfile(source_file, target_file)
            with open(os.path.join(self.output, 'result', 'result.txt'), 'a') as f:
                # sta_script = os.path.join(self.output, 'sta.script')
                # sta_output = os.path.join(self.output, 'sta.out')
                # app_delay = get_delay(self.path['OpenSTA'], sta_script, self.library, source_file, self.modulename, sta_output)
                # power = get_power(self.path['OpenSTA'], sta_script, self.library, source_file, self.modulename, sta_output, self.delay) * 1e6
                #f.write('{}% error metric chip area {:.2f}, delay {:.2f}, power {:.2f}\n'.format(int(ts*100), self.area_list[it], app_delay, power))
                f.write('{:<10.6f}{:<15.2f}{:<15.6f}{:<15.6f}\n'.format(self.error_list[idx], self.area_list[idx], self.power_list[idx], self.delay_list[idx]) )

        if len(threshold) == 0: 
            print('Reach error threshold. Exit approximation.')
            return -1
        
        # source_file = os.path.join(self.output, 'tmp', 'iter{}design{}.v'.format(self.iter, idx))
        # target_file = os.path.join(self.output, 'approx_design', 'iter{}.v'.format(self.iter))
        # shutil.copyfile(source_file, target_file)

        
        self.plot(self.error_list, self.area_list)

        return 0


    def evaluate_iter(self, curr_k_streams, num_iter, step_size, parallel, threshold, least_error):
    
        k_lists = []
        err_list = []
        area_list = []
        delay_list = []
        power_list = []
        name_list = []
        count = 0
        changed = {}

        for num_track, curr_k_stream in enumerate(curr_k_streams):
            print('==========TRACK {} =========='.format(num_track))
            # Create a set of candidate k_streams
            k_lists_tmp = []
            for i in range(len(curr_k_stream)):
                if curr_k_stream[i] == 1:
                    continue

                new_k_stream = list(curr_k_stream)
                new_k_stream[i] = max(new_k_stream[i] - step_size, 1)
                
                if new_k_stream in self.explored_streams:
                    continue
                k_lists_tmp.append(new_k_stream)
                self.explored_streams.append(new_k_stream)
                
                changed[count] = i
                count += 1

            name_list += ['iter'+str(num_iter)+'track'+str(num_track)+'design'+str(i) for i in range((len(k_lists_tmp)))]
        
            # Parallel mode
            if parallel:
                pool = mp.Pool(mp.cpu_count())
                results = [pool.apply_async(evaluate_design,args=(k_lists_tmp[i], self, 'iter'+str(num_iter)+'track'+str(num_track)+'design'+str(i), False )) for i in range(len(k_lists_tmp))]
                pool.close()
                pool.join()
                for result in results:
                    err_list.append(result.get()[0])
                    area_list.append(result.get()[1])
                    delay_list.append(result.get()[2])
                    power_list.append(result.get()[3])
            else:
            # Sequential mode
                for i in range(len(k_lists_tmp)):
                    # Evaluate each list
                    print('======== Design number ' + str(i))
                    k_stream = k_lists_tmp[i]
                    err, area, delay, power = evaluate_design(k_stream, self, 'iter'+str(num_iter)+'track'+str(num_track)+'design'+str(i))
                    err_list.append(err)
                    area_list.append(area)
                    delay_list.append(delay)
                    power_list.append(power)

            k_lists += k_lists_tmp

        if least_error:
            rank = least_error_opt(np.array(err_list), np.array(area_list) / self.initial_area, threshold)
        else:
            rank = optimization(np.array(err_list), np.array(area_list), self.initial_area, self.error_list[-1], self.area_list[-1], threshold+0.01)
        result = k_lists[rank[0]]

        # for i,e in enumerate(err_list):
            # if e <= self.error_list[-1] and area_list[i] <= self.area_list[-1]:
                # result[changed[i]] = k_lists[i][changed[i]]
            
        return result, k_lists, err_list, area_list, delay_list, power_list, name_list, rank

    def plot(self, error_list, area_list):

        error_np = np.array(error_list) * 100
        area_np = np.array( area_list ) / area_list[0] * 100
        c = np.random.rand(len(error_list))

        fig, ax = plt.subplots(1, 1)
        ax.scatter(error_np, area_np, c='r', s=6)
        # plt.plot(error_np, area_np, c='b', linewidth=3)
        #plt.xlim(0,1.0)
        #plt.ylim(0,1.1)
        ax.set_ylabel('Area ratio (%)')
        ax.set_xlabel('HD Approximation Error (%)')
        ax.set(xlim=(1e-3, 1e2), ylim=(.0, 1.2))
        #plt.xticks(np.arange(0,1,0.1))
        #plt.yticks(np.arange(0,1.1,0.1))
        ax.set_title('Greedy search on ' + self.modulename)
        ax.set_xscale('log')
        fig.savefig(os.path.join(self.output, 'visualization.png'))
        
        fig.clf()




