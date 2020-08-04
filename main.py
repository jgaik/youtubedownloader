import tkinter as tk
from tkinter import ttk
import ttkwidgets
import pyperclip
import downloader as dl
import re


class App:
    TREE_MEDIA_HEIGHT_MIN = 1
    TREE_MEDIA_HEIGHT_MAX = 10

    def __init__(self, master):
        self.master = master

        self.map_media = {}
        self.map_columns = {
            "status": "Status",
            "title": "Title",
            "format": "Format",
            "dest": "Destination"
        }

        self.button_clipboard = ttk.Button(
            self.master, text="Add from clipboard", command=self.event_clipboard)

        self.entry_media_add = ttk.Entry(self.master)
        
        self.button_media_add = ttk.Button(self.master, text="Add", command=self.event_add)

        self.tree_media = ttkwidgets.CheckboxTreeview(
            self.master, height=self.TREE_MEDIA_HEIGHT_MAX, columns=tuple(self.map_columns.keys()))

        self.tree_media.heading("#0", text="URL ID")
        for (c_key, c_val) in self.map_columns.items():
            self.tree_media.heading(c_key, text=c_val)

        self.button_clipboard.pack()
        self.entry_media_add.pack()
        self.button_media_add.pack()
        self.tree_media.pack()

    def event_clipboard(self):
        urls = pyperclip.paste()
        for url in re.split(r'[\s,]+', urls):
            self.update_tree(url)

    def event_add(self):
        urls = self.entry_media_add.get()
        for url in re.split(r'[\s,]+', urls):
            self.update_tree(url)

    def event_tree_height(self):
        pass

    def update_tree(self, url):
        media_new = dl.Downloader(url)
        id = self.tree_media.insert('', 'end', text=media_new.media.url, values=(
            media_new.media.status.value, media_new.media.title))
        self.map_media[id] = media_new
        if media_new.type == dl.Type.PLAYLIST:
            for m in media_new.media_list:
                self.tree_media.insert(id, 'end', text=m.url, iid=m.idx,
                    values=(m.status.value, m.title))



if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    root.mainloop()
