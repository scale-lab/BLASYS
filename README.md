# BLASYS: Approximate Logic Synthesis Using Boolean Matrix Factorization
## Introduction
This flow approximates an input circuit (in verilog format) with boolean matrix factorization. It follows a greedy design-space exploration scheme based on each subcircuit. The flow is written in Python3.

## Required packages
### Yosys: https://github.com/YosysHQ/yosys
### ABC: https://github.com/berkeley-abc/abc
### LSOracle: https://github.com/LNIS-Projects/LSOracle
### Icarus Verilog: http://iverilog.icarus.com

## Usage
### Install all packages listed in previous section.
### Open params.yml and fill in path to the corresponding executable. If it is in environment path, just put the executable name.
### Run BLASYS with following command
```
python3 greedyWorker.py -i [input_verilog] -tb [testbench_verilog] -n [number_of_partitions] -o [output-directory]
```
### If your machine has multiple cores and you want to run in parallel, please specify ```--parallel``` in argument list.
You can either copy input file and testbench to the directory of BLASYS, or run python flow from other directory that contains input file and testbench.
