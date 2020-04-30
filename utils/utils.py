import regex as re
import sys
import os
import numpy as np
import shutil
import subprocess
import time
from .ASSO.BMF import BMF

class CombinationalLoop(Exception):
    pass

class NoValidDesign(Exception):
    pass


def evaluate_design(k_stream, worker, filename, display=True):
    if display:
        print('Evaluating Design:', k_stream)
    verilog_list = [os.path.join(worker.output, 'partition', worker.modulename + '.v')]

    # Parse each subcircuit
    for i, modulename in enumerate(worker.modulenames):
        approx_degree = k_stream[i]

        # If subcircuit is not approximated
        if approx_degree == worker.output_list[i]:
            part_verilog = os.path.join(worker.output, 'partition', modulename + '.v')
            verilog_list.append(part_verilog)
            continue
        
        part_verilog = os.path.join(worker.output, 'bmf_partition', modulename, modulename + '_approx_k=' + str(approx_degree) + '.v')
        # If has not been approximated before
        if not os.path.exists(part_verilog):
            print('----- Approximating part ' + str(i) + ' to degree ' + str(approx_degree))

            directory = os.path.join(worker.output, 'bmf_partition', modulename, modulename)
            approximate(directory, approx_degree, worker, i)
        
        verilog_list.append(part_verilog)
    
    # Synthesize and estimate chip area
    try:
        output_syn = os.path.join(worker.output, 'tmp', filename)
        area  = synth_design(' '.join(verilog_list), output_syn, worker.library, worker.script, worker.path['yosys'])
    except CombinationalLoop:
        return None

    # QoR estimation
    truth_dir = os.path.join(worker.output, 'truthtable', filename+'.truth')
    subprocess.call([worker.path['iverilog'], '-o', truth_dir[:-5]+'iv'] + verilog_list + [worker.testbench])
    with open(truth_dir, 'w') as f:
        subprocess.call([worker.path['vvp'], truth_dir[:-5]+'iv'], stdout=f)
    os.remove(truth_dir[:-5] + 'iv')

    ground_truth = os.path.join(worker.output, worker.modulename + '.truth')
    err = worker.metric(ground_truth, truth_dir)
    
    if worker.sta:
        # Estimate time and power
        sta_script = os.path.join(worker.output, 'tmp', filename+'_sta.script')
        sta_output = os.path.join(worker.output, 'tmp', filename+'_sta.out')
        delay = get_delay(worker.path['OpenSTA'], sta_script, worker.library, output_syn+'_syn.v', worker.modulename, sta_output)
        power = get_power(worker.path['OpenSTA'], sta_script, worker.library, output_syn+'_syn.v', worker.modulename, sta_output, worker.delay)

        print('Simulation error: {:.6f}\tCircuit area: {:.6f}\tCircuit delay: {:.6f}\tPower consumption: {:.6f}'.format(err, area, delay, power))

        os.remove(sta_script)
        os.remove(sta_output)
    else:
        delay = float('nan')
        power = float('nan')
        print('Simulation error: {:.6f}\tCircuit area: {:.6f}'.format(err, area))


    return err, area, delay, power


def synth_design(input_file, output_file, lib_file, script, yosys):

    if lib_file is not None:
        yosys_command = 'read_verilog ' + input_file + '; ' + 'synth -flatten; opt; opt_clean -purge;  opt; opt_clean -purge; write_verilog -noattr ' +output_file + '.v; abc -liberty '+lib_file + ' -script ' + script + '; stat -liberty '+lib_file + '; write_verilog -noattr ' +output_file + '_syn.v;\n '
        area = 0
        #line=subprocess.call(yosys+" -p \'"+ yosys_command+"\' > "+ output_file+".log", shell=True)
        with open(output_file+'.log', 'w') as f:
            line = subprocess.call([yosys, '-p', yosys_command], stdout=f, stderr=subprocess.STDOUT)
        with open(output_file+".log", 'r') as file_handle:
            for line in file_handle:
                # Combinational loop
                if 'Warning: found logic loop' in line:
                    os.remove(output_file+'.log')
                    raise CombinationalLoop()

                # Find chip area and return
                if 'Chip area' in line:
                    area = line.split()[-1]
                    break

    else:
        yosys_command = 'read_verilog ' + input_file + '; ' + 'synth -flatten; opt; opt_clean -purge; opt; opt_clean -purge; write_verilog -noattr ' +output_file + '.v; abc -g NAND -script ' + script + '; write_verilog -noattr ' +output_file + '_syn.v;\n '
        area = 0
        #line=subprocess.call(yosys+" -p \'"+ yosys_command+"\' > "+ output_file+".log", shell=True)
        with open(output_file+'.log', 'w') as f:
            line = subprocess.call([yosys, '-p', yosys_command], stdout=f, stderr=subprocess.STDOUT)
        with open(output_file+".log", 'r') as file_handle:
            return_list = []
            for line in file_handle:
                # Combinational loop
                if 'Warning: found logic loop' in line:
                    os.remove(output_file+'.log')
                    raise CombinationalLoop()

                # Find num of NAND cells
                if 'ABC RESULTS:' in line and 'NAND cells:' in line:
                    return_list.append(line.split()[-1])
            if len(return_list) == 0:
                area = 0
            else:
                area = return_list[-1]

    os.remove(output_file+'.log')
    return float(area)

def inpout(fname):
    with open(fname) as file:
        line = file.readline()
        inp=0
        out=0
        n_inputs=0
        n_outputs=0
        while line:
            line.strip()
            tokens=re.split('[ ,;\n]', line)
            for t in tokens:
                t.strip()
                if t != "":
                    if inp == 1 and t != 'output':
                        n_inputs+=1
                    if out == 1 and t != 'wire' and t != 'assign':
                        n_outputs+=1
                    if t == 'input':
                        inp=1
                    elif t == 'output':
                        out=1
                        inp=0
                    elif t == 'wire' or t == 'assign':
                        out=0
            line=file.readline()

    return n_inputs, n_outputs


def gen_truth(fname, modulename):
    with open(fname+'.v') as file:
        f=open(fname+'_tb.v', "w+")
        line = file.readline()
        inp=0
        out=0
        n_inputs=0
        n_outputs=0
        while line:
            line.strip()
            tokens=re.split('[ ,;\n]', line)
            for t in tokens:
                t.strip()
                if t != "":
                    if inp == 1 and t != 'output':
                        n_inputs+=1
                    if out == 1 and t != 'wire' and t != 'assign':
                        n_outputs+=1
                    if t == 'input':
                        inp=1
                    elif t == 'output':
                        out=1
                        inp=0
                    elif t == 'wire' or t == 'assign':
                        out=0
            line=file.readline()
        file.close()
    if n_inputs > 16:   
        print('BLASYS cannot handle more than 16 inputs per partition; reduce parition sizes')
        exit(-1)
    f.write("module "+modulename+"_tb;\n")
    f.write('reg ['+str(n_inputs-1)+':0] pi;\n')
    f.write('wire ['+str(n_outputs-1)+':0] po;\n')
    f.write(modulename+' dut(')
    with open(fname+'.v') as file:
        line = file.readline()
        inp=0
        out=0
        first=1
        end=0
        i=0
        while line:
            line.strip()
            tokens=re.split('[ ,;\n]', line)
            for t in tokens:			
                t.strip()
                if t != "":
                    if inp == 1 and t != 'output':
                        if first==0:
                            #f.write(', '+t, end='')
                            f.write(', pi['+str(n_inputs-i-1)+']')
                        else:
                            first=0
                            f.write('pi['+str(n_inputs-i-1)+']')
                        i=i+1
                    if out == 1 and t != 'wire' and t != 'assign':
                        if first == 0:
                            #f.write(', '+t, end='')
                            f.write(', po['+str(n_outputs-i-1)+']')
                        else:
                            first=0
                            f.write(', po['+str(n_outputs-i-1)+']')
                        i+=1
                    if t == 'input':
                        inp=1
                    elif t == 'output':
                        i=0
                        first=1
                        out=1
                        inp=0
                    elif t == 'wire' or t == 'assign':
                        if not end:
                            f.write(');\n')
                            end=1
                        out=0
            line=file.readline()
        file.close()
    f.write("initial\n")
    f.write("begin\n")
    j=0
    while j < 2**n_inputs:
        f.write('# 1  pi='+str(n_inputs)+'\'b')
        str1=bin(j).replace("0b", "")
        str2="0"*(n_inputs-len(str1))
        n=str2+str1
        f.write(n)
        f.write(';\n')
        f.write("#1 $display(\"%b\", po);\n")
        j+=1
    f.write("end\n")
    f.write("endmodule\n")
    f.close()
    return n_inputs, n_outputs


def v2w_top(signal,  n):


    digit_len = len(str(n))
    s=''
    s=s+signal+'{0:0{1}}'.format(0, digit_len)
    for i in range(1,n):
        s = s+', '+signal+'{0:0{1}}'.format(i, digit_len)
    return s


def v2w(signal,  n):
    s=''
    for i in range(n-1, 0, -1):
        s = s+signal+str(i)+', '
    s=s+signal+'0'
    return s


def create_w(n, k, W, f1, modulename, formula_file, abc):    
    f1.write('module '+modulename+'_w'+str(k)+'('+v2w('in', n)+', '+ v2w('k', k)+');\n')
    f1.write('input '+v2w('in', n)+';\n')
    f1.write('output '+v2w('k', k)+';\n')

    for i in range(k-1, -1, -1):
        f1.write('assign k'+str(k-i-1)+' = ')
        
        truth=""
        for j in range(2 ** n-1,-1,-1):
            truth= truth+str(W[j,i])
#        print(truth)
        if truth.find('1') != -1:
            script='read_truth -x '+truth+';bdd;order;write_verilog '+formula_file
            #os.system(abc+' -q '+'\''+script+'\'')
            subprocess.call([abc, '-q', script])
            with open(formula_file, 'r') as file_handle:
                for line in file_handle:
                    if 'assign' in line:
                        formula=line
            formula=formula.replace('assign F = ', '')
#            print(formula)
            for c in range(n):
                formula=formula.replace(chr(97+c)+ ';', 'in'+str(n-c-1)+';')
                formula=formula.replace(chr(97+c)+ ' ', 'in'+str(n-c-1)+' ')
                formula=formula.replace(chr(97+c)+ ')', 'in'+str(n-c-1)+')')
        else:
            formula='0;\n'
 #       print(formula)
        f1.write(formula)

    f1.write('endmodule\n\n')

def create_h(m, k, H, f1, modulename):
    f1.write('module '+modulename+'_h'+str(k)+'('+v2w('k', k)+', '+ v2w('out', m)+');\n')
    f1.write('input '+v2w('k', k)+';\n')
    f1.write('output '+v2w('out', m)+';\n')
    # Print The gates...
    for i in range(m-1, -1, -1):
        f1.write('assign out'+str(m-i-1)+' = ')
        not_first=0
        constant=1
        for j in  range(k):
            if H[j,i] == 1:
                constant=0
                if (not_first):
                    f1.write(' ^ k'+str(k - j -1))
                else:
                    f1.write('k'+str(k - j - 1))
                not_first=1
        if constant == 1:
            f1.write('0')
        f1.write(';\n')
    
    f1.write('endmodule\n')



def create_wh(n, m, k, W, H, fname, modulename, output_dir, abc, formula_file):
    f1=open(fname+'_approx_k='+str(k)+'.v','w')
    f1.write('module ' +modulename+'(' + v2w_top('pi', n)+', '+ v2w_top('po', m)+');\n')
    f1.write('input '+v2w_top('pi', n)+';\n')
    f1.write('output '+v2w_top('po', m)+';\n')
    f1.write('wire '+v2w_top('k', k)+';\n')
    f1.write(modulename+'_w'+str(k)+' DUT1 ('+v2w_top('pi', n)+', '+ v2w_top('k', k)+');\n')
    f1.write(modulename+'_h'+str(k)+' DUT2 ('+v2w_top('k', k)+', '+ v2w_top('po', m)+');\n')
    f1.write('endmodule\n\n')
    create_w(n, k, W, f1, modulename, formula_file, abc)
    create_h(m, k, H, f1, modulename)
    f1.close

def approximate(inputfile, k, worker, i, output_name=None):

    modulename = worker.modulenames[i]
    if output_name is None:
        output_name = modulename

    BMF( inputfile+'.truth', k, True)
    W = np.loadtxt(inputfile + '.truth_w_' + str(k), dtype=int)
    H = np.loadtxt(inputfile + '.truth_h_' + str(k), dtype=int)
    formula_file = os.path.join(worker.output, 'bmf_partition', modulename, modulename+'_formula.v')
    if k == 1:
        W = W.reshape((W.size, 1))
        H = H.reshape((1, H.size))

    create_wh(worker.input_list[i], worker.output_list[i], k, W, H, inputfile, output_name, worker.output, worker.path['abc'], formula_file)



def number_of_cell(input_file, yosys):
    '''
    Get number of yosys standard cells of input circuit
    '''
    yosys_command = 'read_verilog ' + input_file + '; ' \
            + 'synth -flatten; opt; opt_clean -purge; opt; opt_clean -purge; stat;\n'
    num_cell = 0
    output_file = input_file[:-2] + '_syn.log'
    line=subprocess.call(yosys+" -p \'"+ yosys_command+"\' > "+ output_file, shell=True)
    with open(output_file, 'r') as file_handle:
        for line in file_handle:
            if 'Number of cells:' in line:
                num_cell = line.split()[-1]
                break
    os.remove(output_file)
    return int(num_cell)

def write_aiger(input_file, yosys, output_file, map_file):
    '''
    Convert verilog to aig file
    '''
    yosys_command = 'read_verilog ' + input_file + '; synth -flatten; opt; opt_clean -purge; abc -g AND; aigmap; opt; opt_clean -purge; write_aiger -vmap '\
            + map_file + ' ' + output_file + ';'
    subprocess.call([yosys, '-p', yosys_command], stdout=subprocess.DEVNULL)
    # Parse map file and return dict
    # input_map = {}
    # output_map = {}
    # with open(map_file) as f:
        # line = f.readline()
        # while line:
            # tokens = line.split()
            # if tokens[0] == 'input':
                # input_map[int(tokens[1])] = tokens[3]
            # if tokens[0] == 'output':
                # output_map[int(tokens[1])] = tokens[3]

            # line = f.readline()

    # org_input_map, org_output_map = inpout_map(input_file)

    # return {i: org_input_map[input_map[i]] for i in range(len(input_map))}, \
            # {i: org_output_map[output_map[i]] for i in range(len(output_map))}



# def inpout_map(fname):
#     input_map = {}
#     output_map = {}
#     with open(fname) as file:
#         line = file.readline()
#         inp=0
#         out=0
#         n_inp = 0
#         n_out = 0
#         while line:
#             line.strip()
#             tokens=re.split('[ ,;\n]', line)
#             for t in tokens:
#                 t.strip()
#                 if t != "":
#                     if inp == 1 and t != 'output':
#                         input_map[t.strip('\\')] = n_inp
#                         n_inp += 1
#                     if out == 1 and t != 'wire' and t != 'assign':
#                         output_map[t.strip('\\')] = n_out
#                         n_out += 1
#                     if t == 'input':
#                         inp=1
#                     elif t == 'output':
#                         out=1
#                         inp=0
#                     elif t == 'wire' or t == 'assign':
#                         out=0
#             line=file.readline()
# 
#     return input_map, output_map

def get_delay(sta, script, liberty, input_file, modulename, output_file):
    with open(script, 'w') as f:
        f.write('read_liberty {}\nread_verilog {}\nlink_design {}\n'.format(liberty, input_file, modulename))
        f.write('create_clock -name clk -period 1\n')
        f.write('set_input_delay -clock clk 0 [all_inputs]\n')
        f.write('set_output_delay -clock clk 0 [all_outputs]\n')
        f.write('report_checks -digits 6\n')
        f.write('exit')

    with open(output_file, 'w') as f:
        subprocess.call([sta, script],stdout=f)

    with open(output_file) as f:
        line = f.readline()
        while line:
            tokens = line.split()
            if len(tokens) >= 4 and tokens[1] == 'data' and tokens[2] == 'arrival' and tokens[3] == 'time':
                delay = float(tokens[0]) + 0.005
                break
            line = f.readline()

    return delay


def get_power(sta, script, liberty, input_file, modulename, output_file, delay):
    with open(script, 'w') as f:
        f.write('read_liberty {}\nread_verilog {}\nlink_design {}\n'.format(liberty, input_file, modulename))
        f.write('create_clock -name clk -period {}\n'.format(delay))
        f.write('set_input_delay -clock clk 0 [all_inputs]\n')
        f.write('set_output_delay -clock clk 0 [all_outputs]\n')
        f.write('report_checks\n')
        f.write('report_power - digits 12\n')
        f.write('exit')

    with open(output_file, 'w') as f:
        subprocess.call([sta, script], stdout=f)

    with open(output_file) as f:
        line = f.readline()
        while line:
            tokens = line.split()
            if len(tokens) >= 6 and tokens[0] == 'Total':
                power = float(tokens[4])
                break
            line = f.readline()

    return power * 1e6



def create_wrapper(inp, out, top, vmap, worker):
    tmp = os.path.join(worker.output, 'tmp.v')
    yosys_command = 'read_verilog ' + inp + '; synth -flatten; opt; opt_clean;  write_verilog ' + tmp + ';\n'
    subprocess.call([worker.path['yosys'], '-p', yosys_command], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    out_file = open(out, 'w')

    # Write module signature from tmp file
    tmp_file = open(tmp)
    isVector = {}
    line = tmp_file.readline()
    while line:
        tokens = line.strip().strip(';').strip().split()

        if len(tokens) > 0 and tokens[0] == 'module':
            out_file.write(line)

        if len(tokens) > 0 and ( tokens[0] == 'input' or tokens[0] == 'output' ):
            out_file.write(line)
            if len(tokens) == 2:
                isVector[tokens[1]] = False
            else:
                isVector[tokens[2]] = True

        line = tmp_file.readline()
    tmp_file.close()
    
    # Prepare list of arguments
    arg_list = []
    input_dict = {}
    output_dict = {}
    map_file = open(vmap)
    line = map_file.readline()
    while line:
        tokens = line.split()

        # Parse input
        if tokens[0] == 'input':
            if tokens[3] in isVector:
                if isVector[tokens[3]] is False:
                    input_dict[tokens[3]] = int(tokens[1])
                else:
                    input_dict[tokens[3] + '[' + tokens[2] + ']'] = int(tokens[1])
            elif '\\'+tokens[3] in isVector:
                if isVector['\\'+tokens[3]] is False:
                    input_dict['\\'+tokens[3]] = int(tokens[1])
                else:
                    input_dict['\\'+tokens[3] + '[' + tokens[2] + ']'] = int(tokens[1])

        if tokens[0] == 'output':
            # Probe for correct number
            port_num = int(tokens[1])
            while port_num in list(output_dict.values()):
                port_num -= 1

            if tokens[3] in isVector:
                if isVector[tokens[3]] is False:
                    output_dict[tokens[3]] = port_num
                else:
                    output_dict[tokens[3] + '[' + tokens[2] + ']'] = port_num
            elif '\\'+tokens[3] in isVector:
                if isVector['\\'+tokens[3]] is False:
                    output_dict['\\'+tokens[3]] = port_num
                else:
                    output_dict['\\'+tokens[3] + '[' + tokens[2] + ']'] = port_num


        line = map_file.readline()

    inp_digit = len(str(len(input_dict)))
    out_digit = len(str(len(output_dict)))

    map_file.close()

    # Call old top-level module
    # out_file.write('  top U0 ( ' + ' , '.join(arg_list) + ' );\n')
    out_file.write('  top U0 (')
    first = True
    for i in input_dict:
        if not first:
            out_file.write(',')
        first = False
        out_file.write(' .pi{0:0{1}}( {2} ) '.format(input_dict[i], inp_digit, i))
        # out_file.write(' '+ i+' ')

    for i in output_dict:
        if not first:
            out_file.write(',')
        first = False
        out_file.write(' .po{0:0{1}}( {2} ) '.format(output_dict[i], out_digit, i))
        # out_file.write(' '+i+ ' ')


    out_file.write(');\n')
    out_file.write('endmodule\n\n')

    # Copy old top-level and change module name
    top_file = open(top)
    line = top_file.readline()
    replaced = False
    while line:
        tokens = line.split()
        if len(tokens) > 0 and tokens[0] == 'module' and not replaced:
            line = line.replace(worker.modulename, 'top', 1)
            replaced = True
        out_file.write(line)
        line = top_file.readline()
    top_file.close()

    out_file.close()
    
    os.remove(top)
    shutil.move(out, top)

    os.remove(os.path.join(worker.output, 'tmp.v'))


def create_wrapper_single(inp, out, worker):

    tmp = os.path.join(worker.output, 'tmp.v')
    yosys_command = 'read_verilog ' + inp + '; synth -flatten; opt; opt_clean; write_verilog ' + tmp + ';\n'
    subprocess.call([worker.path['yosys'], '-p', yosys_command], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    out_file = open(out, 'w')

    # Write module signature from tmp file
    tmp_file = open(tmp)
    isVector = {}
    line = tmp_file.readline()
    while line:
        tokens = line.strip().strip(';').strip().split()

        if len(tokens) > 0 and tokens[0] == 'module':
            out_file.write(line)

        if len(tokens) > 0 and ( tokens[0] == 'input' or tokens[0] == 'output' ):
            out_file.write(line)

        line = tmp_file.readline()
    tmp_file.close()

    modulename, port_list, i_map, i_count, o_map, o_count = module_info(inp, worker.path['yosys'])
    i_list = ['in{}'.format(k) for k in range(i_count-1, -1, -1)]
    o_list = ['out{}'.format(k) for k in range(o_count-1, -1, -1)]

    out_file.write('  wire ' + ', '.join(i_list) + ', ' + ', '.join(o_list) + ';\n')

    out_file.write('  assign { ')
    i = 0
    o = 0
    first = 1
    for p in port_list:
        if not first:
            out_file.write(', ')
        first = 0
        if p in i_map:
            out_file.write(', '.join( ['in{}'.format(k) for k in range(i+i_map[p]-1, i - 1, -1)] ))
            i += i_map[p]
        if p in o_map:
            out_file.write(', '.join( ['out{}'.format(k) for k in range(o+o_map[p]-1, o - 1, -1)] ))
            o += o_map[p]

    out_file.write('} = {' + ', '.join(port_list)  + '};\n')


    out_file.write('  top U0 (' + ', '.join(i_list) + ', ' + ', '.join(o_list)  + ');\n')
    out_file.write('endmodule\n')

    out_file.close()
    os.remove(tmp)









def module_info(fname, yosys_path):

    tmp = time.strftime('%Y_%m_%d-%H_%m_%s') + '.v'
    yosys_command = 'read_verilog ' + fname + '; synth -flatten; opt; opt_clean; write_verilog ' + tmp + ';\n'
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
