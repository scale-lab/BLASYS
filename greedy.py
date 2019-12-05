from utils.greedyWorker import GreedyWorker
from utils.banner import print_banner
import yaml
import argparse
import os




######################
#        MAIN        #
######################
def main():
    app_path = os.path.dirname(os.path.realpath(__file__))
    
    # Parse command-line args
    parser = argparse.ArgumentParser(description='BLASYS -- Approximate Logic Synthesis Using Boolean Matrix Factorization')
    parser.add_argument('-i', help='Input verilog file', required=True, dest='input')
    parser.add_argument('-tb', '--testbench', help='Number of test vectors', type=int, default=10000, dest='testbench')
    parser.add_argument('-n', help='Number of partitions', default=None, type=int, dest='npart')
    parser.add_argument('-o', help='Output directory', default='output', dest='output')
    parser.add_argument('-ts', '--threshold', help='Threshold on error', default=0.9, type=float, dest='threshold')
    parser.add_argument('-lib', '--liberty', help='Liberty file name', required=True, dest='liberty')
    parser.add_argument('-ss', '--stepsize', help='Step size of optimization process', default=1, type=int, dest='stepsize')
    parser.add_argument('--parallel', help='Run the flow in parallel mode if specified', dest='parallel', action='store_true')
    parser.add_argument('--weight', help='Use weight in error metric', dest='use_weight', action='store_true')
    parser.add_argument('--single', help='Factorize without partition', dest='single', action='store_true')

    args = parser.parse_args()

    print_banner()

    # Load path to yosys, lsoracle, iverilog, vvp, abc
    with open(os.path.join(app_path, 'config', 'params.yml'), 'r') as config_file:
        config = yaml.safe_load(config_file)

    config['part_config'] = os.path.join(app_path, 'config', 'test.ini')

    worker = GreedyWorker(args.input, args.liberty, config, None)
    worker.create_output_dir(args.output)
    pis, pos = worker.evaluate_initial(args.testbench)
    if args.single is not True:
        worker.convert2aig()
        if args.npart is None:
            worker.recursive_partitioning()
        else:
            worker.recursive_partitioning(args.npart)

        worker.greedy_opt(args.parallel, args.stepsize, args.threshold, use_weight=args.use_weight)
    else:
        worker.blasys(args.use_weight)


if __name__ == '__main__':
    main()
