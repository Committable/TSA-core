from tree_sitter import Language


def build_tree_sitter_library(code_path, lib_path):
    Language.build_library(
        # Store the library in the `build` directory
        lib_path,

        # Include one or more languages
        [
            code_path,
        ]
    )
