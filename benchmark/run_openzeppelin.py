import subprocess
import os
import sys
import seraph
import global_params


report = None
current_path = os.getcwd()
source_dir = os.path.join(current_path, "openzeppelin-contracts")

for path, dir_list, file_list in os.walk(os.path.join(source_dir, "contracts")):
    for file_name in file_list:
        file = os.path.join(path, file_name)
        if os.path.splitext(file)[-1] == ".sol":
            source_file = file.split(source_dir)[1][1:]
            output_path = os.path.join(os.path.join(current_path, "output/openzeppelin"), source_file.split(".sol")[0])

            if not os.path.exists(output_path):
                os.makedirs(output_path)

            sys.argv = ["", "-s", source_dir, "-j", source_file, "-sol", "-p", "ethereum", "-o", output_path, "-ne", "-pg"]

            seraph.main()
