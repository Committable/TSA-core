import logging
import os
import re
import subprocess
import json
import solcx
import signal
import shutil

from pyevmasm import disassemble_hex

import global_params

logger = logging.getLogger(__name__)


class AllowedVersion: # left [<=|<] allow_version [<=|<]
    def __init__(self):
        self.unique = ""
        self.right = ""
        self.left = ""
        self.right_equal = False
        self.left_equal = False

    def set_right(self, right, equal):
        self.right = right
        self.right_equal = equal

    def set_unique(self, version):
        self.unique = version

    def set_left(self, left, equal):
        self.left = left
        self.left_equal = equal

    @staticmethod
    def is_bigger(version1, version2):
        try:
            parts1 = version1.split(".")
            parts2 = version2.split(".")
            length = len(parts1) if len(parts1) <= len(parts2) else len(parts2)
            for x in range(0, length):
                if int(parts1[x]) > int(parts2[x]):
                    return True
                elif int(parts1[x]) < int(parts2[x]):
                    return False
            return len(parts1) > len(parts2)
        except:
            return False

    @staticmethod
    def is_smaller(version1, version2):
        try:
            parts1 = version1.split(".")
            parts2 = version2.split(".")
            length = len(parts1) if len(parts1) <= len(parts2) else len(parts2)
            for x in range(0, length):
                if int(parts1[x]) < int(parts2[x]):
                    return True
                elif int(parts1[x]) > int(parts2[x]):
                    return False
            return len(parts1) > len(parts2)
        except:
            return False

    def is_allow(self, version):
        if self.unique:
            return version == self.unique
        elif self.left == "" or self.is_bigger(version, self.left):
            if self.right == "" or self.is_smaller(version, self.right):
                return True
        else:
            return False

    def get_version(self):
        # versions = list(solcx.get_installable_solc_versions())
        versions = ['0.8.10', '0.8.9', '0.8.8', '0.8.7', '0.8.6', '0.8.5', '0.8.4', '0.8.3', '0.8.2', '0.8.1', '0.8.0', '0.7.6', '0.7.5', '0.7.4', '0.7.3', '0.7.2', '0.7.1', '0.7.0', '0.6.12', '0.6.11', '0.6.10', '0.6.9', '0.6.8', '0.6.7', '0.6.6', '0.6.5', '0.6.4', '0.6.3', '0.6.2', '0.6.1', '0.6.0', '0.5.17', '0.5.16', '0.5.15', '0.5.14', '0.5.13', '0.5.12', '0.5.11', '0.5.10', '0.5.9', '0.5.8', '0.5.7', '0.5.6', '0.5.5', '0.5.4', '0.5.3', '0.5.2', '0.5.1', '0.5.0', '0.4.26', '0.4.25', '0.4.24', '0.4.23', '0.4.22', '0.4.21', '0.4.20', '0.4.19', '0.4.18', '0.4.17', '0.4.16', '0.4.15', '0.4.14', '0.4.13', '0.4.12', '0.4.11']
        current = "0.4.11"
        for x in versions:
            if self.is_allow(str(x)) and self.is_bigger(str(x), current):
                current = str(x)
                break

        return current

    def get_versions(self):
        result = set()
        versions = ['0.8.10', '0.8.9', '0.8.8', '0.8.7', '0.8.6', '0.8.5', '0.8.4', '0.8.3', '0.8.2', '0.8.1', '0.8.0', '0.7.6', '0.7.5', '0.7.4', '0.7.3', '0.7.2', '0.7.1', '0.7.0', '0.6.12', '0.6.11', '0.6.10', '0.6.9', '0.6.8', '0.6.7', '0.6.6', '0.6.5', '0.6.4', '0.6.3', '0.6.2', '0.6.1', '0.6.0', '0.5.17', '0.5.16', '0.5.15', '0.5.14', '0.5.13', '0.5.12', '0.5.11', '0.5.10', '0.5.9', '0.5.8', '0.5.7', '0.5.6', '0.5.5', '0.5.4', '0.5.3', '0.5.2', '0.5.1', '0.5.0', '0.4.26', '0.4.25', '0.4.24', '0.4.23', '0.4.22', '0.4.21', '0.4.20', '0.4.19', '0.4.18', '0.4.17', '0.4.16', '0.4.15', '0.4.14', '0.4.13', '0.4.12', '0.4.11']
        for x in versions:
            if self.is_allow(str(x)):
                result.add(x)

        return result

    def merge(self, other_version):
        if other_version.unique and self.unique:
            if other_version.unique == self.unique:
                return self
            else:
                return None
        elif other_version.unique and not self.unique:
            if self.is_allow(other_version.unique):
                return other_version
            else:
                return None
        elif not other_version.unique and self.unique:
            if other_version.is_allow(self.unique):
                return self
            else:
                return None
        else:
            version = AllowedVersion()

            if other_version.right and self.right:
                if other_version.right == self.right:
                    version.set_right(other_version.right, other_version.right_equal and self.right_equal)
                elif self.is_bigger(other_version.right, self.right):
                    version.set_right(self.right, self.right_equal)
                else:
                    version.set_right(other_version.right, other_version.right_equal)
            elif other_version.right:
                version.set_right(other_version.right, other_version.right_equal)
            elif self.right:
                version.set_right(self.right, self.right_equal)

            if other_version.left and self.left:
                if other_version.left == self.left:
                    version.set_left(other_version.left, other_version.left_equal and self.left_equal)
                elif self.is_bigger(self.left, other_version.left):
                    version.set_left(self.left, self.left_equal)
                else:
                    version.set_left(other_version.left, other_version.left_equal)
            elif other_version.left:
                version.set_left(other_version.left, other_version.left_equal)
            elif self.left:
                version.set_left(self.left, self.left_equal)

            if version.right and version.left:
                if version.is_bigger(version.left, version.right):
                    return None
                elif version.right == version.left and not (version.right_equal and version.left_equal):
                    return None

            return version

    def __str__(self):
        if self.unique:
            return "version==" + self.unique
        expr = "version"
        if self.left:
            if self.left_equal:
                expr = self.left + "<=" + expr
            else:
                expr = self.left + "<=" + expr
        if self.right:
            if self.right_equal:
                expr = expr + "<=" + self.right
            else:
                expr = expr + "<" + self.right
        return expr


class SolidityCompiler:
    def __init__(self, source, joker, root_path, allow_paths, remap, compilation_err):
        self.combined_json = {"contracts": {}, "sources": {}}  # compile result of json type

        self.source = source  # source dir of project
        self.joker = joker  # relative dir of the analyse file

        self.root_path = root_path
        self.allow_paths = allow_paths
        self.remap = remap
        self.compilation_err = compilation_err

        self.type = "unknown"

        self.parse_files = []

        self.all_versions = set()
        self.final_version = None

    def get_compiled_contracts_as_json(self):
        # 1. try with solcx
        try:
            self._compile_with_solcx()
            self.type = "solcx"
            self._convert_opcodes()
            return
        except Exception as err:
            logger.info("Can not compile with solcx: ")
            logger.info(str(err))

        # 2. try with detected compiler
        self._detect_built_in_compilation_type()
        if self.type != "unkonwn":
            self._get_all_versions()

        if self.type == "waffle":
            self._compile_with_waffle()
        elif self.type == "hardhat":
            self._compile_with_hardhat()
        elif self.type == "truffle":
            self._compile_with_truffle()
        elif self.type == "buidler":
            self._compile_with_buidler()
        else:
            raise Exception("Can not detect built-in compilation type")

        self._rm_compiled_files()
        return

    def _compile_with_solcx(self):
        # 1. get compiler version
        allowed_version = self._get_solc_version_with_import(os.path.join(self.source, self.joker))
        if allowed_version is None:
            allowed_version = AllowedVersion()
            allowed_version.set_unique("0.8.0")

        version = allowed_version.get_version()
        logger.info("get solc version: %s", version)

        # 2. compile
        solcx.install_solc(version)
        if allowed_version.is_bigger(version, "0.4.25"):
            data_dict = solcx.compile_files([self.source + os.sep + self.joker],
                                            output_values=["abi", "bin", "bin-runtime", "ast",
                                                           "hashes", "opcodes", "srcmap-runtime"],
                                            allow_empty=True,
                                            allow_paths=self.source,
                                            solc_version=version,
                                            )
        else:
            data_dict = solcx.compile_files([self.source + os.sep + self.joker],
                                            output_values=["abi", "bin", "bin-runtime", "ast",
                                                           "opcodes", "srcmap-runtime"],
                                            allow_empty=True,
                                            allow_paths=self.source,
                                            solc_version=version,
                                            )

        # 3. convert json result format
        for key in data_dict:
            file = key.split(":")[0].replace(global_params.SRC_DIR+os.sep, "")
            cname = key.split(":")[-1]

            if file not in self.combined_json["contracts"]:
                self.combined_json["contracts"][file] = {}

            self.combined_json["contracts"][file][cname] = {
                'evm':
                    {
                        'deployedBytecode':
                            {
                                'opcodes': "",
                                "object": data_dict[key]["bin-runtime"],
                                "sourceMap": data_dict[key]["srcmap-runtime"]
                            },
                        "bytecode":
                            {
                                'opcodes': data_dict[key]["opcodes"],
                                "object": data_dict[key]["bin"]
                            },
                        "methodIdentifiers": data_dict[key]["hashes"] if "hashes" in data_dict[key] else {}
                    },
            }

            # 3.1 legacyAST and ast
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

        return

    def _detect_built_in_compilation_type(self):
        try:
            if os.path.exists(os.path.join(self.source,
                                           "hardhat.config.js")):
                self.type = "hardhat"
            elif os.path.exists(os.path.join(self.source,
                                             ".waffle.json")):
                self.type = "waffle"
            elif os.path.exists(os.path.join(self.source,
                                             "buidler.config.js")):
                self.type = "buidler"
            elif os.path.exists(os.path.join(self.source,
                                             "truffle-config.js")) or \
                os.path.exists(os.path.join(self.source,
                                            "truffle.js")):
                self.type = "truffle"
            else:
                self.type = "unknown"
        except Exception as err:
            self.type = "unknown"

    def _compile_with_waffle(self):
        # 1. compile with default config
        with open(os.path.join(self.source, ".waffle_bak.json"), 'w') as outputfile:
            bak_config = {
                  "compilerVersion": "./node_modules/solc",
                  "outputType": "all",
                  "compilerOptions": {
                        "outputSelection": {
                              "*": {
                                "*": [
                                  "evm.bytecode.object",
                                  "evm.deployedBytecode.object",
                                  "abi",
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
            outs, errs = child.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            child.kill()
            child.terminate()
            os.killpg(child.pid, signal.SIGTERM)
            os.remove(os.path.join(self.source, ".waffle_bak.json"))
            raise Exception("npx waffle compile fail: timeout")

        os.remove(os.path.join(self.source, ".waffle_bak.json"))
        if child.returncode != 0:
            raise Exception("npx waffle compile fail: %s", errs)

        # 2. load Combined-Json.json
        with open(os.path.join(self.source, 'build' + os.sep + 'Combined-Json.json'), 'r') as json_file:
            result_json = json.load(json_file)

        for key in result_json["contracts"]:
            file = key.split(":")[0]
            cname = key.split(":")[1]
            if file not in self.combined_json["contracts"]:
                self.combined_json["contracts"][file] = {}
            self.combined_json["contracts"][file][cname] = result_json["contracts"][key]
            if file not in self.combined_json["sources"]:
                self.combined_json["sources"][file] = {"legacyAST": result_json["sources"][file]["legacyAST"]}
        global_params.AST = "legacyAST"

        return

    def _get_all_versions(self):
        for path, dir_list, file_list in os.walk(os.path.join(self.source, "contracts")):
            for file_name in file_list:
                file = os.path.join(path, file_name)
                if os.path.splitext(file)[-1] == ".sol":
                    version = self._get_solc_version_without_import(file)
                    if self.final_version is None:
                        self.final_version = version
                    else:
                        self.final_version = self.final_version.merge(version)
                    self.all_versions.add(version.get_version())

        return

    def _compile_with_hardhat(self):
        try:
            if os.path.exists(os.path.join(self.source, "hardhat.config.js")):
                os.rename(os.path.join(self.source, "hardhat.config.js"),
                          os.path.join(self.source, ".tmp.hardhat.config.js"))
        except:
            pass

        with open(os.path.join(self.source, "hardhat.config.js"), 'w') as output_file:
            version_str = "[\n"
            flag = False
            for v in self.all_versions:
                if flag:
                    version_str = version_str + ",\n"
                else:
                    flag = True
                version_str = version_str + "      { version: \"" + v + "\",\n" + \
                              "settings: {optimizer: {enabled: true,runs: 200}}" + \
                              "\n}"
            version_str = version_str + "\n    ]"

            output_file.write('module.exports = {\n' +
                              '  solidity: {\n' +
                              '    compilers: ' + version_str +
                              '  }\n' +
                              '}')
        child = subprocess.Popen('npx hardhat compile', cwd=self.source, shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        try:
            outs, errs = child.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            child.kill()
            child.terminate()
            os.killpg(child.pid, signal.SIGTERM)
            os.remove(os.path.join(self.source, "hardhat.config.js"))
            try:
                if os.path.exists(os.path.join(self.source, ".tmp.hardhat.config.js")):
                    os.rename(os.path.join(self.source, ".tmp.hardhat.config.js"),
                              os.path.join(self.source, "hardhat.config.js"))
            except:
                pass
            raise Exception("npx waffle compile fail: timeout")

        os.remove(os.path.join(self.source, "hardhat.config.js"))
        try:
            if os.path.exists(os.path.join(self.source, ".tmp.hardhat.config.js")):
                os.rename(os.path.join(self.source, ".tmp.hardhat.config.js"),
                          os.path.join(self.source, "hardhat.config.js"))
        except:
            pass

        if child.returncode != 0:
            raise Exception("harhat compile fail: %s", errs)
        filePath = os.path.join(self.source, 'artifacts' + os.sep + "build-info")
        for i, j, files in os.walk(filePath):
            for file in files:
                with open(filePath + os.sep + file, 'r') as jsonfile:
                    single_json = json.load(jsonfile)
                    if self.joker in single_json['output']["contracts"] or self.joker in single_json['output']["sources"]:
                        self.combined_json["contracts"] = single_json['output']["contracts"]
                        self.combined_json["sources"] = single_json['output']["sources"]
                        global_params.AST = "ast"
                        return

    def _compile_with_truffle(self):
        if os.path.exists(os.path.join(self.source, "truffle.js")):
            os.rename(os.path.join(self.source, "truffle.js"), os.path.join(self.source, ".tmp.truffle.js"))
        if os.path.exists(os.path.join(self.source, "truffle-config.js")):
            os.rename(os.path.join(self.source, "truffle-config.js"),
                      os.path.join(self.source, ".tmp.truffle-config.js"))

        all_versions = set()
        if self.final_version is not None:
            all_versions = self.final_version.get_versions()

        for x in all_versions:
            with open(os.path.join(self.source, "truffle.js"), 'w') as outputfile:
                if self.final_version is not None:
                    bak_config = "module.exports = { compilers: {solc: { version: \'" + \
                                 x + "\'" + \
                                 "} } };"
                else:
                    bak_config = "module.exports = {};"
                outputfile.write(bak_config)

            child = subprocess.Popen('npx truffle compile', cwd=self.source, shell=True,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
            try:
                outs, errs = child.communicate(timeout=60)
            except subprocess.TimeoutExpired:
                child.kill()
                child.terminate()
                os.killpg(child.pid, signal.SIGTERM)
                continue

            if child.returncode != 0:
                continue
            os.remove(os.path.join(self.source, "truffle.js"))
            if os.path.exists(os.path.join(self.source, ".tmp.truffle.js")):
                os.rename(os.path.join(self.source, ".tmp.truffle.js"), os.path.join(self.source, "truffle.js"))
            if os.path.exists(os.path.join(self.source, ".tmp.truffle-config.js")):
                os.rename(os.path.join(self.source, ".tmp.truffle-config.js"),
                          os.path.join(self.source, "truffle-config.js"))
            self._deal_with_truffle()
            self._convert_opcodes()
            return

        os.remove(os.path.join(self.source, "truffle.js"))
        if os.path.exists(os.path.join(self.source, ".tmp.truffle.js")):
            os.rename(os.path.join(self.source, ".tmp.truffle.js"), os.path.join(self.source, "truffle.js"))
        if os.path.exists(os.path.join(self.source, ".tmp.truffle-config.js")):
            os.rename(os.path.join(self.source, ".tmp.truffle-config.js"),
                      os.path.join(self.source, "truffle-config.js"))
        raise Exception("Can not compile with truffle.")

    def _compile_with_buidler(self):
        child = subprocess.Popen('npx buidler compile', cwd=self.source, shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        try:
            outs, errs = child.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            child.kill()
            child.terminate()
            os.killpg(child.pid, signal.SIGTERM)
            raise Exception("npx waffle compile fail: timeout")
        if child.returncode != 0:
            raise Exception("harhat compile fail: %s", errs)
        self._deal_with_buidler()

    def _deal_with_truffle(self):
        if not os.path.exists(os.path.join(self.source, "build/contracts", self.joker.split(os.sep)[-1].split(".")[0]+".json")):
            raise Exception("result not in build dir")
        with open(os.path.join(self.source, "build/contracts", self.joker.split(os.sep)[-1].split(".")[0]+".json")) as jsonfile:
            result = json.load(jsonfile)
            file = self.joker
            cname = result["contractName"]
            self.combined_json["contracts"][file] = {}
            self.combined_json["contracts"][file][cname] = {
                'evm':
                    {
                        'deployedBytecode':
                            {
                                'opcodes': "",
                                "object": result["deployedBytecode"] if "deployedBytecode" in result else "",
                                "sourceMap": result["deployedSourceMap"] if "deployedSourceMap" in result else ""
                            },
                        "bytecode":
                            {
                                'opcodes': "",
                                "object": result["bytecode"] if "deployedSourceMap" in result else ""
                            },
                    }
            }
            self.combined_json["sources"][file] = {
                "ast": result['ast'] if "deployedSourceMap" in result else ""
            }
            global_params.AST = "ast"
        return

    def _deal_with_buidler(self):
        if not os.path.exists(os.path.join(self.source, "cache/solc-output.json")):
            raise Exception("buidler result not exit")
        with open(os.path.join(self.source, "cache/solc-output.json"), 'r') as jsonfile:
            self.combined_json = json.load(jsonfile)
            global_params.AST = "ast"
        return

    def _convert_opcodes(self):
        if "contracts":
            for file in self.combined_json["contracts"]:
                for cname in self.combined_json["contracts"][file]:
                    x = self.combined_json["contracts"][file][cname]
                    deployed_bytecode_object = x["evm"]["deployedBytecode"]['object']
                    if deployed_bytecode_object:
                        x["evm"]["deployedBytecode"]['opcodes'] = disassemble_hex(deployed_bytecode_object).replace("\n", " ")

                    bytecode_object = x["evm"]["bytecode"]['object']
                    if bytecode_object and not x["evm"]["bytecode"]['opcodes']:
                        x["evm"]["bytecode"]['opcodes'] = disassemble_hex(bytecode_object).replace("\n", " ")

    def _rm_compiled_files(self):
        if os.path.exists(os.path.join(self.source, "build")):
            shutil.rmtree(os.path.join(self.source, "build"))
        if os.path.exists(os.path.join(self.source, "artifacts")):
            shutil.rmtree(os.path.join(self.source, "artifacts"))
        if os.path.exists(os.path.join(self.source, "cache")):
            shutil.rmtree(os.path.join(self.source, "cache"))

    def _get_solc_version_with_import(self, file):
        if file in self.parse_files:
            return None
        self.parse_files.append(file)
        import_files = []
        with open(file, 'r') as inputfile:
            version = AllowedVersion()
            lines = inputfile.readlines()
            i = 0
            for line in lines:
                match_obj = re.match(r'pragma solidity (=)(\d*\.\d*\.\d*)(.*)\n', line)
                if match_obj:
                    version.set_unique(match_obj.group(2))
                    break
                match_obj = re.match(r'pragma solidity (\d*\.\d*\.\d*)(.*)\n', line)
                if match_obj:
                    version.set_unique(match_obj.group(2))
                    break
                match_obj = re.match(r'pragma solidity (\^)(\d*\.\d*\.\d*)(.*)\n', line)
                if match_obj:
                    version.set_left(match_obj.group(2), True)
                    parts = match_obj.group(2).split(".")
                    right = parts[0] + "." + str(int(parts[1])+1) + ".0"
                    version.set_right(right, False)
                    break
                match_obj = re.match(r'pragma solidity (>=)(\d*\.\d*\.\d*)(.*)(<=)(\d*\.\d*\.\d*)(.*)\n', line)
                if match_obj:
                    version.set_left(match_obj.group(2), True)
                    version.set_right(match_obj.group(5), True)
                    break
                match_obj = re.match(r'pragma solidity (>)(\d*\.\d*\.\d*)(.*) (<=)(\d*\.\d*\.\d*)(.*)\n', line)
                if match_obj:
                    version.set_left(match_obj.group(2), False)
                    version.set_right(match_obj.group(5), True)
                    break
                match_obj = re.match(r'pragma solidity (>=)(\d*\.\d*\.\d*)(.*) (<)(\d*\.\d*\.\d*)(.*)\n', line)
                if match_obj:
                    version.set_left(match_obj.group(2), True)
                    version.set_right(match_obj.group(5), False)
                    break
                match_obj = re.match(r'pragma solidity (>)(\d*\.\d*\.\d*)(.*) (<)(\d*\.\d*\.\d*)(.*)\n', line)
                if match_obj:
                    version.set_left(match_obj.group(2), False)
                    version.set_right(match_obj.group(5), False)
                    break
                match_obj = re.match(r'pragma solidity (<=)(\d*\.\d*\.\d*)(.*)\n', line)
                if match_obj:
                    version.set_right(match_obj.group(2), True)
                    break
                match_obj = re.match(r'pragma solidity (>)(\d*\.\d*\.\d*)(.*)\n', line)
                if match_obj:
                    version.set_left(match_obj.group(2), False)
                    break
                match_obj = re.match(r'pragma solidity (<)(\d*\.\d*\.\d*)(.*)\n', line)
                if match_obj:
                    version.set_right(match_obj.group(2), False)
                    break
                match_obj = re.match(r'pragma solidity (>=)(\d*\.\d*\.\d*)(.*)\n', line)
                if match_obj:
                    version.set_left(match_obj.group(2), True)
                    break
                match_obj = re.match(r'pragma solidity ([=|>|<|\^]*)(\d*\.\d*\.\d*)(.*)\n', line)
                if match_obj:
                    version.set_unique(match_obj.group(2), True)
                    break
                i += 1
            wrong_times = 0
            for line in lines[i:]:
                match_obj = re.match(r'import ["|\'](.*)["|\'];\n', line)
                if match_obj:
                    import_files.append(match_obj.group(1))
                else:
                    if line != "\n":
                        wrong_times += 1
                        if wrong_times >= 3:
                            break
            logger.info(lines[i])
            logger.info(version)
        current_dir = os.path.dirname(file)
        for x in import_files:
            other_version = self._get_solc_version_with_import(os.path.abspath(os.path.join(current_dir, x)))
            if version and other_version:
                version = version.merge(other_version)
                if version is None:
                    return None

        return version

    def _get_solc_version_without_import(self, file):
        with open(file, 'r') as inputfile:
            version = AllowedVersion()
            lines = inputfile.readlines()
            for line in lines:
                match_obj = re.match(r'pragma solidity (=)(\d*\.\d*\.\d*)(.*)\n', line)
                if match_obj:
                    version.set_unique(match_obj.group(2))
                    break
                match_obj = re.match(r'pragma solidity (\d*\.\d*\.\d*)(.*)\n', line)
                if match_obj:
                    version.set_unique(match_obj.group(2))
                    break
                match_obj = re.match(r'pragma solidity (\^)(\d*\.\d*\.\d*)(.*)\n', line)
                if match_obj:
                    version.set_left(match_obj.group(2), True)
                    parts = match_obj.group(2).split(".")
                    right = parts[0] + "." + str(int(parts[1])+1) + ".0"
                    version.set_right(right, False)
                    break
                match_obj = re.match(r'pragma solidity (>=)(\d*\.\d*\.\d*)(.*)(<=)(\d*\.\d*\.\d*)(.*)\n', line)
                if match_obj:
                    version.set_left(match_obj.group(2), True)
                    version.set_right(match_obj.group(5), True)
                    break
                match_obj = re.match(r'pragma solidity (>)(\d*\.\d*\.\d*)(.*) (<=)(\d*\.\d*\.\d*)(.*)\n', line)
                if match_obj:
                    version.set_left(match_obj.group(2), False)
                    version.set_right(match_obj.group(5), True)
                    break
                match_obj = re.match(r'pragma solidity (>=)(\d*\.\d*\.\d*)(.*) (<)(\d*\.\d*\.\d*)(.*)\n', line)
                if match_obj:
                    version.set_left(match_obj.group(2), True)
                    version.set_right(match_obj.group(5), False)
                    break
                match_obj = re.match(r'pragma solidity (>)(\d*\.\d*\.\d*)(.*) (<)(\d*\.\d*\.\d*)(.*)\n', line)
                if match_obj:
                    version.set_left(match_obj.group(2), False)
                    version.set_right(match_obj.group(5), False)
                    break
                match_obj = re.match(r'pragma solidity (<=)(\d*\.\d*\.\d*)(.*)\n', line)
                if match_obj:
                    version.set_right(match_obj.group(2), True)
                    break
                match_obj = re.match(r'pragma solidity (>)(\d*\.\d*\.\d*)(.*)\n', line)
                if match_obj:
                    version.set_left(match_obj.group(2), False)
                    break
                match_obj = re.match(r'pragma solidity (<)(\d*\.\d*\.\d*)(.*)\n', line)
                if match_obj:
                    version.set_right(match_obj.group(2), False)
                    break
                match_obj = re.match(r'pragma solidity (>=)(\d*\.\d*\.\d*)(.*)\n', line)
                if match_obj:
                    version.set_left(match_obj.group(2), True)
                    break
                match_obj = re.match(r'pragma solidity ([=|>|<|\^]*)(\d*\.\d*\.\d*)(.*)\n', line)
                if match_obj:
                    version.set_unique(match_obj.group(2), True)
                    break

        return version