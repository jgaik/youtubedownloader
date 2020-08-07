import tkinter.simpledialog as sdiag
import tkinter.filedialog as fdiag
import tkinter as tk
from tkinter import ttk
import ttkwidgets
#import pyperclip
import downloader as dl
import re
import threading as th
import concurrent.futures as concurr
import queue as q
import os

class App:
    TREE_MEDIA_HEIGHT_MIN = 1
    TREE_MEDIA_HEIGHT_MAX = 10

    class Format:
        AUDIO = "audio"
        VIDEO = "video"
        BOTH = "audio/video"

    class Column:
        URL = "#0"
        STATUS = "#1"
        TITLE = "#2"
        FORMAT = "#3"
        DESTINATION = "#4"

        @classmethod
        def to_columns(cls):
            attr = cls.__dict__
            out = []
            for a in attr:
                if not callable(getattr(cls, a)):
                    if not a.startswith("__"):
                        if attr[a] != "#0":
                            out.append(attr[a])
            return tuple(out)

    def __init__(self, master):
        self.master = master
        self._flag_update = False
        self._queue_media = q.Queue()

        self.map_media = {}

        self.button_clipboard = ttk.Button(
            self.master, text="Add from clipboard", command=th.Thread(target=self.event_clipboard).start)
        
        self.progress_info = ttk.Progressbasr(self.master)

        self.var_check_audio = tk.StringVar()
        self.var_check_audio.set(self.Format.VIDEO)
        self.check_audio = ttk.Checkbutton(self.master, text="Audio only (mp3)",
            onvalue=self.Format.AUDIO, offvalue=self.Format.VIDEO, variable=self.var_check_audio, command=self.event_check_audio)

        self.var_dir_default = tk.StringVar()
        self.var_dir_default.set(os.getcwd())
        label_dir_default = ttk.Label(self.master, text="Default directory")
        self.entry_dir_default = ttk.Entry(self.master, textvariable=self.var_dir_default)

        self.var_check_subdir = tk.BooleanVar()
        self.var_check_subdir.set(True)
        self.check_subdir = tk.Checkbutton(self.master, text="Playlists in subfolders", 
            onvalue=True, offvalue=False, variable=self.var_check_subdir)

        self.button_dir_default = ttk.Button(self.master, text="Change default", command=self.event_dir_default)

        self.tree_media = ttkwidgets.CheckboxTreeview(
            self.master, height=self.TREE_MEDIA_HEIGHT_MAX, columns=self.Column.to_columns())
        self.tree_media.bind("<Button-1>", self.event_tree_click)
        self.tree_media.bind("<Double-1>", self.event_tree_doubleclick)

        self.tree_media.heading(self.Column.URL, text="URL ID")
        self.tree_media.heading(self.Column.STATUS, text="Status")
        self.tree_media.heading(self.Column.TITLE, text="Title")
        self.tree_media.heading(self.Column.FORMAT, text="Format")
        self.tree_media.heading(self.Column.DESTINATION, text="Destination")

        self.tree_media.column(self.Column.FORMAT, anchor="center")

        self.button_clipboard.pack()
        self.check_audio.pack()
        self.tree_media.pack()
        label_dir_default.pack()
        self.entry_dir_default.pack()
        self.check_subdir.pack()
        self.button_dir_default.pack()

    def event_clipboard(self):
        self._flag_update = True
        th.Thread(target=self.update_tree).start()
        #urls = pyperclip.paste()
        urls = 'https://www.youtube.com/watch?v=hS5CfP8n_js, https://www.youtube.com/watch?v=0MW0mDZysxc, https://www.youtube.com/watch?v=xxSTOGFoDeg&list=PLrryvZ-gdCErP01mLIHNidblxMovnockz, https://www.youtube.com/watch?v=Owx3gcvark8'
        with concurr.ThreadPoolExecutor() as executor:
            executor.map(self.get_media_info, re.split(r'[\s,]+', urls))
        self._flag_update = False

    def get_media_info(self, url):
        self._queue_media.put(dl.Downloader(url))

    def update_tree(self):
        def statuscheck(media):
            if media.status == dl.Status.OK:
                return 'checked'
            else:
                return 'unchecked'

        while self._flag_update:
            media_new = self._queue_media.get()
        
            dest = ""
            if media_new.type == dl.Type.SINGLE:
                if media_new.media.status == dl.Status.OK:
                    dest = os.sep.join(["~", media_new.media.title]) 
                id = self.tree_media.insert('', 'end', text=media_new.media.url, 
                                            values=(
                                                    media_new.media.status.value, 
                                                    media_new.media.title, 
                                                    self.var_check_audio.get(),
                                                    dest),
                                            tags=statuscheck(media_new.media))
            if media_new.type == dl.Type.PLAYLIST:
                if self.var_check_subdir.get():
                    dest = os.sep.join(["~", media_new.media.title])
                else:
                    dest = "~" + os.sep
                id = self.tree_media.insert('', 'end', text=media_new.media.url, 
                                            values=(
                                                f"Extracted {len(media_new.media_list)} of {media_new.count}",
                                                media_new.media.title,
                                                self.var_check_audio.get(),
                                                dest),
                                            tags='checked')
                for m in media_new.media_list:
                    d = os.sep.join([dest, m.title])
                    self.tree_media.insert(id, 'end', text=m.url, 
                                            iid="_".join([id,str(m.idx)]),
                                            values=(
                                                m.status.value, 
                                                m.title, 
                                                self.var_check_audio.get(),
                                                d), 
                                            tags=statuscheck(m))
            self.map_media[id] = media_new

    def event_tree_click(self, event):
        x, y, widget = event.x, event.y, event.widget
        elem = widget.identify("element", x, y)
        item = self.tree_media.identify_row(y)
        if not item is None:
            val = self.tree_media.set(item, self.Column.FORMAT)
            parent = self.tree_media.parent(item)
            if not parent:
                children = self.tree_media.get_children(item)
        else:
            return
        if "image" in elem:
            if not dl.Status.ERROR_URL.value in val:
                if self.tree_media.tag_has("unchecked", item) or self.tree_media.tag_has("tristate", item):
                    self.tree_media._check_ancestor(item)
                    self.tree_media._check_descendant(item)
                else:
                    self.tree_media._uncheck_descendant(item)
                    self.tree_media._uncheck_ancestor(item)

        if self.tree_media.identify_column(x) == self.Column.FORMAT:
            if val == self.Format.AUDIO:
                self.tree_media.set(item, self.Column.FORMAT, self.Format.VIDEO)
                if parent:
                    vals_parent = self.tree_media.item(parent, option="values")
                    if all([self.tree_media.set(v, self.Column.FORMAT) == self.Format.VIDEO for v in self.tree_media.get_children(parent)]):
                        self.tree_media.set(parent, self.Column.FORMAT, self.Format.VIDEO)
                    else:
                        self.tree_media.set(parent, self.Column.FORMAT, self.Format.BOTH)
                else:
                    for child in children:
                        self.tree_media.set(child, self.Column.FORMAT, self.Format.VIDEO)
            else:
                self.tree_media.set(item, self.Column.FORMAT, self.Format.AUDIO)
                if parent:
                    vals_parent = self.tree_media.item(parent, option="values")
                    if all([self.tree_media.set(v, self.Column.FORMAT) == self.Format.AUDIO for v in self.tree_media.get_children(parent)]):
                        self.tree_media.set(parent, self.Column.FORMAT, self.Format.AUDIO)
                    else:
                        self.tree_media.set(parent, self.Column.FORMAT, self.Format.BOTH)
                else:
                    for child in children:
                        self.tree_media.set(child, self.Column.FORMAT, self.Format.AUDIO)
            if val == self.Format.BOTH:
                self.tree_media.set(item, self.Column.FORMAT, self.Format.VIDEO)
                for child in children:
                    self.tree_media.set(child, self.Column.FORMAT, self.Format.VIDEO)
            
            if all([self.tree_media.set(i, self.Column.FORMAT) == self.Format.AUDIO for i in self.tree_media.get_children()]):
                self.var_check_audio.set(self.Format.AUDIO)
            else:
                self.var_check_audio.set(self.Format.VIDEO)

    def event_tree_doubleclick(self, event):
        x, y = event.x, event.y
        item = self.tree_media.identify_row(y)
        if not item is None:
            parent = self.tree_media.parent(item)
            if not parent:
                children = self.tree_media.get_children(item)
        else:
            return
        if self.tree_media.identify_column(x) == self.Column.DESTINATION:
            if not parent:
                dest = self.tree_media.set(item, self.Column.DESTINATION)
                dir = dest.replace('~', self.var_dir_default.get())
                prev = dir.rfind(os.sep)
                if children and not os.path.isdir(dir) or not children:
                    dir = dir[0:prev]
            else:
                dest = self.tree_media.set(parent, self.Column.DESTINATION)
                if not os.path.isdir(dir:=dest.replace('~', self.var_dir_default.get())):
                    prev = dir.rfind(os.sep)
                    dir = dir[0:prev]
            dir_new = fdiag.askdirectory(initialdir=dir, mustexist=True)
            dest_new = dir_new.replace(self.var_dir_default.get(),'~')
            if dir_new:
                if not parent:
                    if not children:
                        self.tree_media.set(item, self.Column.DESTINATION, 
                            os.sep.join([dest_new, self.tree_media.set(item, self.Column.TITLE)]))
                    else:
                        self.tree_media.set(item, self.Column.DESTINATION, dest_new)
                        for child in children:
                            self.tree_media.set(child, self.Column.DESTINATION, 
                                os.sep.join([dest_new, self.tree_media.set(child, self.Column.TITLE)]))
                else:
                    self.tree_media.set(parent, self.Column.DESTINATION, dest_new)
                    for child in self.tree_media.get_children(parent):
                        self.tree_media.set(child, self.Column.DESTINATION, 
                            os.sep.join([dest_new, self.tree_media.set(child, self.Column.TITLE)]))

        if self.tree_media.identify_column(x) == self.Column.TITLE:
            title_old = self.tree_media.set(item, self.Column.TITLE)
            title_new = sdiag.askstring('Edit title', 'Enter new title', initialvalue=title_old)
            if title_new:
                self.tree_media.set(item, self.Column.TITLE, title_new)
                self.tree_media.set(item, self.Column.DESTINATION, 
                    self.tree_media.set(item, self.Column.DESTINATION).replace(title_old, title_new))
                if not parent:
                    if children:
                        for child in children:
                            self.tree_media.set(child, self.Column.DESTINATION, 
                                self.tree_media.set(child, self.Column.DESTINATION).replace(title_old, title_new))

    def event_check_audio(self):
        for child in self.tree_media.get_children():
            self.tree_media.set(child, self.Column.FORMAT, self.var_check_audio.get())
            for subchild in self.tree_media.get_children(child):
                self.tree_media.set(subchild, self.Column.FORMAT, self.var_check_audio.get())
    
    def event_dir_default(self):
        dir = fdiag.askdirectory(initialdir=self.var_dir_default.get(), mustexist=True)
        if dir:
            self.var_dir_default.set(dir)

if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    root.mainloop()
