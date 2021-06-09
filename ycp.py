import json
import youtube_dl
import npyscreen
import os.path
import sys

class MusicList(npyscreen.ActionForm):
    def create(self):
       self.music_list = self.load_music_list()
       self.musicList = self.add(npyscreen.GridColTitles,
                                 col_titles = ["{0}{1}link".format("artist".ljust(32), "title".ljust(32))],
                                 columns = 1,
                                 column_margin = 0,
                                 values = [["{0}{1}{2}".format(item["artist"].ljust(32),
                                                               item["title"].ljust(32),
                                                               item["link"])]
                                           for item in self.music_list["items"]],
                                 select_whole_line = True)

       self.OK_BUTTON_TEXT = "Exit"
       self.CANCEL_BUTTON_TEXT = "Download"

    def load_music_list(self):
        list_file = "ycp.json"
        if os.path.isfile(list_file):
            return json.load(open(list_file, "r"))

        return {}

    def on_ok(self):
        sys.exit(0)

    def on_cancel(self):
        audio_format = "mp3"
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': audio_format
            }]
        }

        for item in self.music_list["items"]:
            print(item)
            ydl_opts["outtmpl"] = "{0} - {1}.%(ext)s".format(item["artist"], item["title"], audio_format)
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([item["link"]])


class MyApplication(npyscreen.NPSAppManaged):
   def onStart(self):
       self.addForm('MAIN', MusicList)

if __name__ == '__main__':
    TestApp = MyApplication().run()


