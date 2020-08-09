import tkinter.simpledialog as sdiag
import tkinter.filedialog as fdiag
import tkinter as tk
from tkinter import ttk
import ttkwidgets
# import pyperclip
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
        def to_columns(cls, all=False):
            attr = cls.__dict__
            out = []
            for a in attr:
                if not callable(getattr(cls, a)):
                    if not a.startswith("__"):
                        if all:
                            out.append(attr[a])
                        elif attr[a] != "#0":
                            out.append(attr[a])
            return tuple(out)

    def __init__(self, master):
        self.master = master
        self._flag_update = False
        self._queue_media = q.Queue()
        self._flag_download = False

        self.map_media = {}

        self.frame_add = ttk.Frame(self.master)
        self.frame_dir = ttk.Frame(self.master)
        self.frame_tree = ttk.Frame(self.master)

        self.style_progress = ttk.Style(self.master)
        self.style_progress.layout('Horizontal.TProgressbar',
                                   [('Horizontal.Progressbar.trough', {
                                       'children': [('Horizontal.Progressbar.pbar', {'side': 'left', 'sticky': 'ns'})],
                                       'sticky': 'nswe'}),
                                       ('Horizontal.Profressbar.label', {'sticky': ''})])

        self.button_clipboard = ttk.Button(
            self.frame_add, text="Add from clipboard", command=self.event_clipboard)
        self.button_download = ttk.Button(
            self.frame_add, text="Download selected", command=self.event_download)
        self.var_check_audio = tk.StringVar()
        self.var_check_audio.set(self.Format.VIDEO)
        self.check_audio = ttk.Checkbutton(self.frame_add, text="Audio only (mp3)",
                                           onvalue=self.Format.AUDIO, offvalue=self.Format.VIDEO, variable=self.var_check_audio, command=self.event_check_audio)

        self.var_dir_default = tk.StringVar()
        self.var_dir_default.set(os.path.expanduser("~"))
        label_dir_default = ttk.Label(self.frame_dir, text="Default directory")
        self.entry_dir_default = ttk.Entry(
            self.frame_dir, textvariable=self.var_dir_default, state=tk.DISABLED, width=len(
                self.var_dir_default.get()))
        self.entry_dir_default.bind("<Double-1>", self.event_dir_default)

        self.var_check_subdir = tk.BooleanVar()
        self.var_check_subdir.set(True)
        self.check_subdir = ttk.Checkbutton(self.frame_dir, text="Playlists in subfolders",
                                            onvalue=True, offvalue=False, variable=self.var_check_subdir)

        self.button_dir_default = ttk.Button(
            self.frame_dir, text="Change default", command=self.event_dir_default)

        self.tree_media = ttkwidgets.CheckboxTreeview(
            self.frame_tree, height=self.TREE_MEDIA_HEIGHT_MAX, columns=self.Column.to_columns())
        self.tree_media.bind("<Button-1>", self.event_tree_click)
        self.tree_media.bind("<Double-1>", self.event_tree_doubleclick)

        self.tree_media.heading(self.Column.URL, text="URL ID")
        self.tree_media.heading(self.Column.STATUS, text="Status")
        self.tree_media.heading(self.Column.TITLE, text="Title")
        self.tree_media.heading(self.Column.FORMAT, text="Format")
        self.tree_media.heading(self.Column.DESTINATION, text="Destination")

        self.tree_media.column(self.Column.STATUS, width=150)
        self.tree_media.column(self.Column.FORMAT, anchor="center", width=100)
        self.tree_media.column(self.Column.TITLE, width=350)

        l = sum([self.tree_media.column(c, option='width')
                 for c in self.Column.to_columns(True)])
        self.progress_info = ttk.Progressbar(self.master, length=l)

        self.frame_add.grid(row=0, column=0)
        self.frame_tree.grid(row=1, column=0)
        self.frame_dir.grid(row=0, column=1, rowspan=2)

        self.button_clipboard.grid(row=0, column=0)
        self.check_audio.grid(row=0, column=1)
        self.button_download.grid(row=0, column=2)

        self.tree_media.grid()

        label_dir_default.grid(row=0, column=0)
        self.entry_dir_default.grid(row=1, column=0)
        self.check_subdir.grid(row=2, column=0)
        self.button_dir_default.grid(row=3, column=0)
        self.progress_info.grid(row=2, column=0)

    def progress_start(self, max, text):
        self.progress_info['maximum'] = max
        self.style_progress.configure(
            'Horizontal.TProgressbar', text=text)

    def progress_update(self):
        self.progress_info['value'] += 1

    def progress_reset(self):
        self.progress_info['value'] = 0
        self.style_progress.configure(
            'Horizontal.TProgressbar', text='')

    def event_clipboard(self):
        if not self._flag_update and not self._flag_download:
            thread = th.Thread(target=self.thread_clipboard)
            thread.start()

    def event_download(self):
        pass

    def thread_clipboard(self):
        self._flag_update = True
        th.Thread(target=self.update_tree).start()
        # urls = pyperclip.paste()
        urls = 'https://www.youtube.com/watch?v=hS5CfP8n_js, https://www.youtube.com/watch?v=0MW0mDZysxc, https://www.youtube.com/playlist?list=PLiM-0FYH7IQ-awx_UzfJd6XwiZP--dnli, https://www.youtube.com/watch?v=Owx3gcvark8'
        urls = re.split(r'[\s,]+', urls)
        self.progress_start(len(urls), 'Retrieving info..')
        with concurr.ThreadPoolExecutor() as executor:
            executor.map(self.get_media_info, urls)
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
                    dest = "~"
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
                                           iid="_".join([id, str(m.idx)]),
                                           values=(
                                               m.status.value,
                                               m.title,
                                               self.var_check_audio.get(),
                                               d),
                                           tags=statuscheck(m))
            self.map_media[id] = media_new
            self.progress_update()
        self.progress_reset()

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
                self.tree_media.set(
                    item, self.Column.FORMAT, self.Format.VIDEO)
                if parent:
                    if all([self.tree_media.set(v, self.Column.FORMAT) == self.Format.VIDEO for v in self.tree_media.get_children(parent)]):
                        self.tree_media.set(
                            parent, self.Column.FORMAT, self.Format.VIDEO)
                    else:
                        self.tree_media.set(
                            parent, self.Column.FORMAT, self.Format.BOTH)
                else:
                    for child in children:
                        self.tree_media.set(
                            child, self.Column.FORMAT, self.Format.VIDEO)
            else:
                self.tree_media.set(
                    item, self.Column.FORMAT, self.Format.AUDIO)
                if parent:
                    if all([self.tree_media.set(v, self.Column.FORMAT) == self.Format.AUDIO for v in self.tree_media.get_children(parent)]):
                        self.tree_media.set(
                            parent, self.Column.FORMAT, self.Format.AUDIO)
                    else:
                        self.tree_media.set(
                            parent, self.Column.FORMAT, self.Format.BOTH)
                else:
                    for child in children:
                        self.tree_media.set(
                            child, self.Column.FORMAT, self.Format.AUDIO)
            if val == self.Format.BOTH:
                self.tree_media.set(
                    item, self.Column.FORMAT, self.Format.VIDEO)
                for child in children:
                    self.tree_media.set(
                        child, self.Column.FORMAT, self.Format.VIDEO)

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
                if not os.path.isdir(dir := dest.replace('~', self.var_dir_default.get())):
                    prev = dir.rfind(os.sep)
                    dir = dir[0:prev]
            dir_new = fdiag.askdirectory(initialdir=dir, mustexist=True)
            if dir_new:
                dest_new = dir_new.replace(self.var_dir_default.get(), '~')
                if not parent:
                    if not children:
                        self.tree_media.set(item, self.Column.DESTINATION,
                                            os.sep.join([dest_new, self.tree_media.set(item, self.Column.TITLE)]))
                    else:
                        self.tree_media.set(
                            item, self.Column.DESTINATION, dest_new)
                        for child in children:
                            self.tree_media.set(child, self.Column.DESTINATION,
                                                os.sep.join([dest_new, self.tree_media.set(child, self.Column.TITLE)]))
                else:
                    self.tree_media.set(
                        parent, self.Column.DESTINATION, dest_new)
                    for child in self.tree_media.get_children(parent):
                        self.tree_media.set(child, self.Column.DESTINATION,
                                            os.sep.join([dest_new, self.tree_media.set(child, self.Column.TITLE)]))

        if self.tree_media.identify_column(x) == self.Column.TITLE:
            title_old = self.tree_media.set(item, self.Column.TITLE)
            title_new = sdiag.askstring(
                'Edit title', 'Enter new title', initialvalue=title_old)
            if title_new:
                self.tree_media.set(item, self.Column.TITLE, title_new)
                self.tree_media.set(item, self.Column.DESTINATION,
                                    self.tree_media.set(item, self.Column.DESTINATION).replace(title_old, title_new))
                if not parent:
                    if children:
                        for child in children:
                            self.tree_media.set(child, self.Column.DESTINATION,
                                                self.tree_media.set(child, self.Column.DESTINATION).replace(title_old, title_new))

        if not self.tree_media.identify_column(x) == self.Column.STATUS:
            self.tree_media.item(
                item, open=not self.tree_media.item(item, 'open'))

    def event_check_audio(self):
        for child in self.tree_media.get_children():
            self.tree_media.set(child, self.Column.FORMAT,
                                self.var_check_audio.get())
            for subchild in self.tree_media.get_children(child):
                self.tree_media.set(
                    subchild, self.Column.FORMAT, self.var_check_audio.get())

    def event_dir_default(self, event):
        dir = fdiag.askdirectory(
            initialdir=self.var_dir_default.get(), mustexist=True)
        if dir:
            self.var_dir_default.set(dir)


if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    root.mainloop()
