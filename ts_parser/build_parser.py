from tree_sitter import Language

Language.build_library(
    # Store the library in the `build` directory
    'ts_parser/build/my-languages.so',

    # Include one or more languages
    [
        # 'vendor/tree-sitter-go',
        'ts_parser/vendor/tree-sitter-typescript/typescript',
        # 'vendor/tree-sitter-python'
    ]
)