from utils.greedyWorker import print_banner, GreedyWorker
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
    parser.add_argument('-tb', help='Testbench verilog file', required=True, dest='testbench')
    parser.add_argument('-n', help='Number of partitions', required=True, type=int, dest='npart')
    parser.add_argument('-o', help='Output directory', default='output', dest='output')
    parser.add_argument('-ts', help='Threshold on error', default=0.9, type=float, dest='threshold')
    parser.add_argument('-lib', help='Liberty file name', default=os.path.join(app_path, 'tsmc65.lib'), dest='liberty')
    parser.add_argument('--parallel', help='Run the flow in parallel mode if specified', dest='parallel', action='store_true')

    args = parser.parse_args()

    print_banner()

    # Load path to yosys, lsoracle, iverilog, vvp, abc
    with open(os.path.join(app_path, 'config', 'params.yml'), 'r') as config_file:
        config = yaml.safe_load(config_file)

    config['part_config'] = os.path.join(app_path, 'config', 'test.ini')
    config['asso'] = os.path.join(app_path, 'asso', 'asso.so')

    worker = GreedyWorker(args.input, args.testbench, args.liberty, config, args.threshold)
    worker.create_output_dir(args.output)
    worker.evaluate_initial()
    worker.recursive_partitioning(args.npart)
    worker.greedy_opt(args.parallel)

if __name__ == '__main__':
    main()
