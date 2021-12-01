import subprocess
import os
import sys
import seraph
import global_params


report = None
current_path = os.getcwd()
source_dir = os.path.join(current_path, "HQ20")
source_file = "contracts/token/ERC20Mintable.sol"
output_path = os.path.join(current_path, "output")

if not os.path.exists(output_path):
    os.makedirs(output_path)

sys.argv = ["", "-s", source_dir, "-j", source_file, "-sol", "-p", "ethereum", "-o", output_path, "-ne"]

seraph.main()

report = global_params.REPORT