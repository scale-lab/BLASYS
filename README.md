# BLASYS: Approximate Logic Synthesis Using Boolean Matrix Factorization

## Introduction
BLASYS toolchain reads in an input circuit in Verilog format and approximates with boolean matrix factorization (BMF). The logistic is to generate truthtable for input circuit, perform BMF on truthtable, and synthesize it back to output circuit. Due to the exponential growth of truthtable, we follow a greedy design-space exploration scheme based on each subcircuit. To make the optimization process efficient on even larger circuit, we also develop an additional script to first partition into subcircuits in proper size (based on number of cells), and then do greedy exploration within each part respectively.


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

## Input Format
BLASYS tool reads in a verilog file, and converts to AIG representation for partitioning. The module signature for input circuit should look like
```
module input ( pi0, pi1, pi2, ..., pin, po0, po1, po2, ..., pon );
input pi0, pi1, pi2, ..., pin ;
output pin, po0, po1, po2, ..., pon;
wire ... ;
...
```
The exact variable name does not matter. But you have to make sure that both input pins and output pins are flattened.

## Usage
### Installation
Enter following command in terminal to clone and build BLASYS tool-chain.
```
git clone https://github.com/scale-lab/BLASYS
cd BLASYS
make
```
Before running BLASYS for first time, please open ``config/params.yml`` and enter path to executable files for all tools in previous section. If you have added them into your system environment, you may just enter the command name.

### Script for Greedy Design-Space Exploration
For circuits of small-medium size, ``greedy.py`` is recommended, which performs greedy design-space exploration. The command-line arguments are
```
python3 [path to BLASYS folder]/greedy.py \
                 -i PATH_TO_INPUT_VERILOG \
                 -lib PATH_TO_LIBERTY_FILE \
                 [-n NUMBER_OF_PARTITIONS] \
                 [-tb NUMBER_OF_TEST_VECTORS] \
                 [-o OUTPUT_FOLDER] \
                 [-ts THRESHOLD] \
                 [-ss STEP_SIZE] \
                 [--parallel] \ 
                 [--weight] \
                 [--single]
```
First two arguments (input / testbench) are mandatory. BLASYS takes a recursive partitioning scheme based on number of standard cells. Thus, number of partitions is optional. It also generates test bench automatically. Number of test vectors is optional, too. Default output folder is ``output``. Default step-size is 1. If no threshold ``-ts`` is specified, BLASYS will keep running until all partitions reach factorization degree 1. 

The flag ``--parallel`` indicates parallel mode. If specified, BLASYS will run in parallel with all available cores in your machine.

The flag ``--weight`` indicates weighted metrics. If specified, BLASYS will compute bit significance for error metric. Otherwise, it will use hamming distance error.

The flag ``--single`` indicates whether or not partition. If specified, BLASYS will directly factorize truthtable without partitioning. Otherwise, it will partition before approximation. Note that this mode only supports number of inputs less than or equal to 16.

### Command-Line Interface
1. We also provided an interactive command-line tool option, which is ``blasys.py``. This interface is just a simple version right now and still under development. To launch it, type following command in terminal
````
python3 [path to BLASYS folder]/blasys.py
````
2. To begin with, you should specify the liberty file for synthesis by command
````
read_liberty PATH_TO_LIBERTY
````
3. Next, please specify the input verilog file that you want to approximate. Here, size of test bench file is optional. If no number is provided, it will create a 10000-length testbench for you later on. Afterwards, you should enter the output folder name based on prompt.
```
read_verilog PATH_TO_INPUT [-tb NUMBER_OF_TEST_VECTOR]
```
4. The next step is partitioning.  You may specify the number of partitions you want. Since BLASYS takes a recursive partitioning scheme, it is optional.
```
partitioning [-n NUMBER_OF_PARTITIONS]
```
5. At this step, BLASYS is ready to do approximation. There are two commands. The first one is to do greedy design-space exploration until error threshold is met or all partitions reach factorization degree 1. All arguments are optional. If flag ``-p`` is specified, BLASYS will run in parallel mode. If flag ``-w`` is specified, the error metric will compute weighted error based on bit significance.
```
greedy [-t THRESHOLD] [-s STEP_SIZE] [-p] [-w]
```
Or you may specify the number of iterations by following command. The default number of iteration number is 1.
```
run_iter [-i NUMBER_OF_ITERATION] [-t THRESHOLD] [-s STEP_SIZE] [-p] [-w]
```
6. As mentioned before, BLASYS may directly factorize truth table without partitioning. This can be done by command 
```
blasys [-w]
```
Again, if ``-w`` is specified, error metric uses weighted version.

7. To have a brief view of results, type command ``display_result``. To clear previous approximate work in this session, type command ``clear``.

### Test samples
In ``test`` folder, we provide several benchmarks together with test benches to test functionality. You may run BLASYS with previous instructions. Or locate into ``test`` folder and run the shell script we prepared for you by entering
```
./test [PATH_TO_LIBERTY]
```

## Result
All error-area information is stored in file ``data.csv`` under the output folder. Each line corresponds to the best result of each iteration, where first column is HD error, second column is chip area, and third column is time used for this iteration (timing information is only available for ``greedy.py``).

If an error threshold is specified, BLASYS will output the smallest circuit under threshold. In folder ``[output folder]/result``,  there is an approximated synthesized verilog file, together with ``result.txt`` which stores area information.

## References
1. Ma, J., Hashemi, S. and Reda S., "Approximate Logic Synthesis Using BLASYS", Article No.5, Workshop on Open-Source EDA Technology (WOSET), 2019.
2. Hashemi, S., Tann, H. and Reda, S., 2019. Approximate Logic Synthesis Using Boolean Matrix Factorization. In Approximate Circuits (pp. 141-154). Springer, Cham.
3. Hashemi, S., Tann, H. and Reda, S., 2018, June. BLASYS: approximate logic synthesis using boolean matrix factorization. In Proceedings of the 55th Annual Design Automation Conference (p. 55). ACM.
