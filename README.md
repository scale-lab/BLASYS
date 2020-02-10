# BLASYS: Approximate Logic Synthesis Using Boolean Matrix Factorization

## Introduction
BLASYS toolchain reads in an input circuit in Verilog format and approximates with boolean matrix factorization (BMF). The logistic is to generate truthtable for input circuit, perform BMF on truthtable, and synthesize it back to output circuit. Due to the exponential growth of truthtable, we follow a greedy design-space exploration scheme based on each subcircuit. To make the optimization process efficient on even larger circuit, we also develop an additional script to first partition into subcircuits in proper size (based on number of cells), and then do greedy exploration within each part respectively.

Version 0.5-beta

## System Requirement
**Operating systems**: Mac OS, Linux, Unix

**Environment**: GCC compiler. Python intepreter (version 3.6+). Please install package ``numpy`` , ``matplotlib`` and ``regex`` with command 
```
pip3 install numpy
pip3 install matplotlib
pip3 install regex
```

## Software Dependency
Be sure to install following tools before running BLASYS toolchain.
1. **Yosys**: Estimating chip area. (https://github.com/YosysHQ/yosys)
2. **ABC**: Logic synthesis. (https://github.com/berkeley-abc/abc)
3. **Icarus Verilog**: Simulation and HD error estimation. (http://iverilog.icarus.com)
4. **LSOracle**: Partitioning. (https://github.com/LNIS-Projects/LSOracle)
5. [Optional] **OpenSTA**: Power and delay estimation. (https://github.com/The-OpenROAD-Project/OpenSTA)

**IMPORTANT NOTE:** After installing tools above, you should either **add them into environment path of your system**, or **put the path to excutable into** ``params.yml``.

![Flow](https://github.com/scale-lab/BLASYS/blob/master/doc/flow.png?raw=true)

## Usage
### Installation
Enter following command in terminal to clone and build BLASYS tool-chain.
```
git clone https://github.com/scale-lab/BLASYS
cd BLASYS
make
```
**IMPORTANT NOTE:** Before running BLASYS for first time, please open ``config/params.yml`` and enter path to executable files for all tools in previous section. If you have added them into your system environment, you may just enter the name of command.

### Testbench Generation
BLASYS provides the script ``testbench.py`` to generate testbench for an input verilog. Please use following command
```
python3 [path to BLASYS folder]/testbench.py \
                 -i PATH_TO_INPUT_VERILOG \
                 -o PATH_TO_OUTPUT_TESTBENCH \
                 [-n NUMBER_OF_TEST_VECTORS]
```
You should specify input verilog file with flag ``-i``, and path to output testbench with flag ``-o``. 

The number of test vectors is optional. Default number is 10,000. However, if total number of input bits is less than 17, it will **enumerate** all possible combinations of test vectors.

### Testbench Customization
Our testbench generation script will create a testbench, where all outputs are in binary bits. BLASYS also supports customized testbench. However, if you bring your own testbench file, make sure to define your own **error metric function**. Please write your own **error metric function** in ``utils/metric.py``, and follow the function signature below:
```
def func_name (original_simulation_output_path, approximate_simulation_output_path):
    // The first input is path to the simulation result of original circuit.
    // The first input is path to the simulation result of approximated circuit.
    // Compute error metric here
    return error_metric
```
After that, you can provide the self-defined function name in command-line. For more detail, please refer to following section.

### Script for Greedy Design-Space Exploration
``blasys.py`` performs greedy design-space exploration with proper command-line arguments, which are
```
python3 [path to BLASYS folder]/blasys.py \
                 -i PATH_TO_INPUT_VERILOG \
                 -tb PATH_TO_TESTBENCH \
                 [-lib PATH_TO_LIBERTY_FILE] \
                 [-n NUMBER_OF_PARTITIONS] \
                 [-o OUTPUT_FOLDER] \
                 [-ss STEP_SIZE] \
                 [-m METRIC_FUNCTION_NAME] \
                 [-ts LIST_THRESHOLD] \
                 [-tr NUMBER_OF_TRACKS] \
                 [--parallel] \ 
                 [-cpu CPU_USED] \
                 [--sta] \
                 [--no_partition]
```
First two arguments (input / testbench) are mandatory.

The third argument ``-lib`` is liberty file. If you do not provide a liberty file, BLASYS will synthesize circuits into NAND gates and count the number as chip area.

The fourth argument ``-n`` is number of partitions. BLASYS takes a recursive partitioning scheme based on number of standard cells. Thus, number of partitions is optional.

Default output ``-o`` is ``output``. Default step-size ``-ss`` is 1. 

For error metric ``-m``, you should put the name of metric function (in ``utils/metric.py``). The default is ``HD``, which refers to Hamming Distance. We also provides ``MAE`` (mean absolute error), ``ER`` (error rate), ``MRE`` (mean relative error). **If you use customized testbench, make sure to implement your own error metric function and use the name of function as argument here.**

For ``--ts``, you can provide a list of error thresholds separated by comma, e.g. ``-ts 0.05,0.10``. If no threshold ``-ts`` is specified, BLASYS will keep running until all partitions reach factorization degree 1. 

For ``--tr``, BLASYS performs multi-track greedy exploration. The default number of tracks is 3.

The flag ``--parallel`` indicates parallel mode. If specified, BLASYS will run in parallel with all available cores in your machine. If you would like to limit the number of cores, write the number as argument of ``-cpu``.

If flag ``--sta`` is specified, BLASYS will invoke OpenSTA to estimate power consumption and circuit delay. **If you want to do that, then liberty file is also mandatory.**

The flag ``--no_partition`` indicates whether or not partition. If specified, BLASYS will directly factorize truthtable without partitioning. Otherwise, it will partition before approximation. Note that this mode only works with circuits whose number of inputs is less than or equal to 16.

### Command-Line Interface
1. We also provided an interactive command-line tool option, which is ``blasys.py``. To launch it, type following command in terminal **without** any arguments
````
python3 [path to BLASYS folder]/blasys.py
````
2. Use following command to specify a liberty file. Again, this is optional. If no liberty file is provided, BLASYS synthesizes circuits into NAND gates and uses number of cells as chip area. **But if you want to invoke OpenSTA for power and delay estimation, you should provide a liberty file.**
````
read_liberty PATH_TO_LIBERTY
````
3. Use following command to provide the verilog file to be approximated.
```
read_verilog PATH_TO_INPUT
```
4. Use following command to provide a testbench file.
```
read_testbench PATH_TO_TESTBENCH
```
5. The next step is partitioning.  You may specify the number of partitions you want. Since BLASYS takes a recursive partitioning scheme, it is optional.
```
partition [-n NUMBER_OF_PARTITIONS]
```
6. Before approximating circuits, here are a few optional configurations. To turn on OpenSTA (for power and delay estimation) or turn off, you can use following command. **However, if you want to use OpenSTA, please provide a liberty file with command** ``read_liberty``.
```
sta on/off
```
To specify the error metric, use following command. **Again, if you want to use customized testbench, please provide a metric function within** ``utils/metric.py``.
```
metric METRIC_FUNCTION_NAME
```
To turn on/off parallel mode in BLASYS, use following command. You are able to limit the number of cores to use. If cpu number is not specified, BLASYS will use all available cores.
```
parallel on/off [-cpu NUMBER_OF_CORES_USE]
```
7. At this step, BLASYS is ready to do approximation. There are two optio. Use following command to do greedy design-space exploration until error threshold is met or all partitions reach factorization degree 1. All arguments are optional. You can provide a list of threshold which are separated by comma, e.g. ``-ts 0.005,0.01``.The default step size is 1. The default number of tracks is 3.
```
blasys [-ts LIST_THRESHOLD] [-s STEP_SIZE] [-tr NUMBER_OF_TRACKS]
```
Or you may specify the number of iterations by following command. The default number of iteration number is 1.
```
run_iter [-i NUMBER_OF_ITERATION] [-ts THRESHOLD] [-s STEP_SIZE] [-tr NUMBER_OF_TRACKS] [-p] [-w]
```
8. To have a brief view of results, type command ``stat``. 

9. To clear previous approximate work in this session, type command ``clear``. Be careful. It will clean everything.

### Test samples
In ``test`` folder, we provide several benchmarks together with test benches to test functionality. You may run BLASYS with previous instructions. Or locate into ``test`` folder and run the shell script we prepared for you by entering
```
./test [PATH_TO_LIBERTY]
```

## Result
All error-area information is stored in file ``data.csv`` under the output folder. Each line corresponds to the best result of each iteration.

If an error threshold is specified, BLASYS will output the smallest circuit under threshold. In folder ``[output folder]/result``,  there is an approximated synthesized verilog file, together with ``result.txt`` which stores area information.

## Known Issue
Since OS X 10.15 has problem with ``multiprocessing`` module in Python 3, parallel mode is not runnable in OS X 10.15 Catalina.

## References
1. Ma, J., Hashemi, S. and Reda S., "Approximate Logic Synthesis Using BLASYS", Article No.5, Workshop on Open-Source EDA Technology (WOSET), 2019.
2. Hashemi, S., Tann, H. and Reda, S., 2019. Approximate Logic Synthesis Using Boolean Matrix Factorization. In Approximate Circuits (pp. 141-154). Springer, Cham.
3. Hashemi, S., Tann, H. and Reda, S., 2018, June. BLASYS: approximate logic synthesis using boolean matrix factorization. In Proceedings of the 55th Annual Design Automation Conference (p. 55). ACM.
