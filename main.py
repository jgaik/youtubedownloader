import tkinter as tk
from tkinter import ttk
import ttkwidgets
#import pyperclip
import downloader as dl
import re
from concurrent.futures import ThreadPoolExecutor


class App:
    TREE_MEDIA_HEIGHT_MIN = 1
    TREE_MEDIA_HEIGHT_MAX = 10

    def __init__(self, master):
        self.master = master

        self.map_media = {}
        self.map_columns = {
            "#1": "Status",
            "#2": "Title",
            "#3": "Format",
            "#4": "Destination"
        }
        self.list_media_audio = []

        self.button_clipboard = ttk.Button(
            self.master, text="Add from clipboard", command=self.event_clipboard)

        self.entry_media_add = ttk.Entry(self.master)

        self.button_media_add = ttk.Button(
            self.master, text="Add", command=self.event_add)

        self.var_check_audio = tk.StringVar()
        self.var_check_audio.set("video")
        self.check_audio = ttk.Checkbutton(self.master, text="Audio only (mp3)",
            onvalue="audio", offvalue="video", variable=self.var_check_audio)

        self.tree_media = ttkwidgets.CheckboxTreeview(
            self.master, height=self.TREE_MEDIA_HEIGHT_MAX, columns=tuple(self.map_columns.keys()))
        self.tree_media.bind("<1>", self.event_tree_click)
        self.tree_media.bind("<Double-1>", self.event_tree_doubleclick)

        self.tree_media.heading("#0", text="URL ID")
        for (c_key, c_val) in self.map_columns.items():
            self.tree_media.heading(c_key, text=c_val)
        self.tree_media.column("#3", anchor="center")


        self.button_clipboard.pack()
        self.entry_media_add.pack()
        self.button_media_add.pack()
        self.check_audio.pack()
        self.tree_media.pack()

    def event_clipboard(self):
        #urls = pyperclip.paste()
        urls = 'https://www.youtube.com/watch?v=hS5CfP8n_js, https://www.youtube.com/watch?v=Gj6V-xZgtlQ&list=PLRza9ng-gU7xKHgkttUffXAkvhrv_ydqf'
        with ThreadPoolExecutor() as executor:
            result = executor.map(self.get_media_info,  re.split(r'[\s,]+', urls))
        for r in result:
            self.update_tree(r)

    def event_add(self):
        urls = self.entry_media_add.get()
        urls = 'https://www.youtube.com/watch?v=hS5CfP8n_js, https://www.youtube.com/watch?v=Gj6V-xZgtlQ&list=PLRza9ng-gU7xKHgkttUffXAkvhrv_ydqf'
        with ThreadPoolExecutor() as executor:
            result = executor.map(self.get_media_info,  re.split(r'[\s,]+', urls))
        for r in result:
            self.update_tree(r)

    def get_media_info(self, url):
        return dl.Downloader(url)

    def update_tree(self, media_new):
        if media_new.type == dl.Type.SINGLE:
            id = self.tree_media.insert('', 'end', text=media_new.media.url, values=(
                media_new.media.status.value, media_new.media.title, self.var_check_audio.get()))
            self.map_media[id] = media_new
        if media_new.type == dl.Type.PLAYLIST:
            id = self.tree_media.insert('', 'end', text=media_new.media.url, values=(
                f"Extracted {len(media_new.media_list)} of {media_new.count}", media_new.media.title, "-"))
            self.map_media[id] = media_new
            for m in media_new.media_list:
                self.tree_media.insert(id, 'end', text=m.url, iid="_".join([id,str(m.idx)]),values=(m.status.value, m.title, self.var_check_audio.get()))

    def event_tree_click(self, event):
        if self.tree_media.identify_column(event.x) == "#3":
            id = self.tree_media.identify_row(event.y)
            if not id is None:
                vals = list(self.tree_media.item(id, option='values'))
                if vals[2] == "audio":
                    self.list_media_audio.remove(id)
                    vals[2] = "video"
                else:
                    self.list_media_audio.append(id)
                    vals[2] = "audio"
                self.tree_media.item(id, **{'values': tuple(vals)})

    def event_tree_doubleclick(self, event):
        if self.tree_media.identify_column(event.x) == "#0":
            print(self.tree_media.identify_row(event.y))
        if self.tree_media.identify_column(event.x) == "#4":
            print(self.tree_media.identify_row(event.y))

if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    root.mainloop()
