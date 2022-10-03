import blessed
from blessed.sequences import Sequence

import constants
from file_handler import WorkingFile
from key_handler import handle_key_press


class Display:

    def __init__(self, file_path):
        self.term = blessed.Terminal()
        self.height = self.term.height - constants.HEADER_HEIGHT - constants.FOOTER_HEIGHT
        self.width = self.term.width - constants.LMARGIN_WIDTH
        self.file = WorkingFile(file_path)
        self.cursor = self.Cursor(self.term)
        self.rows = []
        self.display_active = False
        self.redraw_rows = []

        # TODO: remove these after keyboard debugging is over
        self.key_pressed = ''
        self.key_code = ''


    # TODO: probably can be pulled out of Display() class now
    class Cursor:
        def __init__(self, term):
            self.term = term
            self.x = 0
            self.y = 0
            self.x_memory = 0
            self.max_x = term.width - constants.LMARGIN_WIDTH - 1
            self.max_y = term.height - constants.HEADER_HEIGHT - constants.FOOTER_HEIGHT - 1

        # TODO: all cursor movement should be done by these functions
        # TODO: these functions should update redraw_rows[] rather than forcing other functions to keep track
        def goto(self, x, y):
            self.goto_x(x)
            self.goto_y(y)

        def goto_x(self, x):
            if x > self.max_x:
                x = self.max_x
            elif x < 0:
                x = 0
            self.x = x

        def goto_y(self, y):
            if y > self.max_y:
                y = self.max_y
            elif y < 0:
                y = 0
            self.y = y

        def move(self, x, y):
            self.goto(self.x + x, self.y + y)

        def move_x(self, x):
            self.goto_x(self.x + x)

        def move_y(self, y):
            self.goto_y(self.y + y)

        def set_x_memory(self, m=None):
            if m is None:
                m = self.x
            self.x_memory = m

        # TODO: this function should just have access to (current_row().char_length - 1) in place of row_length
        def snap_x(self, row_length):
            if row_length > self.x_memory:
                self.x = self.x_memory
            else:
                self.goto_x(row_length)


    def current_row(self):
        return self.rows[self.cursor.y]

    def first_row(self):
        return self.rows[0]

    def last_row(self):
        return self.rows[-1]

    def first_byte(self):
        return self.first_row().start_byte

    def last_byte(self):
        return self.last_row().end_byte

    def first_line(self):
        return self.first_row().line_num

    def last_line(self):
        return self.last_row().line_num

    def at_start_of_file(self):
        return self.first_byte() == 0

    def at_end_of_file(self):
        return self.last_row().EOF

    def is_row_start_of_line(self, row):
        return row.start_byte == self.file.line_info[row.line_num].start_byte

    def is_row_end_of_line(self, row):
        return row.chars[-1] == constants.NEWLINE_CHAR or row.EOF


    def set_rows_from_byte(self, byte):
        self.rows = []
        line_num = self.file.get_line_num_of_byte(byte)

        # TODO: as written, the input byte may not even appear on screen for sufficiently long lines
        start_byte = self.file.line_info[line_num].start_byte

        while len(self.rows) < self.height:
            next_row = self.file.get_chunk_from_byte(self.width, start_byte, until_char=constants.NEWLINE_CHAR)
            self.rows.append(next_row)
            if next_row.EOF:
                break
            start_byte = next_row.end_byte
        self.row_check_EOF()
        self.redraw_rows = range(len(self.rows))


    def scroll_down_one_row(self):
        if self.at_end_of_file():
            return
        next_row = self.file.get_chunk_from_byte(self.width, self.last_byte(), until_char=constants.NEWLINE_CHAR)
        del self.rows[0]
        self.rows.append(next_row)
        self.row_check_EOF()
        self.redraw_rows = range(len(self.rows))


    def scroll_up_one_row(self):
        if self.at_start_of_file():
            return
        # check if the top row and previous row are on the same line or not
        top_line_info = self.file.line_info[self.first_line()]
        if top_line_info.start_byte < self.rows[0].start_byte:
            prev_row_start_byte = top_line_info.start_byte
        else:
            prev_row_start_byte = self.file.line_info[self.first_line() - 1].start_byte

        # to wrap rows correctly, we need to divide the previous line into chunks that are fit to the screen width
        prev_row = None
        while prev_row_start_byte < self.rows[0].start_byte:
            prev_row = self.file.get_chunk_from_byte(self.width, prev_row_start_byte, until_char=constants.NEWLINE_CHAR)
            prev_row_start_byte = prev_row.end_byte

        del self.rows[-1]
        self.rows.insert(0, prev_row)
        self.redraw_rows = range(len(self.rows))


    def row_check_EOF(self):
        # add an EOF character to rows[] so that the cursor can insert at the end of the file
        # this function should only be called after a new row is extracted from the file_handler
        if self.rows[-1].EOF:
            self.rows[-1].chars += constants.EOF_CHAR
            self.rows[-1].char_length += 1


    def get_line_num_for_display(self, row):
        line_num = row.line_num
        if not self.is_row_start_of_line(row):
            # only display line numbers on the row that the line starts on
            return ''
        # displayed line numbers begin at 1 instead of 0
        num = str(line_num + 1)
        size = len(num)

        # TODO: this calculation is not dynamic and assumes LMARGIN_WIDTH == 5 (4 digits + 1 space for padding)
        if size <= 4:  # 1 - 9,999
            return num
        if size <= 6:  # 10K - 999K
            return num[:-3] + 'K'
        if size <= 7:  # 1M - 9.99M
            if num[1:3] == '00':
                return num[0] + 'M'
            return num[0] + '.' + num[1:3] + 'M'
        if size <= 9:  # 10M - 999M
            return num[:-6] + 'M'
        if size <= 11:  # 1B - 99B
            if num[-9:] == '000000000':
                return num[:-9] + 'B'
            return '>' + num[:-9] + 'B'
        return '????'


    def draw_screen(self):
        for row_num in self.redraw_rows:
            row = self.rows[row_num]

            # highlight the current row
            background = self.term.normal
            ln_color = self.term.gray_on_darkslategray
            if row.line_num == self.rows[self.cursor.y].line_num:
                background += self.term.on_gray20
                ln_color = self.term.gray_on_darkslategray4

            # display line number margin at start of each row
            print(self.term.move_xy(0, row_num + constants.HEADER_HEIGHT), end='')
            ln = self.get_line_num_for_display(row) + ' '
            print(f'{ln_color}{ln:>{constants.LMARGIN_WIDTH}}{background}', end='')

            # print each row, one character at a time
            col_num = 0
            for char in row.chars:
                highlight = ''
                if col_num == self.cursor.x and row_num == self.cursor.y:
                    # highlight the cursor location
                    highlight = self.term.on_lightsteelblue4

                # TODO: tidy this up
                # TODO: need to account for all multi-length, variable-length, and zero-length characters
                # special characters are assigned a symbol and color when displayed
                if row.EOF and col_num == row.char_length - 1:
                    char = f'{self.term.red}{char}{self.term.normal}'
                if char == '\n':
                    char = f'{self.term.blue}\u00B6{self.term.normal}'
                elif char == '\r':
                    char = f'{self.term.turquoise}\u21B2{self.term.normal}'
                elif char == '\t':
                    char = f'{self.term.purple}\u02FD{self.term.normal}'
                elif char == ' ':
                    char = f'{self.term.green}_{self.term.normal}'
                elif Sequence(char, self.term).length() > 1:
                    char = f'{self.term.orange}\u0081{self.term.normal}'

                print(f'{background}{highlight}{char}{background}', end='')
                col_num += 1

            if row.char_length < self.width:
                # delete any leftovers after the last character in a row
                print(f'{background}{self.term.clear_eol}', end='')

        self.draw_footer()
        self.redraw_rows = []
        print(end='', flush=True)


    def draw_header(self):
        # TODO: make this pretty
        print(f'{self.term.home}{self.term.clear}', end='')
        header_string = f' {self.file.directory_path}\\{self.term.purple}{self.file.name}'
        print(f'{self.term.black_on_white}{header_string:<{self.term.width}}', end='')
        print(f'{self.term.clear_eol}', end='')


    def draw_footer(self):
        # TODO: make this pretty (both the code and the contents of the footer)
        print(f'{self.term.move_xy(0, self.height + constants.HEADER_HEIGHT)}', end='')
        footer_string = f' b({self.first_byte()}, {self.last_byte()})  l({self.first_line()+1}, {self.last_line()+1})'
        print(f'{self.term.black_on_white}{footer_string:<{self.term.width}}', end='')
        print(f'{self.term.move_down(1)}{self.term.move_x(0)}', end='')
        footer_string = f' total bytes:{self.file.num_bytes}  total lines:{self.file.num_lines}'
        footer_string += f'  {self.key_pressed} {self.key_code}'
        print(f'{self.term.black_on_white}{footer_string:<{self.term.width}}', end='')


    def run_event_loop(self):
        self.file.open()
        self.set_rows_from_byte(0)
        with self.term.fullscreen(), self.term.cbreak(), self.term.raw(), self.term.hidden_cursor():

            self.display_active = True
            self.draw_header()
            while self.display_active:
                self.draw_screen()

                # TODO: this works (somehow) but should be written more elegantly
                # flush buffered keyboard input
                try:
                    import msvcrt
                    while msvcrt.kbhit():
                        msvcrt.getch()
                except ImportError:
                    import sys, termios
                    termios.tcflush(sys.stdin, termios.TCIOFLUSH)

                key = self.term.inkey()
                handle_key_press(self, key)

        self.file.close()
