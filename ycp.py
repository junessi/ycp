import urwid
import json
import time
import youtube_dl
import argparse
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


class MusicListView(urwid.Frame):
    signals = ['close']
    def __init__(self, music_list_file, height):
        self.height = height
        self.music_list_file = music_list_file
        self.HEADERS = ["Artist", "Title", "Link"]
        music_list = self.read_music_list()
        self.header = urwid.Pile([urwid.Divider('─'),
                                  urwid.AttrMap(urwid.Columns([urwid.Text(c) for c in self.HEADERS]), "column_headers"),
                                  urwid.Divider('─')])

        self.hint_text = "Q/ESC: Quit    A: Add    E: Edit    X: Remove    D: Download    S: Save to file"
        self.footer = urwid.Edit(self.hint_text)

        self.music_items = urwid.SimpleFocusListWalker([])
        for item in music_list["items"]:
            self.music_items.append(MusicItem([item["artist"], item["title"], item["link"]]))
        self.music_list = MusicList(self.music_items)

        super().__init__(self.music_list, self.header, self.footer)

    def set_footer_text(self, caption, etext = "", pos = -1):
        self.footer.set_caption(caption)
        if len(etext):
            self.footer.set_edit_text(etext)
            self.footer.set_edit_pos(pos if pos >= 0 else len(etext))

    def get_footer_text(self):
        return self.footer.get_edit_text()

    def reset_footer_text(self):
        self.footer.set_caption(self.hint_text)
        self.footer.set_edit_text("")

    def set_height(self, height):
        self.height = height

    def create_pop_up(self):
        pop_up = PopUpDialog()
        urwid.connect_signal(pop_up, 'close', lambda button: self.close_pop_up())
        return pop_up

    def add_music(self, artist, title, link):
        self.music_items.append(MusicItem([artist, title, link]))

    def edit_music(self, pos, artist, title, link):
        if pos >= 0 and pos < len(self.music_items):
            self.music_items[pos].update_data([artist, title, link])

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
                self.header,
                urwid.Divider(u'─'),
                urwid.BoxAdapter(self.music_list, self.height - 3)]

    def get_focus_position(self):
        (_, pos) = self.music_list.get_focus()
        return pos

    def set_focus_position(self, pos):
        if pos >= 0:
            self.music_list.set_focus(pos)

    def remove_item(self):
        (_, pos) = self.music_list.get_focus()
        if pos >= 0:
            del self.music_items[pos]


class Downloader(object):
    def __init__(self, items, status_callback):
        """
        Parameters:
        item (list): A list contains items to download.
        status_callback (function): A function is called when a status is triggered.
                                    status: started, downloading, downloaded, finished, error.
        """

        self.downloading_items = items
        self.status_callback = status_callback
        self.audio_format = 'mp3'
        self.downloading_item = None

    def start(self):
        self.status_callback_hook({'status': 'started'})

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': self.audio_format
            }],
            'logger': DownloadLogger(self),
            'progress_hooks': [self.status_callback_hook],
        }

        self.downloading_item_index = 0
        self.downloading_items_count = len(self.downloading_items)
        for item in self.downloading_items:
            self.downloading_item = item
            ydl_opts["outtmpl"] = "{0} - {1}.%(ext)s".format(item["artist"], item["title"], self.audio_format)
            try:
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([item["link"]])
            except DownloadError as e:
                self.status_callback_hook({'status': 'error'})

            self.downloading_item_index += 1

    def status_callback_hook(self, data):
        if self.downloading_item:
            data['artist']          = self.downloading_item['artist']
            data['title']           = self.downloading_item['title']
            data['link']            = self.downloading_item['link']
            data['audio_format']    = self.audio_format
            data['index'] = self.downloading_item_index
            data['count'] = self.downloading_items_count

        self.status_callback(data)

    def log_error(self, msg):
        self.status_callback_hook({'error_msg': msg})


class App(object):
    def __init__(self, music_list_file = None):
        self.PALETTE = [
            ("column_headers", "white, bold", ""),
            ("notifier_active",   "dark cyan",  "light gray"),
            ("notifier_inactive", "black", "dark gray"),
            ("reveal_focus",      "black",      "dark cyan", "standout")
        ]

        # Get terminal size
        (self.terminal_cols, self.terminal_rows) = urwid.raw_display.Screen().get_cols_rows()

        self.music_list_file = "ycp.json" if music_list_file is None else music_list_file
        self.audio_format = "mp3"
        self.adding_music = False
        self.editing_music = False
        self.saving_music_list = False
        self.item_editor_height = 4

        self.create_edit_dialog()
        self.create_music_list_view()

        self.main_view = urwid.Pile([('weight', self.terminal_rows - self.item_editor_height, self.music_list_view)])
        self.loop = urwid.MainLoop(self.main_view, self.PALETTE, unhandled_input = self.handle_input, pop_ups = True)

    def refresh_main_view(self, display_item_editor = False, data = None):
        self.main_view.contents.clear()
        if display_item_editor:
            self.main_view.contents.append((self.item_editor, ('weight', self.item_editor_height)))
            if data is not None:
                self.artist_edit.set_edit_text(data["artist"])
                self.title_edit.set_edit_text(data["title"])
                self.link_edit.set_edit_text(data["link"])
        self.main_view.contents.append((self.music_list_view, ('weight', self.terminal_rows - self.item_editor_height)))

    def create_edit_dialog(self):
        self.artist_edit = urwid.Edit(u"Artist: ", u"")
        self.title_edit = urwid.Edit(u"Title: ", u"")
        self.link_edit = urwid.Edit(u"Link: ", u"")
        save_button = urwid.Button(u"Save", lambda button : self.save_music(self.artist_edit.get_edit_text(),
                                                                            self.title_edit.get_edit_text(),
                                                                            self.link_edit.get_edit_text()))
        cancel_button = urwid.Button(u"Cancel", lambda button : self.handle_input('q'))
        self.item_editor = urwid.ListBox(urwid.SimpleFocusListWalker([self.artist_edit,
                                                                      self.title_edit,
                                                                      self.link_edit,
                                                                      urwid.Columns([save_button, cancel_button])]))

    def create_music_list_view(self):
        self.music_list_view = MusicListView(self.music_list_file, self.terminal_rows - 1) # status bar occupies one row

    def on_edit_item(self):
        self.handle_input('e')

    def handle_input(self, key):
        if key in ('q', 'Q', 'esc'):
            if self.adding_music or self.editing_music:
                self.adding_music = False
                self.editing_music = False
                self.refresh_main_view()
            elif self.saving_music_list:
                self.music_list_view.set_focus('body')
                self.saving_music_list = False
            else:
                self.exit()

            self.reset_status()
        elif key in ('a', 'A'):
            self.adding_music = True
            self.refresh_main_view(True)
            self.set_status("Adding music")
        elif key in ('e', 'E'):
            self.editing_music = True
            self.editing_music_pos = self.music_list_view.get_focus_position()
            data = self.music_list_view.get_music(self.editing_music_pos)
            self.refresh_main_view(True, data)
            self.set_status("Editing music")
        elif key in ('d', 'D'):
            self.start_download()
        elif key in ('s', 'S'):
            self.saving_music_list = True
            self.edit_save_file_name()
        elif key in ('x', 'X'):
            self.music_list_view.remove_item()
        elif key == 'enter':
            if self.saving_music_list:
                self.save_music_list(self.music_list_view.get_footer_text())
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

    def start_download(self):
        d = Downloader(self.music_list_view.get_all_musics(), self.progress_hook)
        d.start()

    def progress_hook(self, data):
        if data['status'] == 'started':
            self.set_status("preparing download......")
            time.sleep(1)

        elif data['status'] == 'downloading':
            status = "task {0}/{1}: downloading({2}) {3} - {4}.{5}, speed: {6}".format(data['index'] + 1,
                                                                                       data['count'],
                                                                                       data['_percent_str'],
                                                                                       data['artist'],
                                                                                       data['title'],
                                                                                       data['audio_format'],
                                                                                       data['_speed_str'])
            self.set_status(status)
        elif data['status'] == 'error':
            status = "task {0}/{1} failed: {2}".format(data['index'] + 1, data['count'], str(e))
            self.set_status(status)
            time.sleep(8) # hang to let user read what happened

        elif data['status'] == 'finished':
            status = "task {0}/{1}: {2} downloaded".format(data['index'], data['count'], data["filename"])
            self.set_status(status)
            status = "task {0}/{1}: converting to {2} - {3}.{4}".format(data['index'] + 1,
                                                                        data['count'],
                                                                        data['artist'],
                                                                        data['title'],
                                                                        data['audio_format'])
            self.set_status(status)

            if (data['index'] + 1) == data['count']:
                self.set_status("All tasks are finished.")
                time.sleep(2)
                self.reset_status()


    def set_status(self, caption):
        self.music_list_view.set_footer_text(caption)
        self.loop.draw_screen()

    def reset_status(self):
        self.music_list_view.reset_footer_text()

    def edit_save_file_name(self):
        self.music_list_view.set_footer_text("Save as: ", self.music_list_file)
        self.music_list_view.set_focus('footer')

    def exit(self):
        raise urwid.ExitMainLoop()

    def run(self):
        self.loop.run()


def progress_hook(data):
    if data['status'] == 'started':
        print("preparing download......")

    elif data['status'] == 'downloading':
        status = "task {0}/{1}: downloading({2}) {3} - {4}.{5}, speed: {6}".format(data['index'] + 1,
                                                                                   data['count'],
                                                                                   data['_percent_str'],
                                                                                   data['artist'],
                                                                                   data['title'],
                                                                                   data['audio_format'],
                                                                                   data['_speed_str'])
        print(status)
    elif data['status'] == 'error':
        print("error occured: {0}".format(data['error_msg']))

    elif data['status'] == 'finished':
        print("finished")


def start_download(file_name):
    f = open(file_name, "r")
    data = json.load(f)
    d = Downloader(data['items'], progress_hook)
    d.start()
    

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description = 'Download youtube videos as audios')
    ap.add_argument('-f', dest = 'jsonpath', action = 'store')
    ap.add_argument('-d', dest = 'download_directly', action = 'store_true')
    args = ap.parse_args()

    if args.download_directly:
        start_download(args.jsonpath)
    else:
        App(args.jsonpath).run()
