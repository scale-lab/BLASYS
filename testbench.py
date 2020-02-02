import regex as re
import sys
import random
import os
import argparse
import subprocess
import time
import regex as re
from utils.banner import print_banner
import yaml

def create_testbench(input_file, output_file, num, yosys):

    f = open(output_file, 'w')
    modulename, port_list, inp, n_inputs, out, n_outputs = module_info(input_file, yosys)

    f.write("module "+modulename+"_tb;\n")
    f.write('reg ['+str(n_inputs-1)+':0] pi;\n')
    f.write('wire ['+str(n_outputs-1)+':0] po;\n')
    f.write(modulename+' dut(')

    # if.write('pi[0]')
    # for i in range(1, n_inputs):
        # f.write(', pi[{}]'.format(i))
    # for i in range(n_outputs):
        # f.write(', po[{}]'.format(i))
    # f.write(');\n')

    first = True
    inp_count = 0
    out_count = 0

    for i in port_list:
        if not first:
            f.write(',')
        first = False

        if i in inp:
            if inp[i] > 1:
                f.write(' pi[{}:{}] '.format(inp_count + inp[i] - 1, inp_count))
            else:
                f.write(' pi[{}] '.format(inp_count))
            inp_count += inp[i]

        elif i in out:
            if out[i] > 1:
                f.write(' po[{}:{}] '.format(out_count + out[i] - 1, out_count))
            else:
                f.write(' po[{}] '.format(out_count))
            out_count += out[i]

        else:
            print('[Error] Port {} is not defined as input or output.'.format(i))
            sys.exit(0)
    #count = 0
    #for i in inp:
    #    if not first:
    #        f.write(',')
    #    first = False
    #    if inp[i] > 1:
    #        f.write(' .{}(pi[{}:{}]) '.format(i, count + inp[i] - 1, count))
    #    else:
    #        f.write(' .{}(pi[{}]) '.format(i, count))
    #    count += inp[i]

    #count = 0
    #for i in out:
    #    if not first:
    #        f.write(',')
    #    first = False
    #    if out[i] > 1:
    #        f.write(' .{}(po[{}:{}]) '.format(i, count + out[i] - 1, count))
    #    else:
    #        f.write(' .{}(po[{}]) '.format(i, count))
    #    count += out[i]


    f.write(');\n')
        

    f.write("initial\n")
    f.write("begin\n")
    if n_inputs >= 17:
        j=1
        while j <= int(num):
            f.write('# 1  pi='+str(n_inputs)+'\'b')
            i=1
            while i <= n_inputs:
                n=random.randint(0, 1)
                i+=1
                f.write(str(n))
            f.write(';\n')
            f.write("#1 $display(\"%b\", po);\n")
            j+=1
    else:
        for j in range(2**n_inputs):
            f.write('# 1  pi='+str(n_inputs)+'\'b')
            f.write('{0:0>{1}}'.format(str(bin(j))[2:], n_inputs))
            f.write(';\n')
            f.write("#1 $display(\"%b\", po);\n")
                       
    f.write("end\n")
    f.write("endmodule\n")

    f.close()



def module_info(fname, yosys_path):

    tmp = time.strftime('%Y_%m_%d-%H_%m_%s') + '.v'
    yosys_command = 'read_verilog ' + fname + '; synth -flatten; opt; opt_clean; techmap; write_verilog ' + tmp + ';\n'
    subprocess.call([yosys_path, '-p', yosys_command], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    tmp_file = open(tmp)
    inp = {}
    inp_count = 0
    out = {}
    out_count = 0
    modulename = None
    line = tmp_file.readline()
    while line:
        tokens = re.split('[ ()]', line.strip().strip(';').strip())
         
        if len(tokens) > 0 and tokens[0] == 'module' and modulename is None:
            modulename = tokens[1]
            port_list = re.split('[,()]', line.strip().strip(';').strip())[1:]
            port_list = [s.strip() for s in port_list if s.strip() != '']



        if len(tokens) == 2 and ( tokens[0] == 'input' or tokens[0] == 'output' ):
            if tokens[0] == 'input':
                inp[tokens[1]] = 1
                inp_count += 1
            if tokens[0] == 'output':
                out[tokens[1]] = 1
                out_count += 1

        if len(tokens) == 3 and ( tokens[0] == 'input' or tokens[0] == 'output' ):
            range_str = tokens[1][1:-1].split(':')
            range_int = list(map(int, range_str))
            length = max(range_int) - min(range_int) + 1
            if tokens[0] == 'input':
                inp[tokens[2]] = length
                inp_count += length
            if tokens[0] == 'output':
                out[tokens[2]] = length
                out_count += length

        line = tmp_file.readline()


    tmp_file.close()  

    os.remove(tmp)

    return modulename, port_list, inp, inp_count, out, out_count


def main():
    app_path = os.path.dirname(os.path.realpath(__file__))
    
    # Parse command-line args
    parser = argparse.ArgumentParser(description='BLASYS -- Approximate Logic Synthesis Using Boolean Matrix Factorization')
    parser.add_argument('-i', help='Input verilog file', required=True, dest='input')
    parser.add_argument('-o', help='Output testbench file', required=True, dest='output')
    parser.add_argument('-n', help='Number of test vectors', type=int, default=10000, dest='number')
    args = parser.parse_args()

    print_banner()
    print('Start creating testbench ...')

    # Load path to yosys, lsoracle, iverilog, vvp, abc
    with open(os.path.join(app_path, 'config', 'params.yml'), 'r') as config_file:
        config = yaml.safe_load(config_file)

    create_testbench(args.input, args.output, args.number, config['yosys'] )


if __name__ == '__main__':
    main()
