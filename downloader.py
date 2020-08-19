import youtube_dl as yt
from threading import Event
import os
from collections.abc import Sequence
import json


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
            opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'ignoreerrors': True,
                'progress_hooks': [self.hook]
            }
            self._ydl = yt.YoutubeDL(opts)

    def start_download(self, dest):
        if self._downloadable:
            self._ydl.params['outtmpl'] = dest + "%(id)s"
            if self.format == Format.AUDIO:
                self._ydl.params['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3'
                }]
                self._ydl.params['outtmpl'] += ".mp3"
            if self.format == Format.VIDEO:
                self._ydl.params['outtmpl'] += ".mp4"
            self._ydl.download([self.url])

    def wait_download(self):
        self._flag_download.wait()

    def hook(self, dl_data):
        if dl_data['status'] == 'finished':
            self.status = Status.DONE
            os.rename(dl_data['filename'], dl_data['filename'].replace(
                self.url, self.title))
            self._flag_download.set()
        if dl_data['status'] == 'error':
            self.status = Status.ERROR_DOWNLOAD
            self._flag_download.set()

    def __repr__(self):
        dic = self.__dict__
        keys = [k for k in dic.keys() if k[0] != "_"]
        return json.dumps({'class': self.__class__.__name__, 'fields': dict([(k, dic[k]) for k in keys])}, indent=4)
