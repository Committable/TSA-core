import unittest
from utils.context import Context
from utils.source import Source
from abstracts.ast.js_loop_src import JsLoopSrc
from abstracts.ast.js_sequence_src import JsSequenceSrc
from abstracts.ast.js_selection_src import JsSelectionSrc
from js_parser import parser as js_parser
from js_parser import walker as js_walker


class TestJsSrc(unittest.TestCase):
    def test_simple(self):
        source_content = '''for (var i=0;i<cars.length;i++)
                            { 
                                document.write(cars[i] + "<br>");
                            }
        '''
        source_obj = Source(content=source_content)
        source_unit = js_parser.parse(source_obj.get_content())
        ast_walker = js_walker.JsAstWalker()
        context = Context("", "", "", "", "")
        ast = ast_walker.get_ast_json(source_unit, context)

        loop = JsLoopSrc(ast, ast_walker.type, source_obj)
        sequence = JsSequenceSrc(ast, ast_walker.type, source_obj)
        selection = JsSelectionSrc(ast, ast_walker.type, source_obj)
        loop_src = loop.get_index(context)
        sequence_src = sequence.get_index(context)
        selection_src = selection.get_index(context)
        self.assertEqual(loop_src, 1)
        self.assertEqual(sequence_src, 12)
        self.assertEqual(loop_src, 1)


if __name__ == "__main__":
    unittest.main()
