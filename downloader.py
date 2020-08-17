import youtube_dl as yt
import threading as th

class Format:
    AUDIO = "audio"
    VIDEO = "video"
    BOTH = "audio/video"


class Type:
    PLAYLIST = 1
    SINGLE = 0


class Status:
    ERROR_URL = "URL Error"
    ERROR_DOWNLOAD = "Download Error"
    OK = "Ok"
    DOWNLOAD = "Downloading..."
    DONE = "Done"


class Media:

    def __init__(self, url='', title='', status=Status.OK, idx=0):
        self.url = url
        self.title = title
        self.status = status
        self.idx = idx

class Downloader:

    def __init__(self, url):
        self._error = False
        self._flag_download = th.Event()
        self.opts = {
            'ignoreerrors': True
        }
        with yt.YoutubeDL(self.opts) as ytd:
            data_all = ytd.extract_info(url, download=False)

        if data_all is None:
            self.media = Media(url=url, status=Status.ERROR_URL)
            self.type = Type.SINGLE
        else:
            self.media = Media(url=data_all["id"],
                               title=data_all["title"])
            if "entries" in data_all:
                medialist = data_all["entries"]
                self.count = 0
                self.type = Type.PLAYLIST
                self.playlist_idx = []
                self.media_list = []
                self.media.status = Status.OK
                for media in medialist:
                    if not media is None:
                        self.media_list.append(
                            Media(url=media["id"],
                                  title=media["title"],
                                  idx=self.count))
                        self.playlist_idx.append(self.count)
                    self.count += 1
                if not self.media_list:
                    self.type = Type.SINGLE
                    self.media.status = Status.ERROR_URL
            else:
                self.type = Type.SINGLE
                self.media.status = Status.OK

    def start(self, format, name, dest):
        opts = {
            'format': 'bestaudio/best',
            '''
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }],
            '''
            'ignoreerrors': False,
            'simulate': False,
        }
        try:
            with yt.YoutubeDL(opts) as ydl:
                ydl.download([self.media.url])
            self.media.status = Status.DONE
            self._flag_download.set()
        except e:
            self.media.status = Status.ERROR_DOWNLOAD
            self._flag_download.set()

    def wait_download(self):
        self._flag_download.wait()
