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


class Downloader:

    def __init__(self, url):
        self._error = False
        opts = {
            'ignoreerrors': True
        }
        with yt.YoutubeDL(opts) as ytd:
            data_all = ytd.extract_info(url, download=False)
        self.data = {
            "url": data_all["id"],
            "title": data_all["title"],
        }
        if data_all is None:
            self.data["status"] = Status.ERROR_URL
            self.type = Type.SINGLE
            self.data["download"] = False
        else:
            if "entries" in data_all:
                medialist = data_all["entries"]
                if len(medialist) == 0:
                    self.type = Type.SINGLE
                    self.data["status"] = Status.ERROR_URL
                    self.data["download"] = False
                else:
                    self.data["count"] = 0
                    self.type = Type.PLAYLIST
                    self.data["media"] = []
                    self.data["status"] = Status.OK
                    for media in medialist:
                        if media is None:
                            self.data["media"].append({
                                "url": "-",
                                "status": Status.ERROR_URL,
                                "title": "-",
                                "download": False
                            })
                            self.data["status"] = Status.ERROR_URL
                        else:
                            self.data["media"].append({
                                "url": media["id"],
                                "status": Status.OK,
                                "title": media["title"],
                                "download": True
                            })
                        self.data["count"] += 1
            else:
                self.type = Type.SINGLE
                self.data["status"] = Status.OK
                self.data["download"] = True

    def info(self):
        return self.data

    def start(self):
        pass

    def update(self):
        pass
