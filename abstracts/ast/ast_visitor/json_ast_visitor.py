class JsonAstVisitor():
    def __init__(self, ast, condition_func, process_func):
        self.ast = ast
        self.f_condition = condition_func
        self.f_process = process_func

    def visit(self, node, context):
        if self.f_condition(node, context):
            self.f_process(context)
        if "children" in node:
            for child in node["children"]:
                self.visit(child, context)
