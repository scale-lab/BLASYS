# BLASYS: Approximate Logic Synthesis Using Boolean Matrix Factorization

A brief video demonstration of BLASYS: https://youtu.be/1mY2Xzn-WnY

## Abstraction
Approximate computing is an emerging paradigm where design accuracy can be traded for improvements in design metrics such as design area and power consumption. In our BLASYS tool-chain, the truth table of a given circuit is approximated using BMF to a controllable approximation degree, and the results of the factorization are used to synthesize the approximate circuit output. BLASYS scales up the computations to large circuits through the use of partition techniques, where an input circuit is partitioned into a number of interconnected subcircuits and then a design-space exploration technique identifies the best order for subcircuit approximations.

## Setup
BLASYS requires ``Python 3.6+``. Please install Python packages ``numpy`` , ``matplotlib`` and ``regex`` with command 
```
pip3 install numpy
pip3 install matplotlib
pip3 install regex
```

Before running the tool-chain, make sure to download and install following tools:
1. **Yosys**: Estimating chip area. (https://github.com/YosysHQ/yosys)
2. **ABC**: Logic synthesis. (https://github.com/berkeley-abc/abc)
3. **Icarus Verilog**: Simulation and HD error estimation. (http://iverilog.icarus.com)
4. **LSOracle**: Partitioning. (https://github.com/LNIS-Projects/LSOracle)
5. [Optional] **OpenSTA**: Power and delay estimation. (https://github.com/The-OpenROAD-Project/OpenSTA)

**IMPORTANT NOTE:** After installing tools above, please **include them into environment path of your system**.

![Flow](https://github.com/scale-lab/BLASYS/blob/master/doc/flow.png?raw=true)

## Usage
### Installation
Enter following command in terminal to clone BLASYS tool-chain.
```
git clone https://github.com/scale-lab/BLASYS
```

### QoR: Testbench and Metric
BLASYS requires a testbench and metric function to evaluate QoR of designs. We provides the script ``testbench.py`` to generate testbench for an input verilog. Please use following command
```
python3 [path to BLASYS folder]/testbench.py \
                 -i PATH_TO_INPUT_VERILOG \
                 -o PATH_TO_OUTPUT_TESTBENCH \
                 [-n NUMBER_OF_TEST_VECTORS]
```
The number of test vectors is optional. Default number is 10,000. However, if total number of input bits is less than 17, it will **enumerate** all possible combinations of test vectors. The generated testbench will output all simulation results for each primary output (which is binary). To match this pattern, we provide 4 metric function in ``utils/metric.py``: ``HD`` (Hamming Distance), ``MAE`` (Mean Absolute Error), ``ER`` (Error Rate), ``MRE`` (Mean Relative Error).

BLASYS also supports customized testbench. However, since metric function must match the pattern of testbench, users should provide metric function with their own testbench. In this case, please write your own **error metric function** in ``utils/metric.py``, and follow the function signature below:
```
def func_name (original_simulation_output_path, approximate_simulation_output_path):
    // The first input is path to the simulation result of original circuit.
    // The first input is path to the simulation result of approximated circuit.
    // Compute error metric here
    
    return error_metric(in float-point number)
```

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
                 [--no_partition] \
                 [--fast_random]
```
Explanation of parameters show in the table below.
| Parameter | Flag | Default | Description |
| --- | --- | --- | --- |
| Input Design | ``-i`` |  |  |
| Testbench | ``-tb`` |  |  |
| Liberty | ``-lib`` | None  | If no liberty file is provided, BLASYS will synthesize circuits into ``NAND`` gates and count the number of ``NAND`` as chip area. |
| Number of Partitions | ``-n`` | Depend on AIG nodes | BLASYS partitions input design recursively in terms of number of AIG nodes. |
| Output Folder | ``-o`` | Module name + Time Stamp |  |
| Step Size | ``-ss`` | 1 |  |
| Metric Function | ``-m`` | HD | Name of metric function. HD (Hamming Distance), MAE (Mean Absolute Error), ER (Error Rate), MRE (Mean Relative Error), or self-defined function. |
| Error Threshold | ``-ts`` | Inf | List of error threshold separated by comma, e.g. ``0.05,0.1,0.15`` |
| Exploration Track | ``-tr`` | 3 | At each iteration, pick ``n`` best designs as starting point of next iteration. |
| Parallel Mode | ``--parallel`` | False | If specified, BLASYS runs in parallel with all available cores of machine. |
| CPU Utilization | ``-cpu`` | All available CPUs | Limit maximum number of cores used in BLASYS.  |
| OpenSTA | ``--sta`` | False | If specified, BLASYS will call OpenSTA to estimate power and delay. **It requires a liberty file.** |
| Approx. Without Partition | ``--no_partition`` | False | If specified, BLASYS will directly factorize truthtable without partitioning.  |
| Random Acceleration | ``--fast_random`` | False | If specified, BLASYS will accelerate design space exploration by random choosing subcircuits in each iteration.  |


### Command-Line Interface
BLASYS also has a command-line interface version. To launch it, type following command in terminal **without** any arguments
````
python3 [path to BLASYS folder]/blasys.py
````
Then, user will be able to type following commands to perform similar tasks as previous section.
#### 1. I/O operation

``read_liberty PATH_TO_LIBERTY`` If no liberty file is provided, BLASYS synthesizes circuits into NAND gates and uses number of cells as chip area. **But if you want to invoke OpenSTA for power and delay estimation, you should provide a liberty file.**

``output_to OUTPUT_FOLDER``

``read_verilog PATH_TO_INPUT``

``read_testbench PATH_TO_TESTBENCH``

#### 2. Circuit Partitioning

 ``partition [-n NUMBER_OF_PARTITIONS]``

#### 3. Configuration

``sta on/off`` Call (or not call) OpenSTA to estimate power and delay.

 ``metric METRIC_FUNCTION_NAME``

``parallel on/off [-cpu NUMBER_OF_CORES_USE]`` Turn on (or turn off) parallel execution. If parallel is on, user can limit maximum number of cores to use.

#### 4. Approximation. Definitions of parameters are same as previous table.
```
blasys [-ts LIST_THRESHOLD] [-s STEP_SIZE] [-tr NUMBER_OF_TRACKS]

OR

run_iter [-i NUMBER_OF_ITERATION] [-ts THRESHOLD] [-s STEP_SIZE] [-tr NUMBER_OF_TRACKS]
```
#### 5. Display results

``stat`` To show the best approximation results of each iteration.

``stat DESIGN_NAME`` To show information about a specific design, which is the name of verilog file in ``tmp/`` folder.

``evaluate PATH_TO_FILE`` To compare the original design with another design (not necessary to be from results of BLASYS).

#### 6. Clear results

``clear``

### Script File
Users may write commands in a script file, and execute BLASYS upon that script file. The command of executing script file is
```
python3 [path to BLASYS folder]/blasys.py -f SCRIPT_FILE
```
In script file, each command takes a single line. An example can be
```
output_to c5315_script_output
read_verilog c5315.v
read_testbench c5315_tb.v
parallel on
metric HD
sta on
partition 35
blasys -ts 0.01,0.02 -tr 3
```

### Test samples
In ``test`` folder, we provide several benchmarks from EPFL combinational benchmark suite [4], ISCAS-85 benchmarks [5], EvoApproxLib[6] together with a runnable script. The command of test script shows below. If no design name is provided, it will execute tests for all benchmarks inside the folder.
```
./test PATH_TO_LIBERTY [DESIGN_NAME]
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

4. Amarú, Luca, Pierre-Emmanuel Gaillardon, and Giovanni De Micheli. "The EPFL combinational benchmark suite." Proceedings of the 24th International Workshop on Logic & Synthesis (IWLS). No. CONF. 2015.
5. Hansen, Mark C., Hakan Yalcin, and John P. Hayes. "Unveiling the ISCAS-85 benchmarks: A case study in reverse engineering." IEEE Design & Test of Computers 16.3 (1999): 72-80.
6. Mrazek, Vojtech, Zdenek Vasicek, and Lukas Sekanina. "EvoApproxLib: Extended Library of Approximate Arithmetic Circuits.", Article No.10, Workshop on Open-Source EDA Technology (WOSET), 2019.

## License
BSD 3-Clause License. See [LICENSE](LICENSE) file
