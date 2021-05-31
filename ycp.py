import json
import youtube_dl

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
