# BLASYS: Approximate Logic Synthesis Using Boolean Matrix Factorization

## Introduction
BLASYS toolchain reads in an input circuit in Verilog format and approximates with boolean matrix factorization (BMF). The logistic is to generate truthtable for input circuit, perform BMF on truthtable, and synthesize it back to output circuit. Due to the exponential growth of truthtable, we follow a greedy design-space exploration scheme based on each subcircuit. To make the optimization process efficient on even larger circuit, we also develop an additional script to first partition into subcircuits in proper size (based on number of cells), and then do greedy exploration within each part respectively.

![Flow](https://github.com/scale-lab/BLASYS/blob/master/doc/BMF.png?raw=true)

## System Requirement
**Operating systems**: Mac OS, Linux, Unix

**Environment**: GCC compiler. Python intepreter (version 3.6+). Be sure to install package ``numpy`` and ``matplotlib`` with command 
```
pip3 install numpy
pip3 install matplotlib
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
#### Installation
Enter following command in terminal to clone and build BLASYS tool-chain.
```
git clone https://github.com/scale-lab/BLASYS
cd BLASYS
make
```
Before running BLASYS for first time, please open ``config/params.yml`` and enter path to executable files for all tools in previous section. If you have added them into your system environment, you may just enter the command name.

#### Script for Greedy Design-Space Exploration
For circuits of small-medium size, ``greedy.py`` is recommended, which performs greedy design-space exploration. The command-line arguments are
```
python3 [path to BLASYS folder]/greedy.py \
                 -i PATH_TO_INPUT_VERILOG \
                 -tb PATH_TO_TESTBENCH \
                 -lib PATH_TO_LIBERTY_FILE \
                 [-n NUMBER_OF_PARTITIONS] \
                 [-o OUTPUT_FOLDER] \
                 [-ts THRESHOLD] \
                 [-ss STEP_SIZE] \
                 [--parallel]
```
First three arguments (input / testbench / liberty file) are mandatory. BLASYS takes a recursive partitioning scheme based on number of standard cells. Thus, number of partitions is optional. Default output folder is ``output``. Default step-size is 1. If no threshold ``-ts`` is specified, BLASYS will keep running until all partitions reach factorization degree 1. The last flag ``--parallel`` indicates parallel mode. If specified, BLASYS will run in parallel with all available cores in your machine.

#### Script for Two-Level Partitioning
For larger circuit, you may find that simulation process takes too much time. in this case, there is another script ``recursive.py``, which will first partition large circuit into proper size, and then do BLASYS on each sub-circuit. The usage is
```
python3 [path to BLASYS folder]/recursive.py \
                 -i PATH_TO_INPUT_VERILOG \
                 -tb PATH_TO_TESTBENCH \
                 -lib PATH_TO_LIBERTY_FILE \
                 [-o OUTPUT_FOLDER] \
                 [-ts THRESHOLD] \
                 [-ss STEP_SIZE] \
                 [--parallel]

```
Definitions of command-line arguments are same as previous section.

#### Command-Line Interface
1. We also provided an interactive command-line tool option, which is ``blasys.py``. This interface is just a simple version right now and still under development. To launch it, type following command in terminal
````
python3 [path to BLASYS folder]/blasys.py
````
2. To begin with, you should specify the liberty file for synthesis by command
````
read_liberty PATH_TO_LIBERTY
````
3. Next, please specify the input verilog file that you want to approximate. Here, testbench file is optional. If no testbench is provided, it will create a 5000-length testbench for you later on.
```
read_verilog PATH_TO_INPUT [-tb PATH_TO_TESTBENCH]
```
4. The next step is partitioning. You should enter a path in first argument, where BLASYS will create and output all results into that folder. You may also specify the number of partitions you want. Since BLASYS takes a recursive partitioning scheme, it is optional
```
partitioning OUTPUT_FOLDER [-n NUMBER_OF_PARTITIONS]
```
5. At this step, BLASYS is ready to do approximation. There are two commands. The first one is to do greedy design-space exploration until error threshold is met or all partitions reach factorization degree 1. All arguments are optional. If flag ``-p`` is specified, BLASYS will run in parallel mode.
```
greedy [-t THRESHOLD] [-s STEP_SIZE] [-p]
```
Or you may specify the number of iterations by following command. The default number of iteration number is 1.
```
run_iter [-i NUMBER_OF_ITERATION] [-t THRESHOLD] [-s STEP_SIZE] [-p]
```
6. To have a brief view of results, type command ``display_result``. To clear previous approximate work in this session, type command ``clear``.

## Result
All error-area information is stored in file ``data.csv`` under the output folder. Each line corresponds to the best result of each iteration, where first column is HD error, second column is chip area, and third column is time used for this iteration (timing information is only available for ``greedy.py``).

If an error threshold is specified, BLASYS will output the smallest circuit under threshold. In folder ``[output folder]/result``,  there is an approximated synthesized verilog file, together with ``result.txt`` which stores area information.
