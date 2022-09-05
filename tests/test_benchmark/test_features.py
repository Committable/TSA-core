import unittest
import os
import shutil
import global_params
import log
import os
import time
from analyzer import analyze_evm_from_solidity
from context import Context

global_params.DEST_PATH = "./tmp"

log.mylogger = log.get_logger()

THIS_DIR = os.path.dirname(os.path.abspath(__file__))


class FeaturesBenchmark(unittest.TestCase):

    def setUp(self):
        self.start = time.time()
        self.project_dir = os.path.join(THIS_DIR, "features")
        self.workspace = os.path.join(global_params.DEST_PATH, str(self.start))

    def tearDown(self):
        # shutil.rmtree(self.workspace)
        pass

    def _test_evm(self, name, expected_cfg, expected_ssg):
        context = Context(self.start, self.project_dir, f"{name}.sol", [], "",
                          "")

        filename = os.path.join(THIS_DIR, "features", f"{name}.sol")
        log.mylogger.info(
            "-----------------start analysis: %s------------------", filename)
        cfg_reporter, ssg_reporter = analyze_evm_from_solidity(
            self.workspace, context.src_file, context.project_dir, context)

        self.assertDictEqual(cfg_reporter.cfg_abstract, expected_cfg)
        self.assertDictEqual(ssg_reporter.ssg_abstract, expected_ssg)

    def test_assert(self):
        self._test_evm("assert", {
            'sequence_bin': 11,
            'selection_bin': 4,
            'loop_bin': 0
        }, {
            'data_flow': 0,
            'control_flow': 5
        })

    def test_event(self):
        self._test_evm("event", {
            'sequence_bin': 12,
            'selection_bin': 4,
            'loop_bin': 0
        }, {
            'data_flow': 0,
            'control_flow': 5
        })

    def test_list(self):
        self._test_evm("list", {
            'sequence_bin': 19,
            'selection_bin': 8,
            'loop_bin': 0
        }, {
            'data_flow': 13,
            'control_flow': 9
        })

    def test_loop(self):
        self._test_evm("loop", {
            'sequence_bin': 26,
            'selection_bin': 11,
            'loop_bin': 2
        }, {
            'data_flow': 19,
            'control_flow': 13
        })

    def test_map(self):
        self._test_evm("map", {
            'sequence_bin': 10,
            'selection_bin': 4,
            'loop_bin': 0
        }, {
            'data_flow': 6,
            'control_flow': 5
        })

    def test_memory(self):
        self._test_evm("memory", {
            'sequence_bin': 17,
            'selection_bin': 6,
            'loop_bin': 1
        }, {
            'data_flow': 0,
            'control_flow': 6
        })

    def test_require(self):
        self._test_evm("require", {
            'sequence_bin': 15,
            'selection_bin': 6,
            'loop_bin': 0
        }, {
            'data_flow': 5,
            'control_flow': 7
        })

    def test_struct(self):
        self._test_evm("struct", {
            'sequence_bin': 15,
            'selection_bin': 7,
            'loop_bin': 0
        }, {
            'data_flow': 8,
            'control_flow': 8
        })

    def test_tuple(self):
        self._test_evm("tuple", {
            'sequence_bin': 20,
            'selection_bin': 12,
            'loop_bin': 3
        }, {
            'data_flow': 0,
            'control_flow': 9
        })

    def test_external(self):
        self._test_evm("external", {
            'sequence_bin': 24,
            'selection_bin': 8,
            'loop_bin': 0
        }, {
            'data_flow': 7,
            'control_flow': 10
        })

    def test_internal(self):
        self._test_evm("internal", {
            'sequence_bin': 14,
            'selection_bin': 4,
            'loop_bin': 1
        }, {
            'data_flow': 0,
            'control_flow': 5
        })


if __name__ == "__main__":
    unittest.main()
