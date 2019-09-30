# BLASYS: Approximate Logic Synthesis Using Boolean Matrix Factorization
## Introduction
This flow approximates an input circuit (in verilog format) with boolean matrix factorization. It follows a greedy design-space exploration scheme based on each subcircuit. The flow is written in Python3.

## Required packages
###### Yosys: https://github.com/YosysHQ/yosys
###### ABC: https://github.com/berkeley-abc/abc
###### LSOracle: https://github.com/LNIS-Projects/LSOracle
###### Icarus Verilog: http://iverilog.icarus.com

## Usage
1. Install all packages listed in previous section.
2. Open params.yml and fill in path to the corresponding executable. If it is in environment path, just put the executable name.
3. Run BLASYS with following command
```
python3 greedyWorker.py -i [input_verilog] -tb [testbench_verilog] -n [number_of_partitions] -o [output-directory]
```
4. If your machine has multiple cores and you want to run in parallel, please specify ```--parallel``` in argument list.
5. You can either copy input file and testbench to the directory of BLASYS, or run python flow from other directory that contains input file and testbench.
