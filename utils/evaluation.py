import sys
import yaml
import regex as re
import os
import argparse
import shutil
from .utils import synth_design, get_delay, get_power
from .create_tb import create_testbench
from .metric import distance
import subprocess



app_path = os.path.dirname(os.path.realpath(__file__))
# Parse command-line args
parser = argparse.ArgumentParser(description='BLASYS -- Approximate Logic Synthesis Using Boolean Matrix Factorization')
parser.add_argument('-i', help='Input verilog file', nargs='+', required=True, dest='input')
parser.add_argument('-o', help='Output directory', required=True, dest='output')
parser.add_argument('-lib', '--liberty', help='Liberty file name', required=True, dest='liberty')
args = parser.parse_args()

abc_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config', 'abc.script')

# Create output die
if os.path.exists(args.output):
    shutil.rmtree(args.output)
os.mkdir(args.output)
os.mkdir(os.path.join(args.output, 'tb'))
os.mkdir(os.path.join(args.output, 'truthtable'))
# Load path to yosys, lsoracle, iverilog, vvp, abc
with open(os.path.join(app_path, 'config', 'params.yml'), 'r') as config_file:
    config = yaml.safe_load(config_file)

sta_script = os.path.join(args.output, 'sta.script')
sta_output = os.path.join(args.output, 'sta.out')

result = os.path.join(args.output, 'result.txt')
with open(result, 'w') as data:
    data.write('{},{},{},{},{},{},{}\n'.format('Design','HD', 'MAE', 'MAE%', 'Area(um^2)', 'Power(uW)', 'Delay(ns)') )


for inp in args.input:
    
    with open(inp) as file:
        line = file.readline()
        while line:
            tokens = re.split('[ (]', line)
            for i in range(len(tokens)):
                if tokens[i] == 'module':
                    modulename = tokens[i+1]
                    break
            line = file.readline()

    # TODO: Chip area
    out_syn = os.path.join(args.output, 'modulename')
    area = synth_design(inp, out_syn, args.liberty, abc_path, config['yosys'] )
    print('Circuit area for {}: {}'.format(modulename, area))

    # TODO: Error metric
    tb = os.path.join(args.output, modulename+'_tb.v')

    if inp == args.input[0]:
        org_modulename = modulename
        org_tb = tb
        with open(tb, 'w') as f:
            create_testbench(inp, 10000, f)
    
        truth_dir = os.path.join(args.output, 'truthtable', modulename+'.truth')
        subprocess.call([config['iverilog'], '-o', truth_dir[:-5]+'iv', tb, inp])
        with open(truth_dir, 'w') as f:
            subprocess.call([config['vvp'], truth_dir[:-5]+'iv'], stdout=f)
        os.remove(truth_dir[:-5] + 'iv')

        ground_truth = truth_dir
        metric = [.0, .0, .0]
    
    else:
        with open(org_tb) as f1, open(tb, 'w') as f2:
            line = f1.readline().replace(org_modulename, modulename)
            f2.write(line)
            while line:
                line = f1.readline().replace(org_modulename, modulename)
                f2.write(line)
        truth_dir = os.path.join(args.output, 'truthtable', modulename+'.truth')
        subprocess.call([config['iverilog'], '-o', truth_dir[:-5]+'iv', tb, inp])
        with open(truth_dir, 'w') as f:
            subprocess.call([config['vvp'], truth_dir[:-5]+'iv'], stdout=f)
        os.remove(truth_dir[:-5] + 'iv')

        _, metric = distance(ground_truth, truth_dir )
    
    print('Hamming Distance: {}\tMAE: {}\tMAE%:{}'.format(metric[0], metric[1], metric[2]))


    # TODO: Circuit delay
    delay = get_delay(config['OpenSTA'], sta_script, args.liberty, out_syn+'_syn.v', modulename, sta_output)
    if inp == args.input[0]:
        org_delay = delay
    print('Delay: {}'.format(delay))

    # TODO: Power consumption
    power = get_power(config['OpenSTA'], sta_script, args.liberty, out_syn+'_syn.v', modulename, sta_output, org_delay) * 1000000
    print('Power:', power)

    # TODO: Write results in output file
    with open(result, 'a') as data:
        data.write('{},{:.6f},{:.6e},{:<.6f},{:.2f},{:.6f},{:.6f}\n'.format(modulename, metric[0], metric[1], metric[2], area, power, delay) )


