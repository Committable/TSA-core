from tree_sitter import Language

Language.build_library(
    # Store the library in the `build` directory
    'move_parser/build/my-languages.so',

    # Include one or more languages
    [
        # 'vendor/tree-sitter-go',
        'move_parser/vendor/tree-sitter-move',
        # 'vendor/tree-sitter-python'
    ]
)