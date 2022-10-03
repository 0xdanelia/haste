
def cursor_up_one_row(self):
    if self.current_row().start_byte == 0:
        # move cursor to the first byte if already at the top of the file
        self.cursor.set_x_memory(0)
    elif self.cursor.y == 0:
        self.scroll_up_one_row()
    else:
        self.cursor.move_y(-1)
    self.cursor.snap_x(self.current_row().char_length - 1)


def cursor_down_one_row(self):
    if self.current_row().EOF:
        # move cursor to the last byte if already at the bottom of the file
        self.cursor.set_x_memory(self.current_row().char_length - 1)
    elif self.cursor.y == len(self.rows) - 1:
        self.scroll_down_one_row()
    else:
        self.cursor.move_y(1)
    self.cursor.snap_x(self.current_row().char_length - 1)
    return


def cursor_page_up(self):
    if self.at_start_of_file():
        self.cursor.goto(0, 0)
        self.cursor.set_x_memory()
    else:
        # TODO: should instead write an optimized function specifically for page_up
        for i in range(self.height):
            self.scroll_up_one_row()
        self.cursor.snap_x(self.current_row().char_length - 1)


def cursor_page_down(self):
    if self.at_end_of_file():
        self.cursor.goto_y(len(self.rows) - 1)
        self.cursor.goto_x(self.last_row().char_length - 1)
        self.cursor.set_x_memory()
    else:
        for i in range(self.height):
            self.scroll_down_one_row()
        self.cursor.snap_x(self.current_row().char_length - 1)


def cursor_home(self):
    if self.cursor.x != 0:
        self.cursor.goto_x(0)
    elif not self.is_row_start_of_line(self.current_row()):
        if self.first_row().line_num == self.current_row().line_num and not self.is_row_start_of_line(self.first_row()):
            # if the start of the line is off-screen, travel there
            self.set_rows_from_byte(self.file.line_info[self.current_row().line_num].start_byte)
            self.cursor.goto(0, 0)
        else:
            # the start of the line is one of the current rows
            for row_num in range(len(self.rows)):
                if self.rows[row_num].line_num == self.current_row().line_num:
                    self.cursor.goto(0, row_num)
                    break
    self.cursor.set_x_memory()


def cursor_end(self):
    if self.cursor.x != self.current_row().char_length - 1:
        self.cursor.goto_x(self.current_row().char_length - 1)
    elif not self.is_row_end_of_line(self.current_row()):
        if self.last_row().line_num == self.current_row().line_num and not self.is_row_end_of_line(self.last_row()):
            # if the end of the line is off-screen, travel there
            while not self.is_row_end_of_line(self.last_row()):
                self.scroll_down_one_row()
            self.cursor.goto(self.last_row().char_length - 1, len(self.rows) - 1)
        else:
            # the end of the line is one of the current rows
            for row_num in range(len(self.rows) - 1, 0, -1):
                if self.rows[row_num].line_num == self.current_row().line_num:
                    self.cursor.goto(self.rows[row_num].char_length - 1, row_num)
                    break
    self.cursor.set_x_memory()


def handle_key_press(self, key):

    current_line_num = self.current_row().line_num

    if key.is_sequence:
        pressed = key.name
        code = key.code
    else:
        pressed = key
        code = ord(key)

    self.key_pressed = pressed
    self.key_code = code

    # Arrow keys
    if pressed == 'KEY_UP':
        cursor_up_one_row(self)

    elif pressed == 'KEY_DOWN':
        cursor_down_one_row(self)

    elif pressed == 'KEY_RIGHT':
        if self.cursor.x == self.current_row().char_length - 1:
            self.cursor.set_x_memory(0)
            cursor_down_one_row(self)
        else:
            self.cursor.move_x(1)
        self.cursor.set_x_memory()

    elif pressed == 'KEY_LEFT':
        if self.cursor.x == 0:
            self.cursor.set_x_memory(self.cursor.max_x)
            cursor_up_one_row(self)
        else:
            self.cursor.move_x(-1)
        self.cursor.set_x_memory()

    # Page navigation
    elif pressed == 'KEY_PGDOWN':
        cursor_page_down(self)

    elif pressed == 'KEY_PGUP':
        cursor_page_up(self)

    elif pressed == 'KEY_HOME':
        cursor_home(self)

    elif pressed == 'KEY_END':
        cursor_end(self)

    # indicate which rows need to be redrawn
    if not self.redraw_rows:
        # scrolling up/down will populate redraw_rows[], so only update it here if it is empty
        for row_num in range(len(self.rows)):
            # at minimum, the previous line and the current line should be redrawn after a key press event
            if self.rows[row_num].line_num in {current_line_num, self.current_row().line_num}:
                self.redraw_rows.append(row_num)

    # TODO: as the key handling is currently written, [CTRL + Z] does not return a key press event
    # TODO: need to research [CTRL + KEY] interaction across different keyboards and operating systems
    # TODO: currently [CTRL + home/end] sends a sequence that begins with [ESC] but is interpreted as just [ESC]
    if code == 17 or pressed == 'KEY_ESCAPE':  # [CTRL + q] or [ESC]
        self.display_active = False
