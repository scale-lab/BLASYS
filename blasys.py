from cmd import Cmd
import os
from utils.greedyWorker import GreedyWorker, print_banner
from utils.create_tb import create_testbench

class Blasys(Cmd):
    prompt = 'blasys> '
    liberty = None
    optimizer = None
    
    def do_exit(self, args):
        print('Bye.')
        return True

    def help_exit(self):
        print('Exit blasys tool.')

    def do_read_liberty(self, args):
        args_list = args.split()
        if len(args_list) != 2:
            print('[Error] Invalide arguments.')
            self.help_read_liberty()
            return
        
        if not os.path.exists(args_list[0]) or os.path.isdir(args_list[0]):
            print('[Error] Cannot find liberty file', args_list[0])
            return

        if self.liberty is not None:
            print('[Error] Already loaded liberty file.')
            return
        
        self.liberty = args_list[0]


    def help_read_liberty(self, args):
        print('[Usage] read_liberty [path_to_liberty_file]')


    def do_read_verilog(self, args):
        args_list = args.split()
        if not ( len(args_list) == 1 or (len(args_list) == 3 and args_list[1] == '-t') ):
            print('[Error] Invalid arguments.')
            self.help_read_verilog()
            return
        
        if self.liberty is None:
            print('[Error] No liberty file loaded. Please load liberty file first.')

        # Check existence of input file
        if not os.path.exists(args_list[0]) or os.path.isdir(args_list[0]):
            print('[error] cannot find input file', args_list[0])
            return        
        input_file = args_list[0]
        
        # Get modulename
        modulename = None
        with open(input_file) as f:
            line = f.readline()
            while line:
                tokens = re.split('[ (]', line)
                for i in range(len(tokens)):
                    if tokens[i] == 'module':
                        modulename = tokens[i+1]
                        break
                line = f.readline()

        if modulename is None:
            print('[Error] Cannot parse input file.')
            return

        if len(args_list) == 3:
            # Check existence of testbench file
            if not os.path.exists(args_list[2]) or os.path.isdir(args_list[2]):
                print('[error] cannot find testbench file', args_list[2)
                return
            testbench_file = args_list[2]
        else:
            testbench_file = modulename + '_tb.v'
            with open(testbench_file, 'w') as f:
                create_testbench()



        
    
    
    def help_read_verilog(self):
        print('[Usage] read_verilog INPUT_FILE_PATH [-t TESTBENCH_PATH]')


    def do_partitioning(self, args):
        if self.verilog is None:
            print('[Error] No input file. Please first specify an input verilog file.\n')
            return

        command_list = args.split()
        # Check input arguments
        if len(command_list) != 2 or not command_list[0].isdigit():
            print('[Error] Input arguments are wrong!')
            self.help_partitioning()
            return

        # Check existence of output directory
        if os.path.isdir(command_list[1]):
            a = input('Output path already exists. Delete current directory? (Y/N)')
            if a.lower() == 'n':
                return
            if a.lower() != 'y':
                print('[Error] Sorry I don\'t understand. Please try again.\n')
                return
            else:
                shutil.rmtree(command_list[1])

        print('Create output path and partition with LSOracle ...')
        # Create output dir
        os.mkdir(command_list[1])
        partition_dir = os.path.join(command_list[1], 'partition')
        os.mkdir(partition_dir)

        os.mkdir(os.path.join(command_list[1], 'approx_design'))
        os.mkdir(os.path.join(command_list[1], 'truthtable'))
        # Call LSOracle to partition
        lsoracle_command = 'read_verilog ' + self.verilog + ';' \
                'partitioning ' + command_list[0] + '; get_all_partitions ' + partition_dir
        f = open(os.path.join(command_list[1], 'lsoracle.log'), "w")
        subprocess.call(['lstools', '-c', lsoracle_command], stdout=f, stderr=subprocess.STDOUT)
        f.close()

        # Check input and output
        num_part = int(command_list[0])
        input_list = []
        output_list = []

        for i in range(num_part):
            file_path = os.path.join(partition_dir, self.modulename + '_' + str(i))
            if not os.path.exists(file_path + '.v'):
                input_list.append(-1)
                output_list.append(-1)
                continue
            inp, out = inpout(file_path)
            input_list.append(inp)
            output_list.append(out)

        print('Input numbers:  ' + str(input_list))
        print('Output numbers: ' + str(output_list))
        print('Max input number: {}\n'.format(max(input_list)))

        respond = input('Okay with the partitioning? (Y/N) ')
        if respond.lower() == 'n':
            shutil.rmtree(command_list[1])
            self.output_dir = None
            return
        
        self.output_dir = command_list[1]
        self.input_list = input_list
        self.output_list = output_list
        # Generate truth table and benchmarks for each partition
        print('Generate benchmark and truthtable for each partition ...')
        for i in range(num_part):
            submodname = self.modulename + '_' + str(i)
            file_path = os.path.join(partition_dir, submodname)
            if not os.path.exists(file_path + '.v'):
                continue

            # Create testbench for partition
            print('Create testbench for partition '+str(i))
            n, m = gen_truth(file_path, submodname)

            # Generate truthtable
            print('Generate truth table for partition '+str(i))
            part_output_dir = os.path.join(command_list[1], submodname)
            os.mkdir(part_output_dir)
            subprocess.call(['iverilog', '-o', file_path+'.iv', file_path+'.v', file_path+'_tb.v'])
            truth_dir = os.path.join(part_output_dir, submodname + '.truth')
            #subprocess.call(['vvp', file_path+'.iv > ' + truth_dir])
            os.system('vvp ' + file_path + '.iv > ' + truth_dir)

        print('Simulate truth table on input design...')
        os.system('iverilog -o '+ self.modulename + '.iv ' + self.verilog + ' ' + self.testbench )
        output_truth = os.path.join(self.output_dir, self.modulename+'.truth')
        os.system('vvp ' + self.modulename + '.iv > ' + output_truth)
        os.system('rm ' + self.modulename + '.iv')

        area = synth_design(self.verilog, os.path.join(self.output_dir, self.modulename+'_syn'), 'asap7.lib', '')
        print('Initial chip area: {:.6f}\n'.format(area))
        self.input_area = area


    def help_partitioning(self):
        print('[Usage] partitioning NUMBER_OF_PARTITIONS OUTPUT_DIRECTORY')


    def do_blasys(self, args):
        arg_list = re.split('[ ,]', args)
        for i in range(len(arg_list)):
            arg_list[i] = int(arg_list[i])
        err, area = evaluate_design(arg_list, self.input_list, self.output_list, self.modulename, self.output_dir, self.testbench, 'asap7.lib', '','tmp')
        print('k_stream: ' + args)
        print('Area ratio: {:.6f}\tError: {:.6f}\n'.format(area/self.input_area, err))

    def help_blasys(self):
        print('[Usage] blasys K_STREAM (a list of numbers, separate by comma).')
        print('For example, blasys 5,5,5,5,5')

    
    def do_greedy(self, args):
        curr_stream = self.output_list.copy()
        count_iter = 1
        while True:
            
            print('--------------- Iteration ' + str(count_iter) + ' ---------------')
            before = time.time()
            tmp, err, area = evaluate_iter(curr_stream, self.input_list, self.output_list, self.modulename, self.output_dir, self.testbench, 'asap7.lib','', count_iter, self.input_area )
            after = time.time()

            time_used = after - before

            print('--------------- Finishing Iteration' + str(count_iter) + '---------------')
            print('Previous k_stream: ' + str(curr_stream))
            print('Chosen k_stream:   ' + str(tmp))
            for i in range(len(curr_stream)):
                pre = curr_stream[i]
                aft = tmp[i]
                if pre != aft: 
                    print('Approximated partition ' + str(i) + ' from ' + str(pre) + ' to ' + str(aft))
                    break
            print('Approximated HD error:  ' + str(100*err) + '%')
            print('Area percentage:        ' + str(100 * area) + '%')
            print('Time used:              ' + str(time_used))

            msg = 'Approximated HD error: {:.6f}%\tArea percentage: {:.6f}%\tTime used: {:.6f} sec\n'.format(100*err, 100*area, time_used)
            print(msg)
            with open(os.path.join(self.output_dir, 'log'), 'a') as log_file:
                log_file.write(str(tmp))
                log_file.write('\n')
                log_file.write(msg)

            curr_stream = tmp

            if tmp == False:
                break

            count_iter += 1




        

    def help_greedy(self):
        print('greedy')





if __name__ == '__main__':
    # Write abc script
    with open('abc.script', 'w') as file:
        file.write('strash;fraig;refactor;rewrite -z;scorr;map')
    check_sys_req()
    print_banner()
    Blasys().cmdloop()
