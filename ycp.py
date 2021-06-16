import urwid
import json

class SelectableRow(urwid.WidgetWrap):
    def __init__(self, contents, on_select=None):
        self.contents = contents
        self.on_select = on_select

        self._columns = urwid.Columns([urwid.Text(c) for c in contents])
        self._focusable_columns = urwid.AttrMap(self._columns, '', 'reveal_focus')

        super(SelectableRow, self).__init__(self._focusable_columns)

    def selectable(self):
        return True

    def update_contents(self, contents):
        # update the list record inplace...
        self.contents[:] = contents

        # ... and update the displayed items
        for t, (w, _) in zip(contents, self._columns.contents):
            w.set_text(t)

    def keypress(self, size, key):
        if self.on_select:
            if key == 'enter':
                self.on_select()
            elif key in ('e', 'E'):
                self.on_select()

        return key

    def get_music_data(self, pos):
        if pos >= 0:
            (artist_col, _) = self._columns.contents[0]
            (title_col, _)  = self._columns.contents[1]
            (link_col, _)   = self._columns.contents[2]
            return {"artist": artist_col.text,
                    "title":  title_col.text,
                    "link":   link_col.text}

    def update_data(self, data):
        if len(data) == len(self.contents):
            (artist_col, _) = self._columns.contents[0]
            artist_col.set_text(data[0])
            (title_col, _) = self._columns.contents[1]
            title_col.set_text(data[1])
            (link_col, _) = self._columns.contents[2]
            link_col.set_text(data[2])

class MyListBox(urwid.ListBox):
    def __init__(self, body, on_focus_change=None):
        super().__init__(body)

        self.on_focus_change = on_focus_change

    # Overriden
    def change_focus(self, size, position, offset_inset=0, coming_from=None, cursor_coords=None, snap_rows=None):
        super().change_focus(size,
                             position,
                             offset_inset,
                             coming_from,
                             cursor_coords,
                             snap_rows)

        # Implement a hook to be able to deposit additional logic
        if self.on_focus_change != None:
            self.on_focus_change(size,
                                 position,
                                 offset_inset,
                                 coming_from,
                                 cursor_coords,
                                 snap_rows)

class MusicList(urwid.PopUpLauncher):
    signals = ['close']
    def __init__(self, on_edit_callback = None):
        self.music_list_file = "ycp.json"
        self.on_edit_callback = on_edit_callback
        self.HEADERS = ["Artist", "Title", "Link"]
        music_list = self.read_music_list()
        self.ENTRIES = [[item["artist"], item["title"], item["link"]] for item in music_list["items"]]
        column_headers = urwid.AttrMap(urwid.Columns([urwid.Text(c) for c in self.HEADERS]), "column_headers")

        self.selectable_rows = []
        for entry in self.ENTRIES:
            row = SelectableRow(entry)
            self.selectable_rows.append(row)
        self.content = urwid.SimpleFocusListWalker(self.selectable_rows)
        self.listbox = MyListBox(self.content)

        # Get terminal dimensions
        terminal_cols, terminal_rows = urwid.raw_display.Screen().get_cols_rows()
        list_rows = (terminal_rows - 3) if (terminal_rows > 7) else 5
        self.list_box = urwid.BoxAdapter(self.listbox, list_rows)

        self.layout = [
            urwid.Divider(u'─'),
            column_headers,
            urwid.Divider(u'─'),
            self.list_box
        ]

    def create_pop_up(self):
        pop_up = PopUpDialog()
        urwid.connect_signal(pop_up, 'close',
            lambda button: self.close_pop_up())
        return pop_up

    def add_music(self, artist, title, link):
        self.content.append(SelectableRow([artist, title, link]))

    def edit_music(self, pos, artist, title, link):
        if pos >= 0:
            item = self.selectable_rows[pos]
            item.update_data([artist, title, link])

    def get_music(self, pos):
        return self.selectable_rows[pos].get_music_data(pos)

    def get_pop_up_parameters(self):
        return {'left': 0, 'top': 1, 'overlay_width': 32, 'overlay_height': 7}

    def read_music_list(self):
        f = open(self.music_list_file, "r")
        return json.load(f)

    def get_layout(self):
        return self.layout

    def get_cursor_position(self):
        (_, pos) = self.listbox.get_focus()
        return pos

class App(object):
    def __init__(self):
        self.PALETTE = [
            ("column_headers", "white, bold", ""),
            ("notifier_active",   "dark cyan",  "light gray"),
            ("notifier_inactive", "black", "dark gray"),
            ("reveal_focus",      "black",      "dark cyan", "standout")
        ]

        self.music_list = MusicList(self.on_edit_item)

        self.artist_edit = urwid.Edit(u"Artist: ", u"")
        self.title_edit = urwid.Edit(u"Title: ", u"")
        self.link_edit = urwid.Edit(u"Link: ", u"")
        self.item_editor = [self.artist_edit, self.title_edit, self.link_edit]
        self.save_button = urwid.Button(u"Save", lambda button : self.save_music(self.artist_edit.get_edit_text(),
                                                                                 self.title_edit.get_edit_text(),
                                                                                 self.link_edit.get_edit_text()
                                                                                 ))
        self.cancel_button = urwid.Button(u"Cancel", lambda button : self.handle_input('q'))
        self.item_editor.append(urwid.Columns([self.save_button, self.cancel_button]))

        self.adding_music = False
        self.editing_music = False
        self.display_edit = False
        self.view = urwid.SimpleFocusListWalker([])
        self.view.append(urwid.Pile(self.music_list.get_layout()))
        self.list = urwid.ListBox(self.view)
        self.loop = urwid.MainLoop(self.list, self.PALETTE, unhandled_input = self.handle_input, pop_ups = True)

        """
        fill = urwid.Filler(urwid.Padding(ThingWithAPopUp(), 'center', 15))
        self.loop = urwid.MainLoop(
            fill,
            [('popbg', 'white', 'dark blue')],
            pop_ups=True)
        """

    def on_edit_item(self):
        self.handle_input('e')

    def handle_input(self, key):
        if key in ('q', 'Q', 'esc'):
            if self.adding_music or self.editing_music:
                self.adding_music = False
                self.editing_music = False
                self.display_edit_dialog(False)
            else:
                self.exit()
        elif key in ('a', 'A'):
            self.adding_music = True
            self.display_edit_dialog(True)
        elif key in ('e', 'E'):
            self.editing_music = True
            self.editing_music_pos = self.music_list.get_cursor_position()
            data = self.music_list.get_music(self.editing_music_pos)
            self.display_edit_dialog(True, data)

    def save_music(self, artist, title, link):
        if self.adding_music:
            self.music_list.add_music(artist, title, link)
        elif self.editing_music:
            self.music_list.edit_music(self.editing_music_pos, artist, title, link)
        self.handle_input('q')

    def display_edit_dialog(self, display, data = None):
        self.view.clear()
        if display:
            if data is not None:
                self.artist_edit.set_edit_text(data["artist"])
                self.title_edit.set_edit_text(data["title"])
                self.link_edit.set_edit_text(data["link"])
            self.view.append(urwid.Pile(self.item_editor + self.music_list.get_layout()))
        else:
            self.artist_edit.set_edit_text("")
            self.title_edit.set_edit_text("")
            self.link_edit.set_edit_text("")
            self.view.append(urwid.Pile(self.music_list.get_layout()))

    def exit(self):
        raise urwid.ExitMainLoop()

    def run(self):
        self.loop.run()

if __name__ == '__main__':
    App().run()
