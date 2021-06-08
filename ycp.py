import json
import youtube_dl
import npyscreen
import os.path
import sys

class MusicList(npyscreen.ActionForm):
    def create(self):
       music_list = self.load_music_list()
       self.musicList = self.add(npyscreen.GridColTitles,
                                 col_titles = ["artist", "title", "link"],
                                 columns = 3,
                                 column_margin = 0,
                                 values = [[item["artist"], item["title"], item["link"]] for item in music_list["items"]],
                                 select_whole_line = True)

    def load_music_list(self):
        list_file = "ycp.json"
        if os.path.isfile(list_file):
            return json.load(open(list_file, "r"))

        return {}

    def on_ok(self):
        sys.exit(0)

class MyApplication(npyscreen.NPSAppManaged):
   def onStart(self):
       self.addForm('MAIN', MusicList)
       # A real application might define more forms here.......

if __name__ == '__main__':
    TestApp = MyApplication().run()

    """
    f = open("ycp.json", "r")
    file_dict = json.load(f)

    audio_format = "mp3"
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': audio_format
        }]
    }

    for item in file_dict["items"]:
        print(item)
        ydl_opts["outtmpl"] = "{0} - {1}.%(ext)s".format(item["artist"], item["title"], audio_format)
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([item["link"]])
    """

