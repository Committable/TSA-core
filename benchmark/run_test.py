import subprocess
import os
import sys
import seraph
import global_params


report = None
current_path = os.getcwd()
source_dir = os.path.join(current_path, "uniswap-v2-core")
source_file = "contracts/UniswapV2ERC20.sol"
output_path = os.path.join(current_path, "output")

if not os.path.exists(output_path):
    os.makedirs(output_path)

sys.argv = ["", "-s", source_dir, "-j", source_file, "-sol", "-p", "ethereum", "-o", output_path, "-ne", "-pg"]

seraph.main()