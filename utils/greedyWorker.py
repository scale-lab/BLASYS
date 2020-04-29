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
from .utils import gen_truth, evaluate_design, synth_design, inpout, number_of_cell, write_aiger, get_delay, get_power, approximate, create_wrapper, module_info, NoValidDesign, create_wrapper_single
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
        if library is not None:
            assert os.path.exists(library), 'Cannot find liberty file'

        self.input = input_circuit
        self.testbench = testbench
        self.library = library
        self.path = path
        self.sta = sta

        self.error_list = [0.0]
        self.area_list = []
        self.power_list = []
        self.delay_list = []
        self.design_list = []
        self.iter = 0

        self.iter_rank = [0]

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
        
        if output is None:
            output = self.modulename + time.strftime('_%Y%m%d-%H%M%S')

        print('Create output directory...')
        self.output = output

        if os.path.isdir(self.output):
            shutil.rmtree(self.output)
        os.mkdir(self.output)

        os.mkdir(os.path.join(self.output, 'tmp'))
        os.mkdir(os.path.join(self.output, 'truthtable'))
        os.mkdir(os.path.join(self.output, 'result'))
        os.mkdir(os.path.join(self.output, 'log'))
        bmf_part = 'bmf_partition'
        os.mkdir(os.path.join(self.output, bmf_part))
        # Write script
        dir_path = os.path.dirname(os.path.realpath(__file__))
        self.script = os.path.join(dir_path, '..', 'config', 'abc.script')
        # self.script = os.path.join(self.output, 'abc.script')
        # with open(self.script, 'w') as file:
            # file.write('strash;ifraig;dc2;fraig;rewrite;refactor;resub;rewrite;refactor;resub;rewrite;rewrite -z;rewrite -z;rewrite -z;')
            # file.write('balance;refactor -z;refactor -N 11;resub -K 10;resub -K 12;resub -K 14;resub -K 16;refactor;balance;map -a')



    def convert2aig(self):
        print('Parsing input verilog into aig format ...')
        self.aig = os.path.join(self.output, self.modulename + '.aig')
        mapping = os.path.join(self.output, self.modulename + '.map')
        write_aiger(self.input, self.path['yosys'], self.aig, mapping)



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
        out_dir = os.path.join(self.output, 'bmf_partition', self.modulename)
        os.mkdir(out_dir)
        src_dir = os.path.join(self.output, self.modulename)
        truth_dir = os.path.join(out_dir, self.modulename)
        shutil.copyfile(src_dir+'.truth', truth_dir+'.truth')
        
        if self.sta:
            sta_script = os.path.join(self.output, 'sta.script')
            sta_output = os.path.join(self.output, 'sta.out')
            synth_input = os.path.join(self.output, self.modulename+'_syn.v')
            self.delay = get_delay(self.path['OpenSTA'], sta_script, self.library, synth_input, self.modulename, sta_output)
            power = get_power(self.path['OpenSTA'], sta_script, self.library, synth_input, self.modulename, sta_output, self.delay)
        else:
            self.delay = float('nan')
            power = float('nan')


        f = open(os.path.join(self.output, 'result', 'iteration.csv'), 'a')
        f.write('{},{},{},{},{},{}\n'.format('Iter','Metric', 'Area(um^2)', 'Power(uW)', 'Delay(ns)', 'Filename') )
        f.write('{},{:<.6f},{:.2f},{:.6f},{:.6f},{}\n'.format('Org', 0, self.initial_area, power, self.delay, 'Org') )

        d = open(os.path.join(self.output, 'result', 'data.csv'), 'a')
        d.write('{},{},{},{},{}\n'.format('Name','Metric', 'Area(um^2)', 'Power(uW)', 'Delay(ns)') )
        d.write('{},{:.6f},{:.2f},{:.6f},{:.6f}\n'.format('Org', 0, self.initial_area, power, self.delay) )

        # Create wrapper
        wrapper = os.path.join(self.output, 'wrapper.v')
        create_wrapper_single(self.input, wrapper, self)


        err_list = []
        area_list = []
        for k in range(out-1, 0,-1):
            # Approximate
            approximate(truth_dir, k, self, 0, 'top')
            in_file = os.path.join(out_dir, self.modulename+'_approx_k='+str(k)+'.v')
            filename = self.modulename+'_k='+str(k)
            out_file = os.path.join(self.output, 'result', filename)
            gen_truth = os.path.join(out_dir, self.modulename+'.truth_wh_'+str(k))
            area = synth_design(in_file+' '+wrapper, out_file, self.library, self.script, self.path['yosys'])
            err = self.metric(truth_dir+'.truth', gen_truth)
            err_list.append(err)
            area_list.append(area/self.initial_area)
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
            f.write('{},{:.6f},{:.2f},{:.6f},{:.6f},{}\n'.format(k, err, area, power_iter, delay_iter, filename) )
            d.write('{},{:.6f},{:.2f},{:.6f},{:.6f}\n'.format(filename, err, area, power_iter, delay_iter) )
        self.plot(err_list, area_list)
        f.close()
        d.close()

        # Clear up directory
        if self.sta:
            os.remove(sta_script)
            os.remove(sta_output)

        os.remove(wrapper)
        shutil.rmtree(os.path.join(self.output, 'tmp'))
        shutil.rmtree(os.path.join(self.output, 'truthtable'))
        shutil.rmtree(os.path.join(self.output, 'log'))




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



    def partitioning(self, num_parts):

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
        
        log_partition = os.path.join(self.output, 'log', 'lsoracle.log')
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

        # Clear up redundant file
        # os.remove(self.aig)
        # os.remove(os.path.join(self.output, self.modulename + '.map'))

     

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
            part_output_dir = os.path.join(self.output, 'bmf_partition', modulename)
            os.mkdir(part_output_dir)
            subprocess.call([self.path['iverilog'], '-o', file_path+'.iv', file_path+'.v', file_path+'_tb.v'])
            with open( os.path.join(part_output_dir, modulename + '.truth'), 'w') as f:
                subprocess.call([self.path['vvp'], file_path+'.iv'], stdout=f)
                os.remove(file_path+'.iv')

        self.curr_stream = self.output_list.copy()
        self.curr_streams = [self.output_list.copy()]
        self.explored_streams = [self.output_list.copy()]


    def greedy_opt(self, parallel, cpu_count, step_size = 1, threshold=[1000000.], track=3):
        threshold.sort()
        while True:
            if self.next_iter(parallel, cpu_count, step_size, threshold, track=track) == -1:
                break


    def next_iter(self, parallel, cpu_count, step_size, threshold=[1000000.], least_error=False, track=3):

        if self.iter == 0:
            print('==================== Starting Approximation by Greedy Search  ====================')
            with open(os.path.join(self.output, 'result', 'result.txt'), 'w') as f:

                if self.sta:
                    sta_script = os.path.join(self.output, 'sta.script')
                    sta_output = os.path.join(self.output, 'sta.out')
                    synth_input = os.path.join(self.output, self.modulename+'_syn.v')
                    self.delay = get_delay(self.path['OpenSTA'], sta_script, self.library, synth_input, self.modulename, sta_output)
                    power = get_power(self.path['OpenSTA'], sta_script, self.library, synth_input, self.modulename, sta_output, self.delay) 

                    os.remove(sta_script)
                    os.remove(sta_output)
                else:
                    self.delay = float('nan')
                    power = float('nan')

                f.write('{:<10}{:<15}{:<15}{:<15}\n'.format('Metric', 'Area(um^2)', 'Power(uW)', 'Delay(ns)') )
                f.write('{:<10.2f}{:<15.2f}{:<15.6f}{:<15.6f}\n'.format(0, self.initial_area, power, self.delay) )
            self.power_list.append(power)
            self.delay_list.append(self.delay)
            with open(os.path.join(self.output, 'result', 'iteration.csv'), 'a') as f:
                f.write('{},{},{},{},{},{}\n'.format('Iter','Metric', 'Area(um^2)', 'Power(uW)', 'Delay(ns)', 'Filename') )
                f.write('{},{:.6f},{:.2f},{:.6f},{:.6f},{}\n'.format('Org', 0, self.initial_area, power, self.delay,'Org') )

            with open(os.path.join(self.output, 'result', 'data.csv'), 'a') as f:
                f.write('{},{},{},{},{}\n'.format('Name','Metric', 'Area(um^2)', 'Power(uW)', 'Delay(ns)') )
                f.write('{},{:.6f},{:.2f},{:.6f},{:.6f}\n'.format('Org', 0, self.initial_area, power, self.delay) )



        print('Current stream of factorization degree:\n','\n'.join(map(str, self.curr_streams)))

        print('--------------- Iteration ' + str(self.iter) + ' ---------------')
        before = time.time()

        try:
            next_stream, streams, err, area, delay, power, name_list, rank = self.evaluate_iter(self.curr_streams, self.iter, step_size, parallel, threshold[0], least_error, cpu_count)
        except NoValidDesign:
            # If no more valid design
            a = np.array(self.area_list)
            e = np.array(self.error_list)
            a[e > threshold[0]] = np.inf
            idx = np.argmin(a)

            if idx == 0:
                source_file = os.path.join(self.output, self.modulename + '.v')
                source_file_syn = os.path.join(self.output, self.modulename + '_syn.v')
            else:
                source_file = os.path.join(self.output, 'tmp', '{}.v'.format(self.design_list[idx - 1]))
                source_file_syn = os.path.join(self.output, 'tmp', '{}_syn.v'.format(self.design_list[idx - 1]))

            target_file = os.path.join(self.output, 'result', '{}_{}.v'.format(self.modulename, 'REST'))
            target_file_syn = os.path.join(self.output, 'result', '{}_{}_syn.v'.format(self.modulename, 'REST'))
            shutil.copyfile(source_file, target_file)
            shutil.copyfile(source_file_syn, target_file_syn)

            with open(os.path.join(self.output, 'result', 'result.txt'), 'a') as f:
                f.write('{:<10.6f}{:<15.2f}{:<15.6f}{:<15.6f}\n'.format(self.error_list[idx], self.area_list[idx], self.power_list[idx], self.delay_list[idx]) )

            print('All subcircuits have been approximated to degree 1. Exit approximating.')
            return -1


        after = time.time()


        time_used = after - before
        print('--------------- Finishing Iteration' + str(self.iter) + '---------------')
        part_idx = list(np.nonzero(np.subtract(next_stream, self.curr_stream)))
        print('Partition', part_idx, 'being approximated')

        msg = 'Approximated error: {:.6f}%\tArea percentage: {:.6f}%\tTime used: {:.6f} sec\n'.format(100*err[rank[0]], 100 * area[rank[0]] / self.initial_area, time_used)
        print(msg)
        with open(os.path.join(self.output, 'log', 'blasys.log'), 'a') as log_file:
            log_file.write(str(next_stream))
            log_file.write('\n')
            log_file.write(msg)
        
        
        self.curr_streams = [streams[i] for i in rank[:track]]

            
        with open(os.path.join(self.output, 'result', 'iteration.csv'), 'a') as f:
            f.write('{},{:.6f},{:.2f},{:.6f},{:.6f},{}\n'.format(self.iter, err[rank[0]], area[rank[0]], power[rank[0]], delay[rank[0]], name_list[rank[0]]) )
        
        with open(os.path.join(self.output, 'result', 'data.csv'), 'a') as f:
            for i,n in enumerate(name_list):
                f.write('{},{:.6f},{:.2f},{:.6f},{:.6f}\n'.format(n, err[i], area[i], power[i], delay[i]) )

        self.iter += 1

        self.error_list += err
        self.area_list += area
        self.design_list += name_list
        self.power_list += power
        self.delay_list += delay

        self.iter_rank.append(rank[0])

        if err[rank[0]] >= threshold[0]+0.005:
            ts = threshold.pop(0)
            print('Reach threshold on', ts)
            a = np.array(self.area_list)
            e = np.array(self.error_list)
            a[e > ts] = np.inf
            idx = np.argmin(a)
            
            if idx == 0:
                source_file = os.path.join(self.output, self.modulename + '.v')
                source_file_syn = os.path.join(self.output, self.modulename + '_syn.v')
            else:
                source_file = os.path.join(self.output, 'tmp', '{}.v'.format(self.design_list[idx - 1]))
                source_file_syn = os.path.join(self.output, 'tmp', '{}_syn.v'.format(self.design_list[idx - 1]))

            target_file = os.path.join(self.output, 'result', '{}_{:%}.v'.format(self.modulename, ts))
            target_file_syn = os.path.join(self.output, 'result', '{}_{:%}_syn.v'.format(self.modulename, ts))
            shutil.copyfile(source_file, target_file)
            shutil.copyfile(source_file_syn, target_file_syn)
            with open(os.path.join(self.output, 'result', 'result.txt'), 'a') as f:
                f.write('{:<10.6f}{:<15.2f}{:<15.6f}{:<15.6f}\n'.format(self.error_list[idx], self.area_list[idx], self.power_list[idx], self.delay_list[idx]) )

        if len(threshold) == 0: 
            print('Reach error threshold. Exit approximation.')
            return -1
        
        
        self.plot(self.error_list, self.area_list)
        return 0


    def evaluate_iter(self, curr_k_streams, num_iter, step_size, parallel, threshold, least_error, cpu_count):
    
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

            # name_list += ['{}_{}-{}-{}'.format(self.modulename, num_iter, num_track, i) for i in range((len(k_lists_tmp)))]
        
            # Parallel mode
            if parallel:
                pool = mp.Pool(cpu_count)
                results = [pool.apply_async(evaluate_design,args=(k_lists_tmp[i], self, '{}_{}-{}-{}'.format(self.modulename, num_iter, num_track, i), False )) for i in range(len(k_lists_tmp))]
                pool.close()
                pool.join()
                for idx, result in enumerate(results):
                    res = result.get()
                    if res is None:
                        continue
                    err_list.append(res[0])
                    area_list.append(res[1])
                    delay_list.append(res[2])
                    power_list.append(res[3])
                    k_lists.append(k_lists_tmp[idx])
                    name_list.append('{}_{}-{}-{}'.format(self.modulename, num_iter, num_track, idx) )
            else:
            # Sequential mode
                for i in range(len(k_lists_tmp)):
                    # Evaluate each list
                    print('======== Design number ' + str(i))
                    k_stream = k_lists_tmp[i]
                    res = evaluate_design(k_stream, self, '{}_{}-{}-{}'.format(self.modulename, num_iter, num_track, i))
                    if res is None:
                        continue
                    err_list.append(res[0])
                    area_list.append(res[1])
                    delay_list.append(res[2])
                    power_list.append(res[3])

                    k_lists.append(k_stream)
                    name_list.append('{}_{}-{}-{}'.format(self.modulename, num_iter, num_track, i) )

            # k_lists += k_lists_tmp
        
        if len(name_list) == 0:
            raise NoValidDesign()

        if least_error:
            rank = least_error_opt(np.array(err_list), np.array(area_list) / self.initial_area, threshold)
        else:
            rank = optimization(np.array(err_list), np.array(area_list), self.initial_area, self.error_list[self.iter_rank[-1]], self.area_list[self.iter_rank[-1]], threshold+0.01)
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
        ax.scatter(error_np, area_np, c='b', s=3)
        # plt.plot(error_np, area_np, c='b', linewidth=3)
        #plt.xlim(0,1.0)
        #plt.ylim(0,1.1)
        ax.set_ylabel('Area ratio (%)')
        ax.set_xlabel('HD Approximation Error (%)')
        #ax.set(xlim=(1e-5, 1e2), ylim=(.0, 120.0))
        #plt.xticks(np.arange(0,1,0.1))
        #plt.yticks(np.arange(0,1.1,0.1))
        ax.set_title('Greedy search on ' + self.modulename)
        ax.set_xscale('log')
        fig.savefig(os.path.join(self.output, 'metric-error.png'))
        
        fig.clf()



