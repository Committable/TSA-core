import logging
import os
import re
import subprocess
import json
import global_params
import solcx
from pathlib import Path
from utils import run_command_with_err

logger = logging.getLogger(__name__)


class SolidityCompiler:
    def __init__(self, source, joker, root_path, allow_paths, remap, compilation_err):
        self.compiled_contracts = []
        self.combined_json = {"contracts": {}, "sources": {}}
        self.source = source
        self.joker = joker
        self.root_path = root_path
        self.allow_paths = allow_paths
        self.remap = remap
        self.compilation_err = compilation_err
        self.path = os.path.join(global_params.TMP_DIR, self.joker.split("/")[-1].split(".")[0])

    def get_compiled_contracts(self):
        if not self.compiled_contracts:
            self.compiled_contracts = self._compile_solidity()
        return self.compiled_contracts

    def get_compiled_contracts_from_json(self):
        if not self.compiled_contracts:
            # 0. try with solcx
            try:
                self._compile_with_solcx()
            except Exception as err1:
                logger.error(err1)
                # 1. try with npx
                try:
                    self._compile_with_npx_waffle()
                except Exception as err2:
                    logger.error(err2)
                    # 2. try with hardhot
                    try:
                        self._compile_with_yarn_hard_hot()
                    except Exception as err3:
                        logger.error(err3)
                        raise Exception("cannot compile target file: %s", self.source+os.sep+self.joker)

        return self.compiled_contracts

    def _compile_with_solcx(self):
        with open(self.source + os.sep + self.joker, 'r') as inputfile:
            version = ""
            line = inputfile.readline()
            while line:
                match_obj = re.match(r'pragma solidity ([=|>|<|\^]*)(\d*\.\d*\.\d*)(;)', line)
                if match_obj:
                    version = match_obj.group(2)
                    break
                line = inputfile.readline()
        if version != "":
            logger.info("get solc version: %s", version)
            solcx.install_solc(match_obj.group(2))
            data_dict = solcx.compile_files( [self.source + os.sep + self.joker],
                                             output_values=["abi", "bin", "bin-runtime", "ast", "asm", "opcodes", "hashes"],
                                             solc_version=version,
                                             allow_empty=True,
                                             allow_paths=self.source
                                             )
            # get runtime bytecode from opcodes
            for key in data_dict:
                file = key.split(":")[0].replace(global_params.SRC_DIR+os.sep,"")
                cname = key.split(":")[-1]

                match_obj = re.match(r'(PUSH1 0x80 PUSH1 0x40 .*) (PUSH1 0x80 PUSH1 0x40 .*)',
                                     data_dict[key]["opcodes"])

                if file not in self.combined_json["contracts"]:
                    self.combined_json["contracts"][file] = {}

                self.combined_json["contracts"][file][cname] = {
                    'evm':
                        {
                            'deployedBytecode':
                                {
                                    'opcodes': "",
                                    "object": data_dict[key]["bin-runtime"]
                                },
                            "bytecode":
                                {
                                    'opcodes': data_dict[key]["opcodes"],
                                    "object": data_dict[key]["bin"]
                                },
                            'legacyAssembly': data_dict[key]["asm"] if "asm" in data_dict[key] else "" ,
                            "methodIdentifiers": data_dict[key]['hashes']
                        }
                }
                if "children" in data_dict[key]["ast"]:
                    self.combined_json["sources"][file] = {
                            "legacyAST": data_dict[key]['ast']
                        }
                    global_params.AST = "legacyAST"
                else:
                    self.combined_json["sources"][file] = {
                        "ast": data_dict[key]['ast']
                    }
                    global_params.AST = "ast"
                if match_obj:
                    self.combined_json["contracts"][file][cname]['evm']['deployedBytecode']['opcodes'] = match_obj.group(2)
                else:
                    self.combined_json["contracts"][file][cname]['evm']['deployedBytecode']['opcodes'] = data_dict[key]["opcodes"]

        self.compiled_contracts = self.combined_json["contracts"][self.joker]

        return

    def _compile_with_npx_waffle(self):
        with open(os.path.join(self.source, ".waffle_bak.json"), 'w') as outputfile:
            bak_config = {
                  "compilerVersion": "./node_modules/solc",
                  "outputType": "all",
                  "compilerOptions":
                      {
                        "outputSelection":
                            {
                              "*": {
                                "*": [
                                  "evm.bytecode.object",
                                  "evm.deployedBytecode.object",
                                  "abi",
                                  "evm.legacyAssembly",
                                  "evm.bytecode.sourceMap",
                                  "evm.deployedBytecode.sourceMap",
                                  "evm.methodIdentifiers"
                                ],
                                "": ["legacyAST"]
                              }
                        },
                      }
                  }
            json.dump(bak_config, outputfile)
        child = subprocess.Popen('npx waffle .waffle_bak.json', cwd=self.source, shell=True, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        try:
            outs, errs = child.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            child.kill()
            outs, errs = child.communicate()
        if child.returncode != 0:
            logger.error(errs)
            logger.error("npx waffle compile fail")
            raise Exception
        # 2. load Combined-Json.json
        with open(self.source + os.sep + 'build' + os.sep + 'Combined-Json.json', 'r') as jsonfile:
            combined_json = json.load(jsonfile)
        for key in combined_json["contracts"]:
            file = key.split(":")[0]
            cname = key.split(":")[1]
            if not self.combined_json["contracts"][file]:
                self.combined_json["contracts"][file] = {}
            self.combined_json["contracts"][file][cname] = combined_json["contracts"][key]
            self.combined_json["sources"][file] = combined_json["sources"][file]["legacyAST"]
        self.compiled_contracts = self.combined_json["contracts"][self.joker]
        global_params.AST = "legacyAST"
        return

    def _compile_with_yarn_hard_hot(self):
        child = subprocess.Popen('yarn compile', cwd=self.source, shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        try:
            outs, errs = child.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            child.kill()
            outs, errs = child.communicate()
        if child.returncode != 0:
            logger.critical(errs)
            logger.critical("yarn compile fail")
            raise Exception
        filePath = self.source + os.sep + 'artifacts' + os.sep + "build-info"
        fileName = ""
        with open(filePath + os.sep + fileName[0], 'r') as jsonfile:
            combined_json = json.load(jsonfile)
        self.combined_json["contracts"] = combined_json['output']["contracts"]
        self.combined_json["sources"] = combined_json['output']["sources"]

        self.compiled_contracts = self.combined_json['contracts'][self.joker]
        global_params.AST = "ast"
        return

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
                    logger.critical("Solidity compilation failed. Please use -ce flag to see the detail.")
                else:
                    logger.critical(err)
                    logger.critical("Solidity compilation failed.")
                exit(1)

        return contracts

