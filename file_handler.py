import os
import constants


class WorkingFile:

    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.name = os.path.basename(path)
        self.directory_path = os.path.abspath(path[:-1 * len(self.name)])
        self.num_bytes = os.path.getsize(self.path)
        self.num_lines = 0
        self.line_info = None
        self._file = None


    class _ByteChunk:
        def __init__(self):
            self.line_num = 0
            self.start_byte = 0
            self.end_byte = 0
            self.char_length = 0
            self.chars = ''
            self.EOF = False


    def open(self):
        self._file = open(self.path, 'r', newline=constants.NEWLINE_CHAR, encoding='utf-8')
        self._cache_line_info()
        self._file.seek(0)


    def close(self):
        self._file.close()


    def _cache_line_info(self):
        # TODO: this should run in it's own thread
        # TODO: a file's line info cache should be saved to disk after the first time the file is opened
        # TODO: this should only be loaded in chunks to keep a small memory footprint
        self.line_info = []
        self._file.seek(0)
        next_line = self._ByteChunk()
        num_lines = 0
        while True:
            next_char = self._file.read(1)
            if next_char:
                next_line.char_length += 1
            else:
                next_line.EOF = True
            if not next_char or next_char == constants.NEWLINE_CHAR:
                next_line.end_byte = self._file.tell()
                self.line_info.append(next_line)
                next_line = self._ByteChunk()
                num_lines += 1
                next_line.line_num = num_lines
                next_line.start_byte = self._file.tell()
                if not next_char:
                    break
        self.num_lines = num_lines


    def get_chunk_from_byte(self, num_chars, start_byte, until_char=None, until_byte=None):
        self._file.seek(start_byte)
        result = self._ByteChunk()
        result.start_byte = start_byte
        result.line_num = self.get_line_num_of_byte(start_byte)

        for i in range(num_chars):
            next_char = self._file.read(1)
            result.chars += next_char
            if not next_char:
                result.EOF = True
                break
            if next_char == until_char or (until_byte is not None and self._file.tell() >= until_byte):
                break

        result.char_length = len(result.chars)
        result.end_byte = self._file.tell()
        return result


    def get_line_num_of_byte(self, byte):
        # TODO: this can be optimized with a binary search
        for line_num in range(self.num_lines):
            if byte < self.line_info[line_num].end_byte or self.line_info[line_num].EOF:
                return line_num
