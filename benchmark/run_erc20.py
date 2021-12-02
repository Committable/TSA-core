import subprocess
import os
import sys
import seraph
import global_params


report = None
current_path = os.getcwd()
source_dir = current_path
source_file = "openzeppelin-contracts/token/ERC20/ERC20.sol"
output_path = os.path.join(current_path, "output/ERC20")

if not os.path.exists(output_path):
    os.makedirs(output_path)

sys.argv = ["", "-s", source_dir, "-j", source_file, "-sol", "-p", "ethereum", "-o", output_path, "-ne", "-pg"]

seraph.main()

report = global_params.REPORT