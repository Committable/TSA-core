import os
from utils import log


class Source:
    def __init__(self, file_path=None, content=None):
        if file_path:
            self.file_path = file_path
            self.content = self._load_content()  # the all file content in string type
        else:
            self.file_path = None
            self.content = content
        self.line_break_positions = self._load_line_break_positions()  # the position of all '\n'
        self.index = 0

    def _load_content(self):
        if not os.path.exists(self.file_path):
            log.mylogger.warning("%s not exist", self.file_path)
            content = ''
        else:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        return content

    def get_content(self):
        return self.content

    def is_in_source(self, i):
        return bool(i == self.index)

    def get_content_from_line(self, line):
        if line < 1 or line > len(self.line_break_positions):
            return ''
        end = self.line_break_positions[line - 1]
        if line == 1:
            start = 0
        else:
            start = self.line_break_positions[line - 2] + 1
        return self.content[start:end]

    def get_lines_from_position(self, start, end):  # [start,end)
        lines = []
        last = 0
        for n in range(0, len(self.line_break_positions)):
            if start < self.line_break_positions[n] and end > last:
                lines.append(n + 1)
            if end < self.line_break_positions[n]:
                break
            last = self.line_break_positions[n]

        return lines

    def _load_line_break_positions(self):
        return [i for i, letter in enumerate(self.content) if letter == '\n']
