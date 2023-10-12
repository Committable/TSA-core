import networkx as nx
import threading
import sys
from abstracts import index
from utils import log
from utils import context as ctx


class StopThread(StopIteration):
    pass


threading.SystemExit = SystemExit, StopThread


class myThread(threading.Thread):

    def __init__(self, graphs):
        threading.Thread.__init__(self)
        self.cfg_graphs = graphs
        self.result = []

    def _bootstrap(self, stop_thread=False):

        def stop():
            nonlocal stop_thread
            stop_thread = True

        self.stop = stop

        def tracer(*_):
            if stop_thread:
                raise StopThread()
            return tracer

        sys.settrace(tracer)
        super()._bootstrap()

    def run(self):
        for x in self.cfg_graphs:
            self.result.extend(nx.simple_cycles(self.cfg_graphs[x]))


class LoopBin(index.Index):

    def __init__(self, cfg_graphs):
        self.cfg_graphs = cfg_graphs

    def get_index(self, context):
        if context.error_type == ctx.ExecErrorType.SYMBOL_TIMEOUT or context.error_type == ctx.ExecErrorType.SYMBOL_EXEC:
            return 0
        cycles = []
        loops = {}
        loop_bin = 0

        child = myThread(self.cfg_graphs)
        child.setDaemon(True)
        child.start()

        child.join(30)
        if child.isAlive():
            child.stop()
            log.mylogger.error("cfg loop bin timeout")
            context.set_index_err("loop_bin")
            return 0
        cycles.extend(child.result)
        # for cycle in cycles:
        #     if cycle[0] in loops:
        #         if cycle[-1] not in loops[cycle[0]]:
        #             loop_bin += 1
        #             loops[cycle[0]].add(cycle[-1])
        #     else:
        #         loop_bin += 1
        #         loops[cycle[0]] = set()
        #         loops[cycle[0]].add(cycle[-1])
        return len(cycles)


def get_index_class(cfg_graphs):
    return LoopBin(cfg_graphs)
