class SsgAbstract:

    def __init__(self):
        self.indexes = {}

    def register_index(self, index_name):
        self.indexes[index_name] = getattr(
            __import__("abstracts.ssg." + index_name).ssg, index_name)

    def get_ssg_abstract_json(self, ssg_graphs):
        abstract = {}
        for name, index in self.indexes.items():
            func = getattr(index.get_index_class(ssg_graphs), "get_index")
            abstract[name] = func()

        return abstract

    def register_ssg_abstracts(self, context):
        for index in context.ssg_abstracts:
            self.register_index(index)
