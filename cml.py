from cmd import Cmd
import os
import yaml
import regex as re
import shutil
import numpy as np
from utils.banner import print_banner
from utils.greedyWorker import GreedyWorker
from utils.create_tb import create_testbench

class Blasys(Cmd):
    prompt = 'blasys> '


    def __init__(self):
        super().__init__()
        self.liberty = None
        self.optimizer = None
        self.input_file = None
        self.output = None
        self.partitioned = False
        self.testbench = None
    
    def do_exit(self, args):
        print('Bye.')
        return True

    def help_exit(self):
        print('Exit blasys tool.')

    def do_read_liberty(self, args):
        
        if not os.path.exists(args) or os.path.isdir(args):
            print('[Error] Cannot find liberty file', args)
            self.help_read_liberty()
            return

        if self.liberty is not None:
            print('[Error] Already loaded liberty file.')
            return
        
        print('Successfully loaded liberty file.\n') 
        self.liberty = args


    def help_read_liberty(self):
        print('[Usage] read_liberty PATH_OF_LIBERTY')

    def do_read_verilog(self, args):
        if self.liberty is None:
            print('[Error] No liberty file loaded. Please load liberty file by command read_liberty.')
            return

        args_list = args.split()
        if not ( len(args_list) == 1 or (len(args_list) == 3 and args_list[1] == '-tb') ):
            print('[Error] Invalid arguments.')
            self.help_read_verilog()
            return
        
        # Check existence of input file
        if not os.path.exists(args_list[0]) or os.path.isdir(args_list[0]):
            print('[Error] cannot find input file', args_list[0])
            return        
        input_file = args_list[0]
 
        if len(args_list) == 3:
            self.testbench = int(args_list[2])

        # Load path to executable
        app_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(app_path, 'config', 'params.yml'), 'r') as config_file:
            config = yaml.safe_load(config_file)
        config['part_config'] = os.path.join(app_path, 'config', 'test.ini')

        self.optimizer = GreedyWorker(input_file, self.liberty, config, None)
        self.input_file = input_file
        print('Successfully loaded input file and created optimizer.\n')

        respond = input('Please specify output folder (by default \'output\') ')
        if respond == '':
            respond = 'output'

        while 1:
            print('Create output folder', respond)
            if os.path.isdir(respond):
                a = input('Output path already exists. Delete current directory? (Y/N)')
                if a.lower() == 'y':
                    shutil.rmtree(respond)
                    break
            else:
                break

            respond = input('Please specify output folder (by default \'output\') ')
            if respond == '':
                respond = 'output'

        # Create output dir
        self.optimizer.create_output_dir(respond)
        self.evaluate_initial()
        self.output = respond



    def help_read_verilog(self):
        print('[Usage] read_verilog INPUT_FILE_PATH [-tb NUM_TEST_VECTOR]')


    def do_partitioning(self, args):
        if self.partitioned:
            print('[Error] Ciruit already partitioned.\n')
            return

        if self.input_file is None:
            print('[Error] No input file. Please first specify an input verilog file.\n')
            return

        args_list = args.split()
        if '-n' in args_list:
            idx = args_list.index('-n')
            if idx == len(args_list) - 1:
                print('[Error] Please put number of partitions.')
                self.help_partitioning()
                return

            if not args_list[idx+1].isdigit():
                print('[Error] Please put an integer as number of partitions.')
                self.help_partitioning()
                return

            # Get threshold
            num_part = int(args_list[idx+1])
            args_list.pop(idx)
            args_list.pop(idx)
        else:
            num_part = None
     
        self.optimizer.convert2aig()

        if num_part is None:
            self.optimizer.recursive_partitioning()
        else:
            self.optimizer.recursive_partitioning(num_part)

        self.partitioned = True
        print('\n')


    def help_partitioning(self):
        print('[Usage] partitioning [-n NUMBER_OF_PARTITIONS]')

    
    def do_greedy(self, args):
        if not self.partitioned:
            print('[Error] Circuit has not been partitioned yet.')
            return

        args_list = args.split()
        if '-p' in args_list:
            parallel = True
            args_list.remove('-p')
        else:
            parallel = False

        if '-w' in args_list:
            weighted = True
            args_list.remove('-w')
        else:
            weighted = False

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
        self.optimizer.greedy_opt(parallel, stepsize, threshold_list, weighted, track=track)


    def help_greedy(self):
        print('greedy [-ts THRESHOLD] [-s STEP_SIZE] [-tr NUMBER_TRACK] [-p] [-w]')

    def do_run_iter(self, args):
        if not self.partitioned:
            print('[Error] Circuit has not been partitioned yet.')
            return

        args_list = args.split()
        if '-p' in args_list:
            parallel = True
            args_list.remove('-p')
        else:
            parallel = False

        if '-w' in args_list:
            weighted = True
            args_list.remove('-w')
        else:
            weighted = False

        if '-ts' in args_list:
            idx = args_list.index('-ts')
            if idx == len(args_list) - 1:
                print('[Error] Please put float-point threshold.')
                self.help_greedy()
                return

            if not args_list[idx+1].replace('.', '', 1).isdigit():
                print('[Error] Please put float-point threshold.')
                self.help_greedy()
                return

            # Get threshold
            threshold = float(args_list[idx+1])
            args_list.pop(idx)
            args_list.pop(idx)
        else:
            threshold = np.inf

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
            if self.optimizer.next_iter(parallel, stepsize, [threshold], use_weight=weighted, track=track) == -1:
                print('You have either reached error threshold or all partitions reached factorization degree 1.')
                return

    def help_run_iter(self):
        print('[Usage] run_iter [-i NUMBER_ITERATION] [-ts THRESHOLD] [-tr NUMBER_TRACK] [-s STEPSIZE] [-p] [-w]')

    def do_clear(self, args):
        a = input('Are you sure to clear?\nDoing this will clear ALL approximate work done in this session. (Y/N)')
        if a.lower() == 'n':
            return
        if a.lower() != 'y':
            print('[Error] Sorry I don\'t understand. Please try again.\n')
            return
        self.optimizer = None
        self.input_file = None
        self.output = None
        self.partitioned = False
        self.testbench = None

    def help_clear(self):
        print('[Usage] Clear ALL approximate work done in this session. Be careful to use it.')

    def do_display_result(self, args):
        hd_list = []
        mae_list = []
        mae_p_list = []
        area_list = []
        power_list = []
        delay_list = []
        with open(os.path.join(self.output,'data.csv')) as data:
            line = data.readline()
            line = data.readline().rstrip('\n')
            while line:
                tokens = re.split(',',line)
                hd_list.append(float(tokens[1]))
                mae_list.append(float(tokens[2]))
                mae_p_list.append(float(tokens[3]))
                area_list.append(float(tokens[4]))
                power_list.append(float(tokens[5]))
                delay_list.append(float(tokens[6]))
                #err = float(tokens[0])
                #area = float(tokens[1])
                #error_list.append(err)
                #area_list.append(area)
                line = data.readline().rstrip('\n')
        
        print('{:<12}{:<12}{:<12}{:<12}{:<12}{:<12}{:<12}\n'.format('Iteration', 'HD Error', 'MAE', 'MAE%', 'Area(um^2)', 'Power(uW)', 'Delay(ns)'))
        for i, ( hd, mae, mae_p, a, p, d ) in enumerate(zip(hd_list, mae_list, mae_p_list, area_list, power_list, delay_list)):
            if i == 0:
                it = 'Original'
            else:
                it = i - 1
            print('{:<12}{:<12.4f}{:<12.4f}{:<12.4f}{:<12.4f}{:<12.4f}{:<12.4f}\n'.format(it, hd, mae, mae_p, a, p, d))

    def help_display_result(self):
        print('Show approximate result.')



    def evaluate_initial(self):
        if self.testbench is None:
            self.optimizer.evaluate_initial()
        else:
            self.optimizer.evaluate_initial(self.testbench)
        # self.optimizer.convert2aig()

    def do_blasys(self, args):
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



    def help_blasys(self):
        print('[Usage] blasys [-w]')
        print('Run BMF on truthtable WITHOUT partitioning')






if __name__ == '__main__':
    print_banner()
    Blasys().cmdloop()
