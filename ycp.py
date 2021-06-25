import urwid
import json
import time
import youtube_dl
from youtube_dl.utils import DownloadError

class DownloadLogger(object):
    def __init__(self, parent):
        self.parent = parent

    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        self.parent.log_error(msg)

class MusicItem(urwid.WidgetWrap):
    def __init__(self, contents, on_select=None):
        self.contents = contents
        self.on_select = on_select

        self._columns = urwid.Columns([urwid.Text(c) for c in contents])
        self._focusable_columns = urwid.AttrMap(self._columns, '', 'reveal_focus')

        super(MusicItem, self).__init__(self._focusable_columns)

    def selectable(self):
        return True

    def update_contents(self, contents):
        self.contents[:] = contents
        for t, (w, _) in zip(contents, self._columns.contents):
            w.set_text(t)

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
    def __init__(self, items):
        self.items = items
        super().__init__(self.items)

    # Overriden
    def change_focus(self, size, position, offset_inset=0, coming_from=None, cursor_coords=None, snap_rows=None):
        super().change_focus(size,
                             position,
                             offset_inset,
                             coming_from,
                             cursor_coords,
                             snap_rows)


class MusicListView(urwid.Frame):
    signals = ['close']
    def __init__(self, music_list_file, height):
        self.height = height
        self.music_list_file = music_list_file
        self.HEADERS = ["Artist", "Title", "Link"]
        music_list = self.read_music_list()
        self.column_headers = urwid.AttrMap(urwid.Columns([urwid.Text(c) for c in self.HEADERS]), "column_headers")

        self.music_items = urwid.SimpleFocusListWalker([])
        for item in music_list["items"]:
            self.music_items.append(MusicItem([item["artist"], item["title"], item["link"]]))
        self.music_list = MusicList(self.music_items)

        super().__init__(self.music_list)

    def set_height(self, height):
        self.height = height

    def create_pop_up(self):
        pop_up = PopUpDialog()
        urwid.connect_signal(pop_up, 'close', lambda button: self.close_pop_up())
        return pop_up

    def add_music(self, artist, title, link):
        self.music_items.append(MusicItem([artist, title, link]))

    def edit_music(self, pos, artist, title, link):
        if pos >= 0:
            row = self.music_items[pos]
            row.update_data([artist, title, link])

    def get_item_count(self):
        return len(self.music_items)

    def get_music(self, pos):
        return self.music_items[pos].get_music_data()

    def get_all_musics(self):
        return [row.get_music_data() for row in self.music_items]

    def get_pop_up_parameters(self):
        return {'left': 0, 'top': 1, 'overlay_width': 32, 'overlay_height': 7}

    def read_music_list(self):
        f = open(self.music_list_file, "r")
        return json.load(f)

    def get_layout(self):
        return [urwid.Divider(u'─'),
                self.column_headers,
                urwid.Divider(u'─'),
                urwid.BoxAdapter(self.music_list, self.height - 3)]

    def get_focus_position(self):
        (_, pos) = self.music_list.get_focus()
        return pos

    def remove_item(self):
        (_, pos) = self.music_list.get_focus()
        if pos >= 0:
            del self.music_items[pos]

class App(object):
    def __init__(self):
        self.PALETTE = [
            ("column_headers", "white, bold", ""),
            ("notifier_active",   "dark cyan",  "light gray"),
            ("notifier_inactive", "black", "dark gray"),
            ("reveal_focus",      "black",      "dark cyan", "standout")
        ]

        # Get terminal size
        (self.terminal_cols, self.terminal_rows) = urwid.raw_display.Screen().get_cols_rows()

        self.music_list_file = "ycp.json"
        self.audio_format = "mp3"
        self.adding_music = False
        self.editing_music = False
        self.saving_music_list = False

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
        self.music_list_view = MusicListView(self.music_list_file, self.terminal_rows - 1) # status bar occupies one row
        self.view = urwid.SimpleFocusListWalker([])
        self.view.append(urwid.Pile(self.music_list_view.get_layout()))

        ######## status bar ########
        self.hint_text = "Q/ESC: Quit    A: Add    E: Edit    X: Remove    D: Download    S: Save to file"
        self.status_bar = urwid.Edit(self.hint_text)
        self.view.append(self.status_bar)

        self.list = urwid.ListBox(self.view)
        self.loop = urwid.MainLoop(self.music_list_view, self.PALETTE, input_filter = self.input_filter, unhandled_input = self.handle_input, pop_ups = True)

    def input_filter(self, keys, raw):
        if 'down' in keys:
            if self.music_list_view.get_item_count() == (self.music_list_view.get_focus_position() + 1):
                self.view.set_focus(self.view.focus)
                return []
        return keys

    def on_edit_item(self):
        self.handle_input('e')

    def handle_input(self, key):
        if key in ('q', 'Q', 'esc'):
            if self.adding_music or self.editing_music:
                self.adding_music = False
                self.editing_music = False
                self.display_edit_dialog(False)
            elif self.saving_music_list:
                self.view.set_focus(self.view.focus - 1)
                self.saving_music_list = False
            else:
                self.exit()

            self.set_status(self.hint_text)
        elif key in ('a', 'A'):
            self.adding_music = True
            self.display_edit_dialog(True)
            self.status_bar.set_caption("Adding music")
        elif key in ('e', 'E'):
            self.editing_music = True
            self.editing_music_pos = self.music_list_view.get_focus_position()
            data = self.music_list_view.get_music(self.editing_music_pos)
            self.display_edit_dialog(True, data)
            self.status_bar.set_caption("Editing music")
        elif key in ('d', 'D'):
            self.start_download()
        elif key in ('s', 'S'):
            self.saving_music_list = True
            self.status_bar.set_caption("Save as: ")
            self.status_bar.set_edit_text(self.music_list_file)
            self.status_bar.set_edit_pos(len(self.music_list_file))
            self.view.set_focus(self.view.focus + 1)
        elif key in ('x', 'X'):
            self.music_list_view.remove_item()
        elif key == 'enter':
            if self.saving_music_list:
                self.save_music_list(self.status_bar.get_edit_text())
                self.handle_input('q')

    def save_music_list(self, file_name):
        items = self.music_list_view.get_all_musics()
        with open(file_name, "w") as f:
            json.dump({"items": items}, f, indent = 4)

    def save_music(self, artist, title, link):
        if self.adding_music:
            self.music_list_view.add_music(artist, title, link)
        elif self.editing_music:
            self.music_list_view.edit_music(self.editing_music_pos, artist, title, link)
        self.handle_input('q')

    def display_edit_dialog(self, display, data = None):
        self.view.clear()
        if display:
            self.music_list_view.set_height(self.terminal_rows - 5)
            if data is not None:
                self.artist_edit.set_edit_text(data["artist"])
                self.title_edit.set_edit_text(data["title"])
                self.link_edit.set_edit_text(data["link"])
            self.view.append(urwid.Pile(self.item_editor + self.music_list_view.get_layout()))
        else:
            self.music_list_view.set_height(self.terminal_rows - 1)
            self.artist_edit.set_edit_text("")
            self.title_edit.set_edit_text("")
            self.link_edit.set_edit_text("")
            self.view.append(urwid.Pile(self.music_list_view.get_layout()))

        self.view.append(self.status_bar)

    def start_download(self):
        self.set_status("starting download......")
        time.sleep(1)

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': self.audio_format
            }],
            'logger': DownloadLogger(self),
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
            ydl_opts["outtmpl"] = "{0} - {1}.%(ext)s".format(item["artist"], item["title"], self.audio_format)
            try:
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([item["link"]])
                time.sleep(3)
            except DownloadError as e:
                status = "task {0}/{1} failed: {2}".format(self.ith_item + 1, self.num_items, str(e))
                time.sleep(8) # hang to let user read what happened

            self.ith_item += 1

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

    def set_status(self, caption, edit_text = ""):
        self.status_bar.set_caption(caption)
        self.status_bar.set_edit_text(edit_text)
        self.loop.draw_screen()

    def log_error(self, msg):
        self.set_status(msg)

    def exit(self):
        raise urwid.ExitMainLoop()

    def run(self):
        self.loop.run()

if __name__ == '__main__':
    App().run()
