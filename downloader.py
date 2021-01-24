# pylint: disable=attribute-defined-outside-init, C0114, C0115, C0116, invalid-name, unused-argument
from threading import Event
import os
import json
import youtube_dl as yt


def extractMedia(url):
    opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'ignoreerrors': True,
    }
    with yt.YoutubeDL(opts) as ydl:
        data_all = ydl.extract_info(url, download=False)

    if data_all is None:
        media = Media(url=url, status=Status.ERROR_URL, downloader=False)
        media_out = media
    else:
        if "entries" in data_all:
            media = Media(url=data_all["id"],
                          title=data_all["title"], downloader=False)
            medialist = data_all["entries"]
            media_list = [Media(url=m["id"], title=m["title"])
                          for m in medialist if not m is None]
            if not media_list:
                media.status = Status.ERROR_URL
                media_out = media
            else:
                media.count = len(data_all["entries"])
                media_out = (media, media_list)
        else:
            media = Media(url=data_all["id"], title=data_all["title"])
            media_out = media
    return media_out


class Format:
    AUDIO = "audio"
    VIDEO = "video"
    BOTH = "audio/video"


class Status:
    ERROR_URL = "URL Error"
    ERROR_DOWNLOAD = "Download Error"
    OK = "Ok"
    DOWNLOAD = "Downloading..."
    DONE = "Done"


class Media:

    def __init__(self, url='', title='', status=Status.OK, downloader=True):
        self.url = url
        self.title = title
        self.status = status
        self.format = None
        self._downloadable = False
        if downloader:
            self._flag_download = Event()
            self._downloadable = True

    def start_download(self, dest):
        if self._downloadable:
            opts = {
                'quiet': True,
                'ignoreerrors': True,
                'progress_hooks': [self.hook],
                'outtmpl': dest + self.title.replace(os.sep, "") + ".%(ext)s"
            }
            if self.format == Format.AUDIO:
                opts['format'] = 'bestaudio/best'
                opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3'
                }]
            if self.format == Format.VIDEO:
                opts['format'] = 'bestvideo+bestaudio/best'
            with yt.YoutubeDL(opts) as _ydl:
                _ydl.download([self.url])

    def wait_download(self):
        self._flag_download.wait()

    def hook(self, dl_data):
        if dl_data['status'] == 'finished':
            self.status = Status.DONE
            self._flag_download.set()
        if dl_data['status'] == 'error':
            self.status = Status.ERROR_DOWNLOAD
            self._flag_download.set()

    def __repr__(self):
        dic = self.__dict__
        keys = [k for k in dic if k[0] != "_"]
        return json.dumps(
            {
                'class': self.__class__.__name__,
                'fields': {(k, dic[k]) for k in keys}
            }, indent=4)
