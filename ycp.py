import urwid
import json
import time
import youtube_dl

class DownloadLogger(object):
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)

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
        self.contents[:] = contents
        for t, (w, _) in zip(contents, self._columns.contents):
            w.set_text(t)

    def keypress(self, size, key):
        if self.on_select:
            if key == 'enter':
                self.on_select()
            elif key in ('e', 'E'):
                self.on_select()

        return key

    def get_music_data(self):
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

class MusicList(urwid.ListBox):
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

class MusicListView(object):
    signals = ['close']
    def __init__(self):
        self.music_list_file = "ycp.json"
        self.HEADERS = ["Artist", "Title", "Link"]
        music_list = self.read_music_list()
        column_headers = urwid.AttrMap(urwid.Columns([urwid.Text(c) for c in self.HEADERS]), "column_headers")

        self.selectable_rows = []
        for item in music_list["items"]:
            row = SelectableRow([item["artist"], item["title"], item["link"]])
            self.selectable_rows.append(row)
        self.music_items = urwid.SimpleFocusListWalker(self.selectable_rows)
        self.music_list = MusicList(self.music_items)

        # Get terminal dimensions
        (_, terminal_rows) = urwid.raw_display.Screen().get_cols_rows()
        # edit dialog occupies 3 rows and status bar occupis 1 row,
        # so we minus 4 rows from total, rest for the music list.
        height = terminal_rows - 4
        self.list_box = urwid.BoxAdapter(self.music_list, height)

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
        self.music_items.append(SelectableRow([artist, title, link]))

    def edit_music(self, pos, artist, title, link):
        if pos >= 0:
            row = self.selectable_rows[pos]
            row.update_data([artist, title, link])

    def get_music(self, pos):
        return self.selectable_rows[pos].get_music_data()

    def get_all_musics(self):
        return [row.get_music_data() for row in self.selectable_rows]

    def get_pop_up_parameters(self):
        return {'left': 0, 'top': 1, 'overlay_width': 32, 'overlay_height': 7}

    def read_music_list(self):
        f = open(self.music_list_file, "r")
        return json.load(f)

    def get_layout(self):
        return self.layout

    def get_cursor_position(self):
        (_, pos) = self.music_list.get_focus()
        return pos

class App(object):
    def __init__(self):
        self.PALETTE = [
            ("column_headers", "white, bold", ""),
            ("notifier_active",   "dark cyan",  "light gray"),
            ("notifier_inactive", "black", "dark gray"),
            ("reveal_focus",      "black",      "dark cyan", "standout")
        ]

        self.audio_format = "mp3"
        self.adding_music = False
        self.editing_music = False

        ######## edit dialog ########
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

        ######## music list ########
        self.music_list_view = MusicListView()
        self.view = urwid.SimpleFocusListWalker([])
        self.view.append(urwid.Pile(self.music_list_view.get_layout()))

        ######## status bar ########
        self.status_bar = urwid.Text("status")
        self.view.append(self.status_bar)

        self.list = urwid.ListBox(self.view)
        self.loop = urwid.MainLoop(self.list, self.PALETTE, unhandled_input = self.handle_input, pop_ups = True)

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
            self.editing_music_pos = self.music_list_view.get_cursor_position()
            data = self.music_list_view.get_music(self.editing_music_pos)
            self.display_edit_dialog(True, data)
        elif key in ('d', 'D'):
            self.start_download()

    def save_music(self, artist, title, link):
        if self.adding_music:
            self.music_list_view.add_music(artist, title, link)
        elif self.editing_music:
            self.music_list_view.edit_music(self.editing_music_pos, artist, title, link)
        self.handle_input('q')

    def display_edit_dialog(self, display, data = None):
        self.view.clear()
        if display:
            if data is not None:
                self.artist_edit.set_edit_text(data["artist"])
                self.title_edit.set_edit_text(data["title"])
                self.link_edit.set_edit_text(data["link"])
            self.view.append(urwid.Pile(self.item_editor + self.music_list_view.get_layout()))
        else:
            self.artist_edit.set_edit_text("")
            self.title_edit.set_edit_text("")
            self.link_edit.set_edit_text("")
            self.view.append(urwid.Pile(self.music_list_view.get_layout()))

    def start_download(self):
        self.set_status("starting download......")
        time.sleep(1)

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': self.audio_format
            }],
            'logger': DownloadLogger(), # avoid outputing to stdout
            'progress_hooks': [self.progress_hook],
        }

        self.ith_item = 0
        self.downloading_items = self.music_list_view.get_all_musics()
        self.num_items = len(self.downloading_items)
        for item in self.downloading_items:
            status = "task {0}/{1}: downloading {2} - {3}".format(self.ith_item + 1,
                                                                  self.num_items,
                                                                  item["artist"],
                                                                  item["title"])
            self.set_status(status)
            time.sleep(2)
            ydl_opts["outtmpl"] = "{0} - {1}.%(ext)s".format(item["artist"], item["title"], self.audio_format)
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([item["link"]])

            self.ith_item += 1

        time.sleep(1)
        self.set_status("download finished")

    def progress_hook(self, d):
        if d['status'] == 'finished':
            status = "task {0}/{1}: {2}".format(self.ith_item, self.num_items, d["filename"])
            self.set_status(status)
            status = "task {0}/{1}: converting to {2} - {3}.{4}".format(self.ith_item + 1,
                                                                        self.num_items,
                                                                        self.downloading_items[self.ith_item]["artist"],
                                                                        self.downloading_items[self.ith_item]["title"],
                                                                        self.audio_format)
            self.set_status(status)
        elif d['status'] == 'downloading':
            status = "task {0}/{1}: downloading {2} - {3}".format(self.ith_item + 1,
                                                                  self.num_items,
                                                                  self.downloading_items[self.ith_item]["artist"],
                                                                  self.downloading_items[self.ith_item]["title"])
            self.set_status(status)

    def set_status(self, status_text):
        self.status_bar.set_text(status_text)
        self.loop.draw_screen()

    def exit(self):
        raise urwid.ExitMainLoop()

    def run(self):
        self.loop.run()

if __name__ == '__main__':
    App().run()
