import log
import os
import re
import subprocess
import solcx
import signal
import traceback

from pyevmasm import disassemble_hex
from errors.compilation_fail import CompilationFailError


class Version:  # "a.b.c"
    def __init__(self, version_str):
        self.version_str = version_str
        parts_str = version_str.split(".")
        if len(parts_str) != 3:
            log.mylogger.error("%s cannot parsed to Version", version_str)
            raise Exception("%s cannot parsed to Version" % version_str)

        try:
            self.major = int(parts_str[0])
            self.sub = int(parts_str[1])
            self.stage = int(parts_str[2])
        except Exception as err:
            log.mylogger.error("Error: %s", str(err))
            raise err

    def __lt__(self, other):
        if self.major < other.major:
            return True
        elif self.major == other.major and self.sub < other.sub:
            return True
        elif self.major == other.major and self.sub == other.sub and self.stage < other.stage:
            return True
        else:
            return False

    def __gt__(self, other):
        if self.major > other.major:
            return True
        elif self.major == other.major and self.sub > other.sub:
            return True
        elif self.major == other.major and self.sub == other.sub and self.stage > other.stage:
            return True
        else:
            return False

    def __le__(self, other):
        if self.major < other.major:
            return True
        elif self.major == other.major and self.sub < other.sub:
            return True
        elif self.major == other.major and self.sub == other.sub and self.stage <= other.stage:
            return True
        else:
            return False

    def __ge__(self, other):
        if self.major > other.major:
            return True
        elif self.major == other.major and self.sub < other.sub:
            return True
        elif self.major == other.major and self.sub == other.sub and self.stage >= other.stage:
            return True
        else:
            return False

    def __eq__(self, other):
        if self.major == other.major and self.sub == other.sub and self.stage == other.stage:
            return True
        else:
            return False

    def __ne__(self, other):
        if self.major != other.major or self.sub != other.sub or self.stage != other.stage:
            return True
        else:
            return False

    def __str__(self):
        return self.version_str


class AllowedVersion:  # left [<=|<] allow_version [<=|<] right
    # 私有变量，无法在外部访问，AllowVersion.__count会出错
    __versions = list(map(lambda x: Version(x),
                          ['0.8.10', '0.8.9', '0.8.8', '0.8.7', '0.8.6', '0.8.5', '0.8.4', '0.8.3', '0.8.2', '0.8.1',
                           '0.8.0',
                           '0.7.6', '0.7.5', '0.7.4', '0.7.3', '0.7.2', '0.7.1', '0.7.0', '0.6.12', '0.6.11', '0.6.10',
                           '0.6.9',
                           '0.6.8', '0.6.7', '0.6.6', '0.6.5', '0.6.4', '0.6.3', '0.6.2', '0.6.1', '0.6.0', '0.5.17',
                           '0.5.16',
                           '0.5.15', '0.5.14', '0.5.13', '0.5.12', '0.5.11', '0.5.10', '0.5.9', '0.5.8', '0.5.7',
                           '0.5.6', '0.5.5',
                           '0.5.4', '0.5.3', '0.5.2', '0.5.1', '0.5.0', '0.4.26', '0.4.25', '0.4.24', '0.4.23',
                           '0.4.22', '0.4.21',
                           '0.4.20', '0.4.19', '0.4.18', '0.4.17', '0.4.16', '0.4.15', '0.4.14', '0.4.13', '0.4.12',
                           '0.4.11']))

    @classmethod
    def get_versions(cls):
        return cls.__versions

    @classmethod
    def update_versions(cls):
        cls.__versions = list(solcx.get_installable_solc_versions())

    def __init__(self):
        self.unique = None

        self.left = None
        self.left_equal = False

        self.right = None
        self.right_equal = False

    def set_right(self, right_str, equal):
        self.right = Version(right_str)
        self.right_equal = equal
        return self

    def set_unique(self, version_str):
        self.unique = Version(version_str)
        return self

    def set_left(self, left_str, equal):
        self.left = Version(left_str)
        self.left_equal = equal
        return self

    def is_allow(self, version):
        if self.unique:
            return version == self.unique
        else:
            if self.left:
                if self.left_equal:
                    if self.left <= version:
                        if self.right:
                            if self.right_equal:
                                return version <= self.right
                            else:
                                return version < self.right
                    else:
                        return False
                else:
                    if self.left < version:
                        if self.right:
                            if self.right_equal:
                                return version <= self.right
                            else:
                                return version < self.right
                    else:
                        return False
                return True
            elif self.right:
                if self.right_equal:
                    return version <= self.right
                else:
                    return version < self.right
            else:
                return True

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
                elif other_version.right > self.right:
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
                elif self.left > other_version.left:
                    version.set_left(self.left, self.left_equal)
                else:
                    version.set_left(other_version.left, other_version.left_equal)
            elif other_version.left:
                version.set_left(other_version.left, other_version.left_equal)
            elif self.left:
                version.set_left(self.left, self.left_equal)

            if version.right and version.left:
                if version.left > version.right:
                    return None
                elif version.right == version.left and not (version.right_equal and version.left_equal):
                    return None

            return version

    def get_allowed_version(self):
        for x in AllowedVersion.get_versions():
            if self.is_allow(x):
                return str(x)
        return None

    def get_allowed_versions_set(self):
        result = []
        for x in AllowedVersion.get_versions():
            if self.is_allow(x):
                result.append(x)

        return result

    def __str__(self):
        if self.unique:
            return "version==" + str(self.unique)
        expr = "version"
        if self.left:
            if self.left_equal:
                expr = str(self.left) + "<=" + expr
            else:
                expr = str(self.left) + "<=" + expr
        if self.right:
            if self.right_equal:
                expr = expr + "<=" + str(self.right)
            else:
                expr = expr + "<" + str(self.right)
        return expr


class SolidityCompiler:
    def __init__(self, project_dir, src_file, root_path, allow_paths, remaps, include_paths, compiler_version,
                 compilation_err):
        self.combined_json = {"contracts": {}, "sources": {}}  # compilation result of json type

        self.project_dir = project_dir  # source dir of project
        self.src_file = src_file  # relative path of the analyzing file
        self.target = os.path.abspath(os.path.join(self.project_dir, self.src_file))  # absolute path of analyzing file

        self.root_path = root_path

        allow_paths.append(self.root_path)
        self.allow_paths = allow_paths

        self.remaps = remaps
        self.include_paths = include_paths
        self.compilation_err = compilation_err

        if compiler_version:
            self.allowed_version = AllowedVersion().set_unique(compiler_version)
            log.mylogger.info("get solidity compiler version: %s", self.allowed_version)
        else:
            # get compiler version
            if not os.path.exists(self.target):
                log.mylogger.warning("Analyzing file: %s not exits", self.target)
            else:
                allowed_version = SolidityCompiler.get_compiler_version_from_pragma(self.target)
                if allowed_version is None:
                    self.allowed_version = Version("0.8.0")
                else:
                    self.allowed_version = allowed_version
                log.mylogger.info("get solidity compiler version: %s", self.allowed_version)

    def prepare_compilation(self, compilation_cfg):
        if "compilation_base" in compilation_cfg:
            if "remaps" in compilation_cfg["compilation_base"]:
                for key in compilation_cfg["compilation_base"]["remaps"]:
                    self.remaps[key] = os.path.join(self.project_dir, compilation_cfg["compilation_base"]["remaps"][key])
            if "allow_paths" in compilation_cfg["compilation_base"]:
                for x in compilation_cfg["compilation_base"]["allow_paths"]:
                    self.allow_paths.append(os.path.join(self.project_dir, x))
        if not os.path.exists(os.path.join(self.project_dir, "node_modules")):
            if "prepare" in compilation_cfg:
                for command in compilation_cfg["prepare"]:
                    path = os.environ['PATH']
                    child = subprocess.Popen(command, cwd=self.project_dir, shell=True, stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)
                    try:
                        outs, errs = child.communicate(timeout=60)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.terminate()
                        os.killpg(child.pid, signal.SIGTERM)
                        os.remove(os.path.join(self.source, ".waffle_bak.json"))
                        log.mylogger.error("run compilation prepare command %s timeout", command)
                        continue
                    if child.returncode != 0:
                        log.mylogger.error("run compilation prepare command %s fail", command)
        log.mylogger.info("success run compilation prepare")

    def get_compiled_contracts_as_json(self, compilation_cfg):
        self.prepare_compilation(compilation_cfg)
        # try solcx with all allowed version until success
        if os.path.exists(self.target):
            for v in self.allowed_version.get_allowed_versions_set():
                try:
                    if self._compile_with_solcx(v):
                        self._convert_opcodes()
                        return
                except Exception as err:
                    # log.mylogger.error("Compile with solcx version %s fail", str(v))
                    traceback.print_exc()
                    continue
            log.mylogger.error("Can not compile with solcx")
            raise CompilationFailError("Can not compile with solcx")

        return

    def _compile_with_solcx(self, version):
        # compile
        version_str = str(version)
        solcx.install_solc(version_str)
        if version > Version("0.4.25"):
            data_dict = solcx.compile_files([self.target],
                                            output_values=["abi", "bin", "bin-runtime", "ast",
                                                           "hashes", "opcodes", "srcmap-runtime"],
                                            allow_empty=True,
                                            # base_path=self.root_path,
                                            optimize=True,
                                            optimize_runs=200,
                                            # optimize_yul=True,
                                            allow_paths=self.allow_paths,
                                            import_remappings=self.remaps,
                                            solc_version=version_str,
                                            )
        else:
            data_dict = solcx.compile_files([self.target],
                                            output_values=["abi", "bin", "bin-runtime", "ast",
                                                           "opcodes", "srcmap-runtime"],
                                            allow_empty=True,
                                            base_path=self.root_path,
                                            optimize=True,
                                            optimize_runs=200,
                                            # optimize_yul=True,
                                            allow_paths=self.allow_paths,
                                            import_remappings=self.remaps,
                                            solc_version=version_str,
                                            )
        # convert json result format
        for key in data_dict:
            file = key.split(":")[0]
            cname = key.split(":")[-1]

            file = os.path.abspath(file)
            if file not in self.combined_json["contracts"]:
                self.combined_json["contracts"][file] = {}

            self.combined_json["contracts"][file][cname] = {
                'evm':
                    {
                        'deployedBytecode':
                            {
                                'opcodes': "",
                                "object": self.convert_external_library_space_holder(data_dict[key]["bin-runtime"]),
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
            if file not in self.combined_json["sources"]:
                if "children" in data_dict[key]["ast"]:
                    self.combined_json["sources"][file] = {
                        "legacyAST": data_dict[key]['ast']
                    }
                else:
                    self.combined_json["sources"][file] = {
                        "ast": data_dict[key]['ast']
                    }
        return True

    def _convert_opcodes(self):
        if "contracts" in self.combined_json:
            for file in self.combined_json["contracts"]:
                for cname in self.combined_json["contracts"][file]:
                    x = self.combined_json["contracts"][file][cname]
                    deployed_bytecode_object = x["evm"]["deployedBytecode"]['object']
                    if deployed_bytecode_object:
                        x["evm"]["deployedBytecode"]['opcodes'] = disassemble_hex(deployed_bytecode_object).replace(
                            "\n", " ")

                    bytecode_object = x["evm"]["bytecode"]['object']
                    if bytecode_object and not x["evm"]["bytecode"]['opcodes']:
                        x["evm"]["bytecode"]['opcodes'] = disassemble_hex(bytecode_object).replace("\n", " ")

    @staticmethod
    def convert_external_library_space_holder(bytecode):
        return bytecode.replace("__$", "abc").replace("$__", "cba")

    @staticmethod
    def get_compiler_version_from_pragma(file):
        with open(file, 'r', encoding="utf-8") as input_file:
            version = AllowedVersion()
            lines = input_file.readlines()
            for line in lines:
                match_obj = re.match(r'pragma solidity (=)(\d*\.\d*\.\d*)(.*)\n', line)
                if match_obj:
                    version.set_unique(match_obj.group(2))
                    break
                match_obj = re.match(r'pragma solidity (\d*\.\d*\.\d*)(.*)\n', line)
                if match_obj:
                    version.set_unique(match_obj.group(1))
                    break
                match_obj = re.match(r'pragma solidity (\^)(\d*\.\d*\.\d*)(.*)\n', line)
                if match_obj:
                    version.set_left(match_obj.group(2), True)
                    parts = match_obj.group(2).split(".")
                    right = parts[0] + "." + str(int(parts[1]) + 1) + ".0"
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
                    version.set_unique(match_obj.group(2))
                    break
        return version
