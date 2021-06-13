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
        self.on_edit_callback = on_edit_callback
        self.HEADERS = ["Artist", "Title", "Link"]
        music_list = self.read_music_list()
        self.ENTRIES = [[item["artist"], item["title"], item["link"]] for item in music_list["items"]]
        column_headers = urwid.AttrMap(urwid.Columns([urwid.Text(c) for c in self.HEADERS]), "column_headers")

        rows = []
        for entry in self.ENTRIES:
            row = SelectableRow(entry, self.on_edit_callback)
            rows.append(row)
        self.content = urwid.SimpleFocusListWalker(rows)
        self.listbox = MyListBox(self.content)

        # Get terminal dimensions
        terminal_cols, terminal_rows = urwid.raw_display.Screen().get_cols_rows()
        list_rows = (terminal_rows - 2) if (terminal_rows > 7) else 5
        self.list_box = urwid.BoxAdapter(self.listbox, list_rows)

        self.layout = [
            urwid.Divider(u'─'),
            column_headers,
            urwid.Divider(u'─'),
            self.list_box,
            urwid.Divider(u'─'),
        ]

    def create_pop_up(self):
        pop_up = PopUpDialog()
        urwid.connect_signal(pop_up, 'close',
            lambda button: self.close_pop_up())
        return pop_up

    def get_pop_up_parameters(self):
        return {'left':0, 'top':1, 'overlay_width':32, 'overlay_height':7}

    def read_music_list(self):
        f = open("ycp.json", "r")
        return json.load(f)

    def get_layout(self):
        return self.layout

"""
class PopUpDialog(urwid.WidgetWrap):
    signals = ['close']
    def __init__(self):
        close_button = urwid.Button("that's pretty cool")
        urwid.connect_signal(close_button, 'click',
            lambda button:self._emit("close"))
        pile = urwid.Pile([urwid.Text(
            "^^  I'm attached to the widget that opened me. "
            "Try resizing the window!\n"), close_button])
        fill = urwid.Filler(pile)
        self.__super.__init__(urwid.AttrWrap(fill, 'popbg'))


class ThingWithAPopUp(urwid.PopUpLauncher):
    def __init__(self):
        self.music_list = MusicList().get_layout()
        self.__super.__init__(urwid.Button("click-me"))
        urwid.connect_signal(self.original_widget, 'click',
            lambda button: self.open_pop_up())

    def create_pop_up(self):
        pop_up = PopUpDialog()
        urwid.connect_signal(pop_up, 'close',
            lambda button: self.close_pop_up())
        return pop_up

    def get_pop_up_parameters(self):
        return {'left':0, 'top':1, 'overlay_width':32, 'overlay_height':7}
"""

class App(object):
    def __init__(self):
        self.PALETTE = [
            ("column_headers", "white, bold", ""),
            ("notifier_active",   "dark cyan",  "light gray"),
            ("notifier_inactive", "black", "dark gray"),
            ("reveal_focus",      "black",      "dark cyan", "standout")
        ]

        self.music_list = MusicList(self.on_edit_item).get_layout()
        # self.layout = urwid.ListBox(self.music_list.get_layout())

        self.display_edit = False
        self.view = urwid.SimpleFocusListWalker([])
        self.view.append(urwid.Pile(self.music_list))
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
        self.handle_input('a')

    def handle_input(self, key):
        if key in ('q', 'Q', 'esc'):
            self.exit()
        elif key in ('a', 'A'):
            self.view.clear()
            if self.display_edit:
                self.view.append(urwid.Pile(self.music_list))
                self.display_edit = False
            else:
                item_editor = [urwid.Edit(u"Artist: ", u""), urwid.Edit(u"Title: ", u""), urwid.Edit(u"Link: ", u"")]
                item_editor.append(urwid.Columns([urwid.Button(u"Save"), urwid.Button(u"Cancel")]))
                self.view.append(urwid.Pile(item_editor + self.music_list))
                self.display_edit = True

    def exit(self):
        raise urwid.ExitMainLoop()

    def run(self):
        self.loop.run()

if __name__ == '__main__':
    App().run()
