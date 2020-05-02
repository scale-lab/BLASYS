from utils.greedyWorker import GreedyWorker
from utils.banner import print_banner
import yaml
import argparse
import os
import numpy as np
import sys
import multiprocessing as mp
import time
from utils.cml import Blasys




######################
#        MAIN        #
######################
def main():
    
    # System config
    max_cpu = mp.cpu_count()
    app_path = os.path.dirname(os.path.realpath(__file__))
    
    # Parse command-line args
    parser = argparse.ArgumentParser(description='BLASYS -- Approximate Logic Synthesis Using Boolean Matrix Factorization')
    parser.add_argument('-i', '--input', help='Input verilog file', required=True, dest='input')
    parser.add_argument('-tb', '--testbench', help='Number of test vectors', required=True, dest='testbench')
    parser.add_argument('-n', '--number', help='Number of partitions', default=None, type=int, dest='npart')
    parser.add_argument('-o', '--output', help='Output directory', default=None, dest='output')
    parser.add_argument('-ts', '--threshold', help='Threshold on error', default='None', dest='threshold')
    parser.add_argument('-lib', '--liberty', help='Liberty file name', default=None, dest='liberty')
    parser.add_argument('-ss', '--stepsize', help='Step size of optimization process', default=1, type=int, dest='stepsize')   
    parser.add_argument('-m', '--metric', help='Choose error metric', dest='metric', default='HD')
    parser.add_argument('-tr', '--track', help='Number of tracks in greedy search', dest='track', type=int, default=3)
    parser.add_argument('-cpu', '--cpu_count', help='Specify number of CPU in parallel mode', dest='cpu', type=int, default=-1)
    
    # Flags 
    parser.add_argument('--parallel', help='Run the flow in parallel mode if specified', dest='parallel', action='store_true')
    parser.add_argument('--no_partition', help='Factorize without partition', dest='single', action='store_true')
    parser.add_argument('--sta', help='Use OpenSTA to estimate power and delay', dest='sta', action='store_true')

    args = parser.parse_args()

    if args.parallel == True and args.cpu == -1:
        args.cpu = max_cpu

    if args.cpu != -1:
        args.parallel = True

    print_banner()

    # Load path to yosys, lsoracle, iverilog, vvp, abc
    with open(os.path.join(app_path, 'config', 'params.yml'), 'r') as config_file:
        config = yaml.safe_load(config_file)

    config['part_config'] = os.path.join(app_path, 'config', 'test.ini')
    if args.threshold == 'None':
        threshold_list = [np.inf]
    else:
        threshold_list = list(map(float, args.threshold.split(',')))

    # Create optimizer
    worker = GreedyWorker(args.input, args.liberty, config, args.testbench, args.metric, args.sta)
    
    # Output directory
    worker.create_output_dir(args.output)
    
    # Evaluate input circuit
    worker.evaluate_initial()

    # Partition mode or non_partition mode
    if args.single is not True:
        worker.convert2aig()
        if args.npart is None:
            worker.recursive_partitioning()
        else:
            worker.recursive_partitioning(args.npart)

        worker.greedy_opt(args.parallel, args.cpu, args.stepsize, threshold_list, track=args.track)
    else:
        worker.blasys()


if __name__ == '__main__':

    # Open command-line interface
    if len(sys.argv) == 1:
        print_banner()
        Blasys().cmdloop()

    # Use script file as command-line
    elif len(sys.argv) == 3 and sys.argv[1] == '-f':
        script = sys.argv[2]
        blasys = Blasys()
        print_banner()
        with open(script, 'r') as f:
            cmd = f.readline()
            count = 0
            while cmd:
                print('[' + str(count) + '] Run BLASYS command: '  + cmd )
                blasys.onecmd(cmd)
                cmd = f.readline()
                count += 1

    # Normal execution
    else:
        main()
