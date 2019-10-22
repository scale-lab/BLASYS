# BLASYS: Approximate Logic Synthesis Using Boolean Matrix Factorization
BLASYS toolchain reads an input circuit in Verilog format and approximates with boolean matrix factorization (BMF). The logistic is to generate truthtable for input circuit, perform BMF on truthtable, and synthesize it back to output circuit. Due to the exponential growth of truthtable, we follow a greedy design-space exploration scheme based on each subcircuit. To make the optimization process efficient on even larger circuit, we also develop an additional script to first partition into subcircuits in proper size (based on number of cells), and then do greedy exploration within each part respectively.

## System Requirement
**Operating systems**: Windows, Mac OS, Linux, Unix

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
1. Install all packages listed in previous section.
2. Open params.yml and fill in path to the corresponding executable. If it is in environment path, just put the executable name.
3. Run BLASYS with following command
```
python3 greedyWorker.py -i [input_verilog] -tb [testbench_verilog] -n [number_of_partitions] -o [output-directory]
```
4. If your machine has multiple cores and you want to run in parallel, please specify ```--parallel``` in argument list.
5. You can either copy input file and testbench to the directory of BLASYS, or run python flow from other directory that contains input file and testbench.
