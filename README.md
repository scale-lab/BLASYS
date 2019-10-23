# BLASYS: Approximate Logic Synthesis Using Boolean Matrix Factorization
BLASYS toolchain reads an input circuit in Verilog format and approximates with boolean matrix factorization (BMF). The logistic is to generate truthtable for input circuit, perform BMF on truthtable, and synthesize it back to output circuit. Due to the exponential growth of truthtable, we follow a greedy design-space exploration scheme based on each subcircuit. To make the optimization process efficient on even larger circuit, we also develop an additional script to first partition into subcircuits in proper size (based on number of cells), and then do greedy exploration within each part respectively.

## System Requirement
**Operating systems**: Mac OS, Linux, Unix

**Memory requirement**: 

**Interpreter**: Python 3.6+. Be sure to install  ``numpy`` package with command 
```
pip3 install numpy
```

## Software Dependency
Be sure to install following tools before running BLASYS toolchain.
1. **Yosys**: Estimating chip area. (https://github.com/YosysHQ/yosys)
2. **ABC**: Logic synthesis. (https://github.com/berkeley-abc/abc)
3. **Icarus Verilog**: Simulation and HD error estimation. (http://iverilog.icarus.com)
4. **LSOracle**: Partitioning. (https://github.com/LNIS-Projects/LSOracle)

**NOTE:** After installing tools above, you should either **add them into environment path of your system**, or **put the path to excutable into** ``params.yml``.

![Flow](https://github.com/scale-lab/BLASYS/blob/master/doc/flow.png?raw=true)

## Usage
1. Install all packages as previous section suggests. Put paths of executable files into ``params.yml``.

2. For circuits of small-medium size, ``greedy.py`` is recommended, which performs greedy design-space exploration. The command-line arguments are
```
python3 [path to BLASYS folder]/greedy.py \
                 -i [path to input verilog file] \
                 -tb [path to testbench verilog file] \
                 -n [number of partitions] \
                 -lib [path to liberty file] \
                 -o [output folder] \
                 -ts [threshold] \
                 -ss [step size] \
                 [--parallel]
```
First four arguments (input / testbench / number of partition / liberty file) are mandatory. Default output folder is ``output``. Default step-size is 1. If no threshold ``-ts`` is specified, BLASYS will keep running until all partitions reach factorization degree 1. The last flag ``--parallel`` indicates parallel mode. If specified, BLASYS will run in parallel with all available cores in your machine.

3. For larger circuit, you may find that simulation process takes too much time. in this case, there is another script ``recursive.py``, which will first partition large circuit into proper size, and then do BLASYS on each sub-circuit. The usage is
```
python3 [path to BLASYS folder]/recursive.py \
                 -i [path to input verilog file] \
                 -tb [path to testbench verilog file] \
                 -lib [path to liberty file] \
                 -o [output folder] \
                 -ts [threshold] \
                 -ss [step size] \
                 [--parallel]

```
All command-line arguments are same as before, except that number of partitions is no longer needed. In this flow, number of partitions will be automatically computed based on **number of Yosys standard cells**.

## Result
All error-area information is stored in file ``data.csv`` under the output folder. Each line corresponds to the best result of each iteration, where first column is HD error, second column is chip area, and third column is time used for this iteration (timing information is only available for ``greedy.py``).

If an error threshold is specified, BLASYS will output the smallest circuit under threshold. In folder ``[output folder]/result``,  there is an approximated synthesized verilog file, together with ``result.txt`` which stores area information.
