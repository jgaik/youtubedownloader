import youtube_dl as yt
import enum


class Type(enum.Enum):
    PLAYLIST = enum.auto()
    SINGLE = enum.auto()


class Status(enum.Enum):
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
        opts = {
            'ignoreerrors': True
        }
        with yt.YoutubeDL(opts) as ytd:
            data_all = ytd.extract_info(url, download=False)

        self.media = Media(url=data_all["id"],
                           title=data_all["title"])
        if data_all is None:
            self.media.status = Status.ERROR_URL
            self.type = Type.SINGLE
        else:
            if "entries" in data_all:
                medialist = data_all["entries"]
                self.count = 0
                self.type = Type.PLAYLIST
                self.media_list = []
                self.media.status = Status.OK
                for media in medialist:
                    if not media is None:
                        self.media_list.append(
                            Media(url=media["id"],
                                    title=media["title"],
                                    idx=self.count))
                    self.count += 1
                if not self.media_list:
                    self.type = Type.SINGLE
                    self.media.status = Status.ERROR_URL
            else:
                self.type = Type.SINGLE
                self.media.status = Status.OK

    def info(self):
        return self.data

    def start(self):
        pass

    def update(self):
        pass
