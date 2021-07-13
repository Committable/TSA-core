import logging
import os
import re
import subprocess
import json
from utils import run_command_with_err


class SolidityCompiler:
    def __init__(self, source, root_path, allow_paths, remap, compilation_err, tmp_path):
        self.compiled_contracts = []
        self.combined_json = None
        self.source = source
        self.root_path = root_path
        self.allow_paths = allow_paths
        self.remap = remap
        self.compilation_err = compilation_err
        self.path = tmp_path + self.source.split("/")[-1].split(".")[0]
        if not os.path.exists(self.path):
            os.mkdir(self.path)


    def get_compiled_contracts(self):
        if not self.compiled_contracts:
            self.compiled_contracts = self._compile_solidity()
        return self.compiled_contracts

    def get_compiled_contracts_from_json(self):
        if not self.compiled_contracts:
            # 1. compile with npx waffle
            child = subprocess.Popen('npx waffle .waffle.json', cwd=self.source, shell=True, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
            try:
                outs, errs = child.communicate(timeout=15)
            except subprocess.TimeoutExpired:
                child.kill()
                outs, errs = child.communicate()
            if child.returncode != 0:
                logging.critical(errs)
                logging.critical("npx waffle compile fail")
                exit(1)
            # 2. load Combined-Json.json
            with open(self.source+os.sep+'build'+os.sep+'Combined-Json.json', 'r') as jsonfile:
                combined_json = json.load(jsonfile)
            self.combined_json = combined_json

            self.compiled_contracts = combined_json['contracts']
        return self.compiled_contracts

    def _compile_solidity(self):
        if not self.allow_paths:
            cmd = "solc --bin-runtime %s %s -o %s" % (self.remap, self.source, self.path)
        else:
            cmd = "solc --bin-runtime %s %s --allow-paths %s -o %s" % (
                self.remap, self.source, self.allow_paths, self.path)

        out, err = run_command_with_err(cmd)
        err = re.sub(self.root_path, "", err)

        return self._extract_bin_str(err)

    def _extract_bin_str(self, err):
        contracts = {}
        for root, dirs, files in os.walk(self.path):
            for file_name in files:
                if file_name.endswith(".bin-runtime"):
                    with open(os.path.join(root, file_name)) as f:
                        bytecodes = f.read()
                    contracts[os.path.join(root, file_name)] = bytecodes

            if len(contracts) == 0:
                if not self.compilation_err:
                    logging.critical("Solidity compilation failed. Please use -ce flag to see the detail.")
                else:
                    logging.critical(err)
                    logging.critical("Solidity compilation failed.")
                exit(1)

        return contracts

