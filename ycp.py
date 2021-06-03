import json
import youtube_dl
import npyscreen

class MusicList(npyscreen.Form):
    def create(self):
       self.musicList = self.add(npyscreen.GridColTitles,
                                 col_titles = ["artist", "title"],
                                 columns = 2,
                                 select_whole_line = True)
       self.musicList.set_grid_values_from_flat_list(["a", "b"])

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

