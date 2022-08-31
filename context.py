class Context:
    def __init__(self, start, project_dir, src_file, diff, platform, request_id):
        self.start = start  # start time
        self.request_id = request_id  # request id

        # input project dir and file dir
        self.project_dir = project_dir
        self.src_file = src_file

        # different lines between commit before and after
        self.diff = diff  # i.e. [1,2,3]

        # platform for analysis files
        # todo: not used now
        self.platform = platform

        # default compilation config
        self.include_paths = ["."]
        self.remaps = {}
        self.root_path = self.project_dir
        self.allow_paths = []

        # default index for abstracts
        self.ast_abstracts = ["sequence_src",
                              "selection_src",
                              "loop_src"]

        self.cfg_abstracts = ["sequence_bin",
                              "selection_bin",
                              "loop_bin"]

        self.ssg_abstracts = ["data_flow",
                              "control_flow"]

        # if analysis cause an error
        self.err = False
        # timeout
        self.timeout = False

    def set_timeout(self):
        self.timeout = True

    def set_err(self):
        self.err = True

    def add_include_path(self, path):
        self.include_paths.append(path)

    def add_remap(self, key, value):
        self.remaps[key] = value

    def add_ast_abstract(self, index):
        self.ast_abstracts.append(index)

    def add_cfg_abstract(self, index):
        self.cfg_abstracts.append(index)

    def add_ssg_abstract(self, index):
        self.ssg_abstracts.append(index)
