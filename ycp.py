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
        if self.on_select and key in ('enter',):
            self.on_select(self)
        return key

    def __repr__(self):
        return '%s(contents=%r)' % (self.__class__.__name__, self.contents)

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

class App(object):

    def __init__(self):
        self.HEADERS = ["Artist", "Title", "Link"]
        music_list = self.read_music_list()
        self.ENTRIES = [[item["artist"], item["title"], item["link"]] for item in music_list["items"]]
        self.PALETTE = [
            ("column_headers", "white, bold", ""),
            ("notifier_active",   "dark cyan",  "light gray"),
            ("notifier_inactive", "black", "dark gray"),
            ("reveal_focus",      "black",      "dark cyan", "standout")
        ]

        column_headers = urwid.AttrMap(urwid.Columns([urwid.Text(c) for c in self.HEADERS]), "column_headers")

        contents = [SelectableRow(entry) for entry in self.ENTRIES]
        self.listbox = MyListBox(urwid.SimpleFocusListWalker(contents), self.update_notifiers)

        # Get terminal dimensions
        terminal_cols, terminal_rows = urwid.raw_display.Screen().get_cols_rows()
        list_rows = (terminal_rows - 2) if (terminal_rows > 7) else 5

        master_pile = urwid.Pile([
            urwid.Divider(u'─'),
            column_headers,
            urwid.Divider(u'─'),
            urwid.BoxAdapter(self.listbox, list_rows),
            urwid.Divider(u'─'),
        ])

        music_list = urwid.Filler(master_pile, 'top')
        self.loop = urwid.MainLoop(music_list, self.PALETTE, unhandled_input = self.exit_app)

    def read_music_list(self):
        f = open("ycp.json", "r")
        return json.load(f)

    def update_notifiers(self, size, position, offset_inset, coming_from, cursor_coords, snap_rows):
        pass

    def exit_app(self, key):
        if key in ('q', 'Q', 'esc'):
            raise urwid.ExitMainLoop()

    def run(self):
        self.loop.run()

if __name__ == '__main__':
    App().run()
