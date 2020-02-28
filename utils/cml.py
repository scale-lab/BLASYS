from cmd import Cmd
import os
import yaml
import glob
import regex as re
import shutil
import numpy as np
import readline
import time
import subprocess
import multiprocessing as mp
from .banner import print_banner
from .greedyWorker import GreedyWorker
from .create_tb import create_testbench
from .utils import module_info, number_of_cell, synth_design, get_power, get_delay
from . import metric



def _complete_path(path):
    if os.path.isdir(path):
        return glob.glob(os.path.join(path, '*'))
    else:
        return glob.glob(path+'*')

class Blasys(Cmd):
    prompt = 'blasys> '

    def __init__(self):
        super().__init__()
        self.liberty = None
        self.reset()
        readline.set_completer_delims(' \t\n')


    def reset(self):
        self.optimizer = None
        self.input_file = None
        self.testbench = None
        self.output = None
        self.partitioned = False
        self.initialized = False

        self.modulename = None
        self.n_input = None
        self.n_output = None
        self.n_cell = None

        self.parallel = False
        self.cpu = mp.cpu_count()
        self.sta = False
        self.metric = 'HD'

    
    def do_exit(self, args):
        print('Blasys exit. Bye.')
        return True

    def help_exit(self):
        print('Exit blasys tool.')


    def do_output_to(self, args):
        arg_list = args.split()
        if len(arg_list) != 1:
            print('[Error] Invalid input.')
            self.help_output_to()

        self.output = arg_list[0]
        print('Set output directory to {}.\n'.format(self.output))

    def help_output_to(self):
        print('[Usage] output_to DIRECTORY_OF_OUTPUT')




    def do_read_liberty(self, args):
        
        if not os.path.exists(args) or os.path.isdir(args):
            print('[Error] Cannot find liberty file', args)
            self.help_read_liberty()
            return

        # if self.liberty is not None:
            # print('[Error] Already loaded liberty file.')
            # return
        
        print('Successfully loaded liberty file {}.\n'.format(args))
        self.liberty = args
        if self.optimizer is not None:
            self.optimizer.library = args


    def complete_read_liberty(self, text, line, start_idx, end_idx):
        return _complete_path(text)


    def help_read_liberty(self):
        print('[Usage] read_liberty PATH_OF_LIBERTY\n')




    def do_read_verilog(self, args):
        
        # Check existence of input file
        if not os.path.exists(args) or os.path.isdir(args):
            print('[Error] cannot find input file', args)
            self.help_read_verilog()
            return        
        input_file = args

        # Load path to executable
        app_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(app_path, '..', 'config', 'params.yml'), 'r') as config_file:
            config = yaml.safe_load(config_file)
        config['part_config'] = os.path.join(app_path, '..', 'config', 'test.ini')

        # Initial BLASYS
        self.optimizer = GreedyWorker(input_file, self.liberty, config, None, self.metric, self.sta)
        self.input_file = input_file
        ret = module_info(input_file, config['yosys'])
        self.n_cell = number_of_cell(input_file, config['yosys'])
        self.modulename, self.n_input, self.n_output = ret[0], ret[3], ret[5]
        print('Successfully loaded input file and created optimizer.\n')

        #respond = input('Please specify output folder (by default \'output\'):  ')
        #if respond == '':
        #    respond = 'output'

        #while 1:
        #    print('Create output folder', respond)
        #    if os.path.isdir(respond):
        #        a = input('Output path already exists. Delete current directory? (Y/N):  ')
        #        if a.lower() == 'y':
        #            shutil.rmtree(respond)
        #            break
        #    else:
        #        break

        #    respond = input('Please specify output folder (by default \'output\'):  ')
        #    if respond == '':
        #        respond = 'output'

        # Create output dir
        self.optimizer.create_output_dir(self.output)
        print('\n')
        # self.evaluate_initial()
        # self.output = respond

    def complete_read_verilog(self, text, line, start_idx, end_idx):
        return _complete_path(text)

    def help_read_verilog(self):
        print('[Usage] read_verilog INPUT_FILE_PATH\n')





    def do_read_testbench(self, args):    
        if self.optimizer is None:
            print('[Error] Please first read input Verilog.\n')
            return
        # Check existence of testbench
        if not os.path.exists(args) or os.path.isdir(args):
            print('[Error] cannot find testbench file', args)
            self.help_read_testbench()
            return        
        self.testbench = args
        self.optimizer.testbench = self.testbench
        print('Successfully read testbench file.\n')

    def complete_read_testbench(self, text, line, start_idx, end_idx):
        return _complete_path(text)

    def help_read_testbench(self):
        print('[Usage] read_testbench TESTBENCH_PATH\n')




    def do_sta(self, args):

        # If turn on sta, user must provide liberty file.
        if args == 'on':
            if self.liberty is None:
                print('[Error] No liberty file found. Please first run read_liberty.\n')
                return
            self.sta = True
            if self.optimizer is not None:
                self.optimizer.sta = True
            print('Turn on OpenSTA. Evaluate power and delay.\n')
        elif args == 'off':
            self.sta = False
            if self.optimizer is not None:
                self.optimizer.sta = False
            print('Turn off OpenSTA. Only evaluate area.\n')
        else:
            print('[Error] Invalid arguments.')
            self.help_sta()

    def help_sta(self):
        print('[Usage] sta on/off\n')
    

    
    def do_parallel(self, args):
        args_list = args.split()

        if args_list[0] == 'off':
            self.parallel = False
            print('Turn off parallel mode.\n')
            return

        elif args_list[0] == 'on':

            if len(args_list) == 1:
                self.parallel = True
                print('Turn on parallel mode.\n')
                return

            if len(args_list) == 3 and args_list[1] == '-cpu':
                self.parallel = True
                cpu_set = int(args_list[2])
                if cpu_set > self.cpu:
                    print('Turn on parallel mode.')
                    print('However, there are only {} available cores.'.format(self.cpu))
                    print('Number of cores using: {}\n'.format(self.cpu))
                    return
                else:
                    print('Turn on parallel mode.')
                    self.cpu = cpu_set
                    print('Number of cores using: {}\n'.format(self.cpu))
                    return

        print('[Error] Invalid arguments.')
        self.help_parallel()


    def help_parallel(self):
        print('[Usage] To turn off parallel mode, type:')
        print('        parallel off')
        print('        To turn on parallel mode, type:')
        print('        parallel on [-cpu NUMBER_OF_CORES]\n')



    def do_metric(self, args):

        # if self.optimizer is None:
            # print('[Error] No input file found. Please first run read_verilog.\n')
            # return

        if not hasattr(metric, args):
            print('[Error] Cannot find metric function {} within utils/metric.py.')
            self.help_metric()
            return

        if self.optimizer is not None:
            self.optimizer.metric = getattr(metric, args)
        self.metric = args

        print('Successfully set error metric as {}\n'.format(args))

    def help_metric(self):
        print('[Usage] metric ERROR_METRIC\n')







    def do_partition(self, args):
        if self.partitioned:
            print('[Error] Ciruit already partitioned.\n')
            return

        if self.optimizer is None:
            print('[Error] No input file found. Please first run read_verilog.\n')
            return

        if not (args.isdigit() or args == ''):
            print('[Error] Please put an integer as number of partitions.')
            self.help_partition()
            return

        if args == '':
            num_part = None
        else:
            num_part = int(args)
     
        self.optimizer.convert2aig()

        if num_part is None:
            self.optimizer.recursive_partitioning()
        else:
            self.optimizer.recursive_partitioning(num_part)

        self.partitioned = True
        print('\n')


    def help_partition(self):
        print('[Usage] partition [NUMBER_OF_PARTITIONS]\n')

    






    def do_blasys(self, args):
        if self.testbench is None:
            print('[Error] No testbench found. Please first run read_testbench.\n')
            return

        if not self.initialized:
            self.initialized = True
            self.optimizer.evaluate_initial()
        
        if not self.partitioned and self.n_input <= 16:
            self.optimizer.blasys()
            print('Finish.\n')
            return

        if not self.partitioned:
            print('[Error] Input circuit is too big. Please first partition by command partition.\n')
            return

        args_list = args.split()

        if '-tr' in args_list:
            idx = args_list.index('-tr')
            if idx == len(args_list) - 1:
                print('[Error] Please specify number of track.')
                self.help_greedy()
                return
            if not args_list[idx+1].isdigit():
                print('[Error] Please put integer as number of track.')
                self.help_greedy()
                return
            track = int(args_list[idx+1])
            args_list.pop(idx)
            args_list.pop(idx)
        else:
            track = 3

        if '-ts' in args_list:
            idx = args_list.index('-ts')
            if idx == len(args_list) - 1:
                print('[Error] Please put float-point threshold.')
                self.help_greedy()
                return

            # if not args_list[idx+1].replace('.', '', 1).replace(',', '').isdigit():
                # print('[Error] Please put float-point digits as threshold.')
                # self.help_greedy()
                # return

            # Get threshold
            threshold = args_list[idx+1]
            threshold_list = list(map(float, threshold.split(',')))
            args_list.pop(idx)
            args_list.pop(idx)
        else:
            threshold_list = [np.inf]

        if '-s' in args_list:
            idx = args_list.index('-s')
            if idx == len(args_list) - 1:
                print('[Error] Please put integer as step size.')
                self.help_greedy()
                return

            if not args_list[idx+1].isdigit():
                print('[Error] Please put integer as step size.')
                self.help_greedy()
                return

            # Get threshold
            stepsize = int(args_list[idx+1])
            args_list.pop(idx)
            args_list.pop(idx)
        else:
            stepsize = 1

        # Call greedy_opt
        self.optimizer.greedy_opt(self.parallel, self.cpu, stepsize, threshold_list, track=track)


    def help_blasys(self):
        print('[Usage] blasys [-ts THRESHOLDS] [-s STEP_SIZE] [-tr NUMBER_TRACK]\n')

    def do_run_iter(self, args):

        if not self.partitioned:
            print('[Error] Circuit has not been partitioned yet.')
            return

        if self.testbench is None:
            print('[Error] No testbench found. Please first run read_testbench.\n')
            return

        if not self.initialized:
            self.initialized = True
            self.optimizer.evaluate_initial()

        args_list = args.split()

        if '-ts' in args_list:
            idx = args_list.index('-ts')
            if idx == len(args_list) - 1:
                print('[Error] Please put float-point threshold.')
                self.help_greedy()
                return

            # if not args_list[idx+1].replace('.', '', 1).isdigit():
                # print('[Error] Please put float-point threshold.')
                # self.help_greedy()
                # return

            # Get threshold
            # threshold = float(args_list[idx+1])
            # args_list.pop(idx)
            # args_list.pop(idx)
            threshold = args_list[idx+1]
            threshold_list = list(map(float, threshold.split(',')))
            args_list.pop(idx)
            args_list.pop(idx)

        else:
            threshold_list = [np.inf]

        if '-tr' in args_list:
            idx = args_list.index('-tr')
            if idx == len(args_list) - 1:
                print('[Error] Please specify number of track.')
                self.help_greedy()
                return
            if not args_list[idx+1].isdigit():
                print('[Error] Please put integer as number of track.')
                self.help_greedy()
                return
            track = int(args_list[idx+1])
            args_list.pop(idx)
            args_list.pop(idx)
        else:
            track = 3

        if '-s' in args_list:
            idx = args_list.index('-s')
            if idx == len(args_list) - 1:
                print('[Error] Please put integer as step size.')
                self.help_greedy()
                return

            if not args_list[idx+1].isdigit():
                print('[Error] Please put integer as step size.')
                self.help_greedy()
                return

            stepsize = int(args_list[idx+1])
            args_list.pop(idx)
            args_list.pop(idx)
        else:
            stepsize = 1

        if '-i' in args_list:
            idx = args_list.index('-i')
            if idx == len(args_list) - 1:
                print('[Error] Please put integer as number of iteration.')
                self.help_run_iter()
                return

            if not args_list[idx+1].isdigit():
                print('[Error] Please put integer as number of iteration.')
                self.help_run_iter()
                return

            iteration = int(args_list[idx+1])
            args_list.pop(idx)
            args_list.pop(idx)
        else:
            iteration = 1

        # Call greedy_opt
        for i in range(iteration):
            if self.optimizer.next_iter(self.parallel, self.cpu, stepsize, threshold_list, track=track) == -1:
                print('You have either reached error threshold or all partitions reached factorization degree 1.')
                return

    def help_run_iter(self):
        print('[Usage] run_iter [-i NUMBER_ITERATION] [-ts THRESHOLDS] [-tr NUMBER_TRACK] [-s STEPSIZE]\n')

    def do_clear(self, args):
        a = input('Are you sure to clear?\nDoing this will clear ALL approximate work done in this session. (Y/N)')
        if a.lower() == 'n':
            return
        if a.lower() != 'y':
            print('[Error] Sorry I don\'t understand. Please try again.\n')
            return
        # self.optimizer = None
        # self.input_file = None
        # self.output = None
        # self.partitioned = False
        # self.testbench = None
        self.reset()

    def help_clear(self):
        print('[Usage] Clear ALL approximate work done in this session. Be careful to use it.\n')




    def do_stat(self, args):
        arg_list = args.split()

        if len(arg_list) == 0:
            metric_list = []
            area_list = []
            power_list = []
            delay_list = []
            name_list = []
            with open(os.path.join(self.optimizer.output, 'result', 'iteration.csv')) as data:
                line = data.readline()
                line = data.readline().rstrip('\n')
                while line:
                    tokens = re.split(',',line)
                    metric_list.append(float(tokens[1]))
                    area_list.append(float(tokens[2]))
                    name_list.append(tokens[5])
                    if tokens[3] == 'nan':
                        power_list.append('nan')
                        delay_list.append('nan')
                    else:
                        power_list.append(float(tokens[3]))
                        delay_list.append(float(tokens[4]))
                    #err = float(tokens[0])
                    #area = float(tokens[1])
                    #error_list.append(err)
                    #area_list.append(area)
                    line = data.readline().rstrip('\n')
            
            print('{:<12}{:<20}{:<12}{:<12}{:<12}{:<12}\n'.format('Iteration', 'Design' ,'Metric', 'Area(um^2)', 'Power(uW)', 'Delay(ns)'))
            for i, ( m, a, p, d, design ) in enumerate(zip(metric_list, area_list, power_list, delay_list, name_list)):
                if i == 0:
                    it = 'Original'
                else:
                    it = i - 1

                if p != 'nan':
                    print('{:<12}{:<20}{:<12.4%}{:<12.4f}{:<12.4f}{:<12.4f}\n'.format(it, design, m, a, p, d))
                else:
                    print('{:<12}{:<20}{:<12.4%}{:<12.4f}{:<12}{:<12}\n'.format(it, design, m, a, 'nan', 'nan'))

        else:
            with open(os.path.join(self.optimizer.output, 'result', 'data.csv')) as data:
                line = data.readline()
                line = data.readline().rstrip('\n')
                while line:
                    tokens = re.split(',', line)
                    if tokens[0] == args.strip():
                        print('*'*15 + ' ' + args + ' ' + '*'*15)
                        print('QoR:\t{:.4%}'.format(float(tokens[1])))
                        print('Area:\t{:.2f}'.format(float(tokens[2])))
                        if tokens[3] != 'nan':
                            print('Power:\t{:.6f}'.format(float(tokens[3])))
                            print('Delay:\t{:.6f}'.format(float(tokens[4])))
                        return
                    line = data.readline()

            print('[Error] Cannot find design {}.'.format(args))
            self.help_stat()
            

    def help_stat(self):
        print('Show best approximate results per iteration.')
        print('If a design name is provided, only information about it will be provided.\n')



    def do_evaluate(self, args):
        if not os.path.exists(args) or os.path.isdir(args):
            print('[Error] Cannot find verilog file', args)
            self.help_read_liberty()
            return

        if self.optimizer is None:
            print('[Error] Please first read an input design by read_verilog.\n')
            return
        
        if self.testbench is None:
            print('[Error] Please first read a testbench by read_testbench.\n')
            return

        ret = module_info(args, self.optimizer.path['yosys'])

        if not (ret[0] == self.modulename and ret[3] == self.n_input and ret[5] == self.n_output):
            print('[Error] Different design from input verilog.')
            print('        Please check module name, number of inputs and outputs.\n')
            return

        folder = 'tmp' + time.strftime('_%Y%m%d-%H%M%S')
        os.mkdir(folder)

        # Synthesize and estimate chip area
        org_output_syn = os.path.join(folder, 'original')
        org_area  = synth_design(self.input_file, org_output_syn, self.liberty, self.optimizer.script, self.optimizer.path['yosys'])

        try:
            output_syn = os.path.join(folder, 'design')
            area  = synth_design(args, output_syn, self.liberty, self.optimizer.script, self.optimizer.path['yosys'])
        except CombinationalLoop:
            print('[Error] Combinational loop detected in approximate design.\n')
            return

        print('********** Design Area **********')
        print('Original input: {}'.format(org_area))
        print('Approx design:  {}'.format(area))
        print('\n')

        # QoR estimation
        app_truth_dir = os.path.join(folder, 'approx.truth')
        subprocess.call([self.optimizer.path['iverilog'], '-o', app_truth_dir[:-5]+'iv', args, self.testbench])
        with open(app_truth_dir, 'w') as f:
            subprocess.call([self.optimizer.path['vvp'], app_truth_dir[:-5]+'iv'], stdout=f)
        os.remove(app_truth_dir[:-5] + 'iv')

        org_truth_dir = os.path.join(folder, 'origin.truth')
        subprocess.call([self.optimizer.path['iverilog'], '-o', org_truth_dir[:-5]+'iv', self.input_file, self.testbench])
        with open(org_truth_dir, 'w') as f:
            subprocess.call([self.optimizer.path['vvp'], org_truth_dir[:-5]+'iv'], stdout=f)
        os.remove(org_truth_dir[:-5] + 'iv')

        err = self.optimizer.metric(org_truth_dir, app_truth_dir)
        print('********** QoR **********')
        print('{}: {:.6%}'.format(self.metric, err))
        print('\n')
    
        if self.sta:
            # Estimate orignal time and power
            sta_script = os.path.join(folder, 'sta.script')
            sta_output = os.path.join(folder, 'sta.out')
            org_delay = get_delay(self.optimizer.path['OpenSTA'], sta_script, self.liberty, org_output_syn+'_syn.v', self.modulename, sta_output)
            org_power = get_power(self.optimizer.path['OpenSTA'], sta_script, self.liberty, org_output_syn+'_syn.v', self.modulename, sta_output, org_delay)
            delay = get_delay(self.optimizer.path['OpenSTA'], sta_script, self.liberty, output_syn+'_syn.v', self.modulename, sta_output)
            power = get_power(self.optimizer.path['OpenSTA'], sta_script, self.liberty, output_syn+'_syn.v', self.modulename, sta_output, org_delay)
            os.remove(sta_script)
            os.remove(sta_output)
            print('********** Power Consumption **********')
            print('Original input: {}'.format(org_power))
            print('Approx design:  {}'.format(power))
            print('\n') 
            print('********** Circuit Delay **********')
            print('Original input: {}'.format(org_delay))
            print('Approx design:  {}'.format(delay))
            print('\n')




        

    def help_evaluate(self):
        print('[Usage] evaluate VERILOG_FILE')
        print('Evaluate a customized design.\n')




    def tmp1(self, args):
        # Call blasys
        if self.input_file is None:
            print('[Error] No input file. Please first specify an input verilog file.\n')
            return
        args_list = args.split()
        if '-w' in args_list:
            weight = True
        else:
            weight = False
        self.optimizer.blasys(weight)



    def tmp2(self):
        print('[Usage] blasys [-w]')
        print('Run BMF on truthtable WITHOUT partitioning')






if __name__ == '__main__':
    print_banner()
    Blasys().cmdloop()
