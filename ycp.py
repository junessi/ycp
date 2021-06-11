import json
import youtube_dl
import npyscreen
import os.path
import sys
import time
import curses

class DownloadLogger(object):
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)

class MusicList(npyscreen.ActionForm):
    def create(self):
       self.load_music_list()
       self.musicList = self.add(npyscreen.GridColTitles,
                                 col_titles = ["{0}{1}link".format("artist".ljust(32), "title".ljust(32))],
                                 columns = 1,
                                 column_margin = 0,
                                 values = [["{0}{1}{2}".format(item["artist"].ljust(32),
                                                               item["title"].ljust(32),
                                                               item["link"])]
                                           for item in self.music_list["items"]],
                                 select_whole_line = True)

       self.audio_format = "mp3"
       self.OK_BUTTON_TEXT = "Exit"
       self.CANCEL_BUTTON_TEXT = "Download"
       self.add_handlers({"a": self.add_music})

    def add_music(self, s):
        print(s)
        self.parentApp.change_form("AddMusic")

    def load_music_list(self):
        list_file = "ycp.json"
        self.music_list = {}
        if os.path.isfile(list_file):
            items = json.load(open(list_file, "r"))
            if "items" in items:
                self.music_list = items

    def on_ok(self):
        sys.exit(0)

    def on_cancel(self):
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': self.audio_format
            }],
            'logger': DownloadLogger(), # avoid outputing to stdout
            'progress_hooks': [self.progress_hook],
        }

        self.download_popup = npyscreen.Popup(name="")
        self.download_popup.preserve_selected_widget = True
        self.mlw = self.download_popup.add(npyscreen.Pager,)
        self.download_popup.center_on_display()
        self.download_popup.display()
        self.num_items = len(self.music_list["items"])
        self.ith_item = 0
        for item in self.music_list["items"]:
            self.ith_item += 1
            self.mlw.values = ["task {0}/{1}".format(self.ith_item, self.num_items),
                               "starting download {0} - {1}".format(item["artist"], item["title"])]
            self.downloading_item = item
            self.download_popup.display()
            time.sleep(2)
            ydl_opts["outtmpl"] = "{0} - {1}.%(ext)s".format(item["artist"], item["title"], self.audio_format)
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([item["link"]])

        # delay closing popup for 3 seconds
        self.mlw.values = ["{0} task(s) finished".format(self.num_items)]
        self.download_popup.display()
        time.sleep(3)

    def progress_hook(self, d):
        status = ["task {0}/{1}".format(self.ith_item, self.num_items)]
        if d['status'] == 'finished':
            status.append("downloaded to {0}".format(d["filename"]))
            status.append("converting to {0}".format(self.audio_format))
        elif d['status'] == 'downloading':
            status.append("downloading {0} - {1}".format(self.downloading_item["artist"],
                                                         self.downloading_item["title"]))

        self.mlw.values = status
        self.download_popup.display()

class AddMusicForm(npyscreen.Form):
    def on_ok(self):
        # self.parentApp.switchFormPrevious()
        self.parentApp.setNextForm("MAIN")

    def create(self):
        self.artist = self.add(npyscreen.TitleText, name="Artist: ")
        self.title = self.add(npyscreen.TitleText, name="Title: ")
        self.link = self.add(npyscreen.TitleText, name="Link: ")

    def afterEditing(self):
        self.parentApp.setNextForm("MAIN")

class MyApplication(npyscreen.NPSAppManaged):
    def onStart(self):
        self.addForm('MAIN', MusicList)
        self.addForm('AddMusic', AddMusicForm)

    def change_form(self, name):
        self.switchForm(name)

if __name__ == '__main__':
    TestApp = MyApplication().run()


