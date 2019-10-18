import regex as re
import sys
import random

def create_testbench(path, modulename, num, f):
    with open(path) as file:
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
				    if out == 1 and t != 'wire':
					    n_outputs+=1
				    if t == 'input':
					    inp=1
				    elif t == 'output':
					    out=1
					    inp=0
				    elif t == 'wire':
					    out=0
		    line=file.readline()
	    file.close()
    f.write("module "+modulename+"_tb;\n")
    f.write('reg ['+str(n_inputs-1)+':0] pi;\n')
    f.write('wire ['+str(n_outputs-1)+':0] po;\n')
    f.write(modulename+' dut(')
    with open(path) as file:
	    line = file.readline()
	    inp=0
	    out=0
	    first=1
	    i=0
	    while line:
		    line.strip()
		    tokens=re.split('[ ,;\n]', line)
		    for t in tokens:			
			    t.strip()
			    if t != "":
				    if inp == 1 and t != 'output':
					    if first==0:
						    #print(', '+t, end='')
						    f.write(', pi['+str(i)+']')
					    else:
						    first=0
						    f.write('pi['+str(i)+']')
					    i=i+1
				    if out == 1 and t != 'wire':
					    if first == 0:
						    #print(', '+t, end='')
						    f.write(', po['+str(i)+']')
					    else:
						    first=0
						    f.write(', po['+str(i)+']')
					    i+=1
				    if t == 'input':
					    inp=1
				    elif t == 'output':
					    i=0
					    first=1
					    out=1
					    inp=0
				    elif t == 'wire':
					    f.write(');\n')
					    out=0
		    line=file.readline()
	    file.close()

    f.write("initial\n")
    f.write("begin\n")
    if n_inputs >= 15:
            j=1
            while j <= int(num):
	            f.write('# 1  pi='+str(n_inputs)+'\'b')
	            i=1
	            while i <= n_inputs:
		            n=random.randint(0, 1)
		            i+=1
		            f.write(n)
	            f.write(';\n')
	            f.write("#1 $display(\"%b\", po);\n")
	            j+=1
    else:
            for j in range(2**n_inputs):
 	            f.write('# 1  pi='+str(n_inputs)+'\'b')
	            f.write('{0:0>{1}}'.format(bin(j)[2:], n_inputs))
	            f.write(';\n')
	            f.write("#1 $display(\"%b\", po);\n")
                   
    f.write("end\n")
    f.write("endmodule\n")

	    
