from tree_sitter import Language

Language.build_library(
    # Store the library in the `build` directory
    'js_parser/build/my-languages.so',

    # Include one or more languages
    [
        # 'vendor/tree-sitter-go',
        'js_parser/vendor/tree-sitter-javascript',
        # 'vendor/tree-sitter-python'
    ]
)