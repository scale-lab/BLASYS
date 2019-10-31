from cmd import Cmd
import os
import yaml
import shutil
from utils.greedyWorker import GreedyWorker, print_banner
from utils.create_tb import create_testbench

class Blasys(Cmd):
    prompt = 'blasys> '
    liberty = None
    optimizer = None
    input_file = None
    output = None
    
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



    def do_create_dir(self, args):
        if self.input_file is None:
            print('[Error] Please first specify input verilog by command read_verilog.')
            return

        # Check existence of output directory
        print('Create output folder', args)
        if os.path.isdir(args):
            a = input('Output path already exists. Delete current directory? (Y/N)')
            if a.lower() == 'n':
                print('To change output folder, please run command output_dir.')
                return
            if a.lower() != 'y':
                print('[Error] Sorry I don\'t understand. Please try again.\n')
                return
            else:
                shutil.rmtree(args)
       
        self.optimizer.create_output_dir(args)

        self.output = args
        print('Successfully create output folder', args)


    def help_create_dir(self):
        print('[Usage] output_dir OUTPUT_DIRECTORY')



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
            # Check existence of testbench file
            if not os.path.exists(args_list[2]) or os.path.isdir(args_list[2]):
                print('[error] cannot find testbench file', args_list[2])
                return
            testbench_file = args_list[2]
        else:
            testbench_file = 'tb.v'
            with open(testbench_file, 'w') as f:
                create_testbench(input_file, 5000, f)

        # Load path to executable
        app_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(app_path, 'config', 'params.yml'), 'r') as config_file:
            config = yaml.safe_load(config_file)
        config['part_config'] = os.path.join(app_path, 'config', 'test.ini')

        self.optimizer = GreedyWorker(input_file, testbench_file, self.liberty, config)
        self.input_file = input_file
        print('Successfully loaded input file and created optimizer.\n')

    def help_read_verilog(self):
        print('[Usage] read_verilog INPUT_FILE_PATH [-tb TESTBENCH_PATH]')


    def do_partitioning(self, args):
        if self.input_file is None:
            print('[Error] No input file. Please first specify an input verilog file.\n')
            return

        if self.output is None:
            print('[Error] No output folder. Please first create output folder by command create_dir.')
            return
        # Parse arguments
        if not args.isdigit():
            print('[Error] Please specify an integer.')
            return           

        
        self.optimizer.evaluate_initial()
        self.optimizer.recursive_partitioning(int(args))


    def help_partitioning(self):
        print('[Usage] partitioning NUMBER_OF_PARTITIONS')

    
    def do_greedy(self, args):
        pass      
        

    def help_greedy(self):
        print('greedy')





if __name__ == '__main__':
    print_banner()
    Blasys().cmdloop()
