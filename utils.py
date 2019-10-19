import regex as re
import sys
import random
import ctypes
import os
import numpy as np
import subprocess

def evaluate_design(k_stream, worker, filename):
    print('Evaluating Design:', k_stream)
    verilog_list = [os.path.join(worker.output, 'partition', worker.modulename + '.v')]

    # Parse each subcircuit
    for i, modulename in enumerate(worker.modulenames):
        approx_degree = k_stream[i]
        # If subcircuit does not exist
        # if approx_degree == -1:
        #     continue
        # If subcircuit is not approximated
        if approx_degree == worker.output_list[i]:
            part_verilog = os.path.join(worker.output, 'partition', modulename + '.v')
            verilog_list.append(part_verilog)
            continue
        
        part_verilog = os.path.join(worker.output, modulename, modulename + '_approx_k=' + str(approx_degree) + '.v')
        # If has not been approximated before
        if not os.path.exists(part_verilog):
            print('----- Approximating part ' + str(i) + ' to degree ' + str(approx_degree))

            directory = os.path.join(worker.output, modulename, modulename)
            approximate(directory, approx_degree, worker, i)
        
        verilog_list.append(part_verilog)

    truth_dir = os.path.join(worker.output, 'truthtable', filename+'.truth')
    subprocess.call([worker.path['iverilog'], '-o', truth_dir[:-5]+'iv'] + verilog_list + [worker.testbench])
    with open(truth_dir, 'w') as f:
        subprocess.call([worker.path['vvp'], truth_dir[:-5]+'iv'], stdout=f)
    os.remove(truth_dir[:-5] + 'iv')

    ground_truth = os.path.join(worker.output, worker.modulename + '.truth')
    
    output_syn = os.path.join(worker.output, 'approx_design', filename)
    area  = synth_design(' '.join(verilog_list), output_syn, worker.library, worker.script, worker.path['yosys'])

    t, h, f = assess_HD(ground_truth, truth_dir)
    print('Simulation error: ' + str(f) + '\tCircuit area: ' + str(area))
    return f, area



def assess_HD(original_path, approximate_path):
    with open(original_path, 'r') as fo:
        org_line_list = fo.readlines()
    with open(approximate_path, 'r') as fa:
        app_line_list = fa.readlines()
    
    org_size = len(org_line_list)
    app_size = len(app_line_list)

    if org_size != app_size:
        print('ERROR! sizes of input files are not equal! Aborting...')
        return -1

    HD=0
    total=0
    for n in range(org_size):
        l1=org_line_list[n]
        l2=app_line_list[n]
        for k in range(len(l1)):
            total+=1
            if l1[k] != l2[k]:
                HD+=1
    return [total, HD, HD/total]

def synth_design(input_file, output_file, lib_file, script, yosys):
    yosys_command = 'read_verilog ' + input_file + '; ' \
            + 'synth -flatten; opt; opt_clean -purge; techmap; write_verilog -noattr ' +output_file + '.v; abc -liberty '+lib_file \
            + ' -script ' + script + '; stat -liberty '+lib_file + '; write_verilog -noattr ' +output_file + '_syn.v;\n '

    area = 0
    line=subprocess.call(yosys+" -p \'"+ yosys_command+"\' > "+ output_file+".log", shell=True)
    with open(output_file+".log", 'r') as file_handle:
        for line in file_handle:
            if 'Chip area' in line:
                area = line.split()[-1]
                break
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


def  gen_truth(fname, modulename):
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
    #s=''
    #for i in range(n-1, 0, -1):
    #    s = s+signal+str(i)+', '
    #s=s+signal+'0'
    #return s

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
        '''
        constant=1
        not_first=0
        for j in range(2 ** n):
            if W[j,i] == 1:
                constant = 0
                if (not_first):
                    f1.write(' | ')
                not_first=1
                str1=bin(j).replace("0b", "")
                str2="0"*(n-len(str1))
                num=str2+str1
                if (num[len(num)-1] == '1'):
                    f1.write('(in0')
                else:
                    f1.write('(~in0')
                for ii in range(2, len(num)+1):
                    if num[len(num)-ii] == '1':
                        f1.write(' & in'+str(ii-1))
                    else:
                        f1.write(' & ~in'+str(ii-1))
                f1.write(')')
        if constant == 1:
            f1.write('0')
        f1.write(';\n')  
'''
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
                    f1.write(' | k'+str(k - j -1))
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

#def approximate(inputfile, k, num_in, num_out, liberty, modulename, app_path, output_dir):
def approximate(inputfile, k, worker, i):
    #print('./asso ' + inputfile + '.truth ' +  str(k))
    #modulename = worker.modulename + '_' + str(i)
    modulename = worker.modulenames[i]
    #os.system(info['asso'] + ' ' + inputfile + '.truth ' +  str(k))
    #subprocess.call([worker.path['asso'], inputfile+'.truth', str(k)])
    asso = ctypes.CDLL(worker.path['asso'])
    asso.asso( ctypes.c_char_p(bytes(inputfile+'.truth', encoding='ASCII')), ctypes.c_int(k) )
    W = np.loadtxt(inputfile + '.truth_w_' + str(k), dtype=int)
    H = np.loadtxt(inputfile + '.truth_h_' + str(k), dtype=int)
    formula_file = os.path.join(worker.output, modulename, modulename+'_formula.v')
    if k == 1:
        W = W.reshape((W.size, 1))
        H = H.reshape((1, H.size))
    print('----- Writing approximate design...')
    create_wh(worker.input_list[i], worker.output_list[i], k, W, H, inputfile, modulename, worker.output, worker.path['abc'], formula_file)
    print('Simulating truth table on approximation design...')
    # os.system('iverilog -o ' + inputfile + '_approx_k=' + str(k) + '.iv ' + inputfile + '_approx_k=' + str(k) + '.v ' + testbench)
    # os.system('vvp ' + inputfile + '_approx_k=' + str(k) + '.iv > ' + inputfile + '_approx_k=' + str(k) + '.truth' )
    # synth_design_app(inputfile + '_approx_k=' + str(k) + '.v', inputfile + '_approx_k=' + str(k), liberty)
