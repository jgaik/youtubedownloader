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
from collections.abc import MutableSequence


class AskString(sdiag.Dialog):

    def __init__(self, title, prompt, initialvalue, parent=None):
        if not parent:
            parent = tk._default_root
        self.prompt = prompt
        self.initialvalue = initialvalue
        sdiag.Dialog.__init__(self, parent, title)

    def body(self, master):

        label_prompt = ttk.Label(master, text=self.prompt, justify=tk.LEFT)
        label_prompt.grid(row=0, padx=5, sticky='w')

        self.entry = ttk.Entry(master, name='entry',
                               width=len(self.initialvalue))
        self.entry.grid(row=1, padx=5, sticky='we')

        self.entry.insert(0, self.initialvalue)
        self.entry.select_range(0, tk.END)

        self.update()
        self.geometry("+0+0")
        self.resizable(False, False)
        return self.entry

    def buttonbox(self):

        box = ttk.Frame(self)

        w = ttk.Button(box, text="OK", width=10,
                       command=self.ok, default=tk.ACTIVE)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = ttk.Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side=tk.LEFT, padx=5, pady=5)

        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

        box.pack()

    def validate(self):
        self.result = self.entry.get()
        return 1

    def destroy(self):
        self.entry = None
        sdiag.Dialog.destroy(self)


def askstring(title, prompt, initialvalue, **kw):
    d = AskString(title=title, prompt=prompt,
                  initialvalue=initialvalue, **kw)
    return d.result


class App:

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
        self._queue_media = q.Queue()
        self._flag_update = False
        self._flag_download = False

        self.map_media = {}

        self.frame_view = ttk.Frame(self.master)
        self.frame_control = ttk.Frame(self.master)
        self.frame_add = ttk.Frame(self.frame_control)
        self.frame_dir = ttk.Frame(self.frame_control)

        self.style_progress = ttk.Style(self.master)
        self.style_progress.layout('Horizontal.TProgressbar',
                                   [('Horizontal.Progressbar.trough', {
                                       'children': [('Horizontal.Progressbar.pbar', {'side': 'left', 'sticky': 'ns'})],
                                       'sticky': 'nswe'}),
                                       ('Horizontal.Profressbar.label', {'sticky': ''})])

        # widgets
        # frame_setup
        # frame_add - adding urls
        self.button_clipboard = ttk.Button(
            self.frame_add, text="Add from clipboard", command=self.event_add)
        self.var_check_audio = tk.StringVar()
        self.var_check_audio.set(dl.Format.VIDEO)
        self.check_audio = ttk.Checkbutton(self.frame_add, text="Audio only (mp3)",
                                           onvalue=dl.Format.AUDIO, offvalue=dl.Format.VIDEO, variable=self.var_check_audio, command=self.event_check_audio)

        # frame_dir - default directory
        label_dir_default = ttk.Label(
            self.frame_dir, text="Default directory:")
        self.var_dir_default = tk.StringVar()
        self.var_dir_default.set(os.path.expanduser("~"))
        self.entry_dir_default = ttk.Entry(
            self.frame_dir, textvariable=self.var_dir_default, state=tk.DISABLED)
        self.entry_dir_default.bind("<Double-1>", self.event_dir_default)
        self.entry_dir_default.bind("<Button-4>", self.event_dir_scroll_up)
        self.entry_dir_default.bind("<Button-5>", self.event_dir_scroll_down)

        self.button_dir_default = ttk.Button(
            self.frame_dir, text="...", width=2, command=self.event_dir_default)

        self.var_check_subdir = tk.BooleanVar()
        self.var_check_subdir.set(True)
        self.check_subdir = ttk.Checkbutton(self.frame_dir, text="Playlists in subfolders",
                                            onvalue=True, offvalue=False, variable=self.var_check_subdir)

        # no subframe
        self.button_download = ttk.Button(
            self.frame_control, text="Download selected", command=self.event_download)
        self.button_clear = ttk.Button(
            self.frame_control, text="Clear", width=5, command=self.event_clear)

        # frame_view
        self.tree_media = ttkwidgets.CheckboxTreeview(
            self.frame_view, columns=self.Column.to_columns(), selectmode='none')
        self.tree_media.bind("<Button-1>", self.event_tree_click)
        self.tree_media.bind("<Double-1>", self.event_tree_doubleclick)

        self.tree_media.heading(self.Column.URL, text="URL ID")
        self.tree_media.heading(self.Column.STATUS, text="Status")
        self.tree_media.heading(self.Column.TITLE, text="Title")
        self.tree_media.heading(self.Column.FORMAT, text="Format")
        self.tree_media.heading(self.Column.DESTINATION, text="Destination")

        self.tree_media.column(
            self.Column.URL, minwidth=70, width=130, stretch=True)
        self.tree_media.column(
            self.Column.STATUS, minwidth=120, width=150, stretch=True)
        self.tree_media.column(
            self.Column.TITLE, width=300, minwidth=100, stretch=True)
        self.tree_media.column(
            self.Column.FORMAT, anchor="center", minwidth=100, width=100, stretch=False)
        self.tree_media.column(self.Column.DESTINATION,
                               minwidth=100, stretch=True)

        self.progress_info = ttk.Progressbar(self.frame_view)

        # layout settings
        # mainframe
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_rowconfigure(0, weight=1)

        self.frame_view.grid(row=0, column=0, sticky="nswe", padx=15, pady=5)
        self.frame_control.grid(
            row=0, column=1, sticky="ns", padx=5, pady=10)

        # frame_view
        self.frame_view.grid_columnconfigure(0, weight=1)
        self.frame_view.grid_rowconfigure(0, weight=1)

        self.tree_media.grid(sticky="nswe", pady=5)
        self.progress_info.grid(row=1, column=0, sticky="we", pady=7)

        # frame_control
        self.frame_dir.grid(row=0, column=0, columnspan=2,
                            sticky="nwe", padx=10, pady=10)
        self.frame_add.grid(row=1, column=0, columnspan=2,
                            sticky="we", padx=10, pady=10)
        self.button_download.grid(
            row=2, column=0, sticky="ws", pady=15, padx=10)
        self.button_clear.grid(row=2, column=1, sticky='se', pady=15, padx=10)

        # frame_dir
        label_dir_default.grid(
            row=0, column=0, columnspan=2, sticky='swe', pady=5)
        self.entry_dir_default.grid(row=1, column=0, sticky='nwe', ipady=3)
        self.button_dir_default.grid(row=1, column=1, sticky='e', padx=5)
        self.check_subdir.grid(
            row=2, column=0, columnspan=2, sticky='nw', pady=5)

        # frame_add
        self.button_clipboard.pack(fill='x')
        self.check_audio.pack(fill='x', pady=5)

        # window
        self.master.title("YouTube downloader")
        self.master.update()
        w_max = self.master.winfo_screenwidth()
        w_opt = self.master.winfo_width()
        h_max = self.master.winfo_screenheight()
        h_opt = self.master.winfo_height()
        w_min = min(w_max, w_opt - 350)
        h_min = min(h_max, h_opt)
        w_out = min(w_opt, w_max)
        h_out = h_min

        pos_x = int((w_max - w_out)/2)
        pos_y = int((h_max - h_out)/5)
        self.master.geometry(f"{w_out}x{h_out}+{pos_x}+{pos_y}")
        self.master.minsize(w_min, h_min)

    def progress_prepare(self, max=0, text=None):
        self.progress_info['maximum'] += max
        if not text is None:
            self.style_progress.configure(
                'Horizontal.TProgressbar', text=text)

    def progress_update(self):
        self.progress_info['value'] += 1

    def progress_reset(self):
        self.progress_info['value'] = 0
        self.style_progress.configure(
            'Horizontal.TProgressbar', text='')
        self.progress_info['maximum'] = 0

    def event_add(self, url=None):
        self.progress_prepare(text='Retrieving info..')
        if not self._flag_download:
            self._flag_update = True
            if url is None:
                # url = pyperclip.paste()
                url = 'https://youtu.be/JKHTdzAvI, https://www.youtube.com/watch?v=0MW0mDZysxc, https://www.youtube.com/playlist?list=PLiM-0FYH7IQ-awx_UzfJd6XwiZP--dnli, https://www.youtube.com/watch?v=Owx3gcvark8'
                url = re.split(r'[\s,]+', url)
                self.progress_prepare(len(url))
            else:
                self.progress_prepare(1)
            th.Thread(target=self.thread_url_parser, args=(url,)).start()
            th.Thread(target=self.thread_update_tree).start()

    def thread_url_parser(self, url_data):
        with concurr.ThreadPoolExecutor() as executor:
            if isinstance(url_data, MutableSequence):
                executor.map(self.queue_media_info, [(u, None) for u in url_data])
            else:
                executor.submit(self.queue_media_info, (url_data, self.tree_media.focus()))
        self._flag_update = False

    def queue_media_info(self, url_tuple):
        self._queue_media.put((dl.Downloader(url_tuple[0]), url_tuple[1]))

    def thread_update_tree(self):
        def statuscheck(media):
            if media.status == dl.Status.OK:
                return 'checked'
            else:
                return 'unchecked'

        while self._flag_update:
            (media_new, id_change) = self._queue_media.get()

            dest = ""
            format = self.var_check_audio.get()
            if media_new.type == dl.Type.SINGLE:
                if media_new.media.status == dl.Status.OK:
                    dest = os.sep.join(["~", media_new.media.title])
                else:
                    format = ""
                if id_change:
                    id = id_change
                    data = {
                        'text': media_new.media.url,
                        'values': (
                            media_new.media.status,
                            media_new.media.title,
                            format,
                            dest),
                        'tags': statuscheck(media_new.media)
                    }
                    self.tree_media.item(id, **data)
                else:
                    id = self.tree_media.insert('', 'end', text=media_new.media.url,
                                                values=(
                                                    media_new.media.status,
                                                    media_new.media.title,
                                                    format,
                                                    dest),
                                                tags=statuscheck(media_new.media))
            if media_new.type == dl.Type.PLAYLIST:
                if self.var_check_subdir.get():
                    dest = os.sep.join(["~", media_new.media.title])
                else:
                    dest = ""

                if id_change:
                    id = id_change
                    data = {
                        'text': media_new.media.url,
                        'values': (
                            f"Extracted {len(media_new.media_list)} of {media_new.count}",
                            media_new.media.title,
                            format,
                            dest),
                        'tags': statuscheck(media_new.media)
                    }
                    self.tree_media.item(id, **data)
                else:
                    id = self.tree_media.insert('', 'end', text=media_new.media.url,
                                                values=(
                                                    f"Extracted {len(media_new.media_list)} of {media_new.count}",
                                                    media_new.media.title,
                                                    format,
                                                    dest),
                                                tags='checked')
                for m in media_new.media_list:
                    if self.var_check_subdir.get():
                        d = os.sep.join([dest, m.title])
                    else:
                        d = os.sep.join(["~", m.title])
                    self.tree_media.insert(id, 'end', text=m.url,
                                           iid="_".join([id, str(m.idx)]),
                                           values=(
                                               m.status,
                                               m.title,
                                               self.var_check_audio.get(),
                                               d),
                                           tags=statuscheck(m))
            self.map_media[id] = media_new
            self.progress_update()
        self.progress_reset()

    def event_download(self):
        if not self._flag_download and not self._flag_update:
            items = [item for item in self.tree_media.get_children()
                     if not 'unchecked' in self.tree_media.item(item)['tags']]
            th.Thread(target=self.thread_download_tree, args=(items,)).start()

    def event_clear(self):
        self.tree_media.delete(*self.tree_media.get_children())
        self.map_media = {}

    def thread_download_tree(self, items):
        self._flag_download = True
        with concurr.ThreadPoolExecutor() as executor:
            executor.map(self.thread_download_media, items)
        self._flag_download = False

    def thread_download_media(self, item):
        downloader = self.map_media[item]
        print(downloader)
        if downloader.type == dl.Type.PLAYLIST:
            pass
        if downloader.type == dl.Type.SINGLE:
            name = self.tree_media.set(item, self.Column.TITLE)
            dest = self.tree_media.set(item, self.Column.DESTINATION).replace('~', self.var_dir_default.get()).replace(name,'')
            th.Thread(target=downloader.start, args=(self.tree_media.set(item, self.Column.FORMAT), name,dest)).start()
            self.tree_media.set(item, self.Column.STATUS, dl.Status.DOWNLOAD)
            downloader.wait_download()
            self.tree_media.set(item, self.Column.STATUS, downloader.media.status)




    def event_tree_click(self, event):
        x, y, widget = event.x, event.y, event.widget
        elem = widget.identify("element", x, y)
        item = self.tree_media.identify_row(y)
        if item != "":
            val = self.tree_media.set(item, self.Column.FORMAT)
            parent = self.tree_media.parent(item)
            if not parent:
                children = self.tree_media.get_children(item)
        else:
            return
        if "image" in elem or (self.tree_media.identify_column(x) == self.Column.URL and not "Treeitem.indicator" in elem):
            if self.tree_media.set(item, self.Column.STATUS) == dl.Status.OK:
                if self.tree_media.tag_has("unchecked", item) or self.tree_media.tag_has("tristate", item):
                    self.tree_media._check_ancestor(item)
                    self.tree_media._check_descendant(item)
                else:
                    self.tree_media._uncheck_descendant(item)
                    self.tree_media._uncheck_ancestor(item)

        if self.tree_media.identify_column(x) == self.Column.FORMAT:
            if val == dl.Format.AUDIO:
                self.tree_media.set(
                    item, self.Column.FORMAT, dl.Format.VIDEO)
                if parent:
                    if all([self.tree_media.set(v, self.Column.FORMAT) == dl.Format.VIDEO for v in self.tree_media.get_children(parent)]):
                        self.tree_media.set(
                            parent, self.Column.FORMAT, dl.Format.VIDEO)
                    else:
                        self.tree_media.set(
                            parent, self.Column.FORMAT, dl.Format.BOTH)
                else:
                    for child in children:
                        self.tree_media.set(
                            child, self.Column.FORMAT, dl.Format.VIDEO)
            else:
                self.tree_media.set(
                    item, self.Column.FORMAT, dl.Format.AUDIO)
                if parent:
                    if all([self.tree_media.set(v, self.Column.FORMAT) == dl.Format.AUDIO for v in self.tree_media.get_children(parent)]):
                        self.tree_media.set(
                            parent, self.Column.FORMAT, dl.Format.AUDIO)
                    else:
                        self.tree_media.set(
                            parent, self.Column.FORMAT, dl.Format.BOTH)
                else:
                    for child in children:
                        self.tree_media.set(
                            child, self.Column.FORMAT, dl.Format.AUDIO)
            if val == dl.Format.BOTH:
                self.tree_media.set(
                    item, self.Column.FORMAT, dl.Format.VIDEO)
                for child in children:
                    self.tree_media.set(
                        child, self.Column.FORMAT, dl.Format.VIDEO)

            if all([self.tree_media.set(i, self.Column.FORMAT) == dl.Format.AUDIO for i in self.tree_media.get_children()]):
                self.var_check_audio.set(dl.Format.AUDIO)
            else:
                self.var_check_audio.set(dl.Format.VIDEO)

    def event_tree_doubleclick(self, event):
        x, y = event.x, event.y
        item = self.tree_media.identify_row(y)
        if item != "":
            parent = self.tree_media.parent(item)
            status_ok = not self.tree_media.set(
                item, self.Column.STATUS) == dl.Status.ERROR_URL
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

        if self.tree_media.identify_column(x) == self.Column.TITLE and status_ok:
            title_old = self.tree_media.set(item, self.Column.TITLE)
            title_new = askstring(
                'Edit title', 'Enter new title:', initialvalue=title_old, parent=parent)
            if title_new:
                self.tree_media.set(item, self.Column.TITLE, title_new)
                self.tree_media.set(item, self.Column.DESTINATION,
                                    self.tree_media.set(item, self.Column.DESTINATION).replace(title_old, title_new))
                if not parent:
                    if children:
                        for child in children:
                            self.tree_media.set(child, self.Column.DESTINATION,
                                                self.tree_media.set(child, self.Column.DESTINATION).replace(title_old, title_new))

        if self.tree_media.identify_column(x) == self.Column.URL and not status_ok and not self._flag_update:
            url_new = askstring('Edit URL', 'Enter new URL:',
                                initialvalue=self.tree_media.item(item, option='text'))
            if url_new:
                self.event_add(url_new)

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

    def event_dir_default(self, event=None):
        dir = fdiag.askdirectory(
            initialdir=self.var_dir_default.get(), mustexist=True)
        if dir:
            self.var_dir_default.set(dir)

    def event_dir_scroll_up(self, event):
        self.entry_dir_default.xview_scroll(-1, tk.UNITS)

    def event_dir_scroll_down(self, event):
        self.entry_dir_default.xview_scroll(1, tk.UNITS)


if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    root.mainloop()
