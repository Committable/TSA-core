import abstracts.cfg.loop_bin
import abstracts.cfg.selection_bin
import abstracts.cfg.sequence_bin


class CfgAbstract:

    def __init__(self):
        self.indexes = {}

    def register_index(self, index_name):
        self.indexes[index_name] = getattr(
            __import__(f'abstracts.cfg.{index_name}').cfg, index_name)

    def get_cfg_abstract_json(self, cfg_graphs):
        abstract = {}
        for name, index in self.indexes.items():
            func = getattr(index.get_index_class(cfg_graphs), 'get_index')
            abstract[name] = func()

        return abstract

    def register_cfg_abstracts(self, context):
        for index in context.cfg_abstracts:
            self.register_index(index)
