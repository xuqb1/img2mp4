# -*- coding: utf-8 -*-
import os
import sys
import shutil
import subprocess
import datetime
import pathlib
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Scrollbar
from PIL import Image
from tkinterdnd2 import DND_FILES, TkinterDnD


def log_write(path, msg):
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S ')
    with open(path, 'a', encoding='utf-8') as f:
        f.write(ts + msg.rstrip() + '\n')

class App(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        #icon_path = pathlib.Path(__file__).with_name('app.ico')
        #if icon_path.exists():
        #     self.iconphoto(True, tk.PhotoImage(file=icon_path))
        self.title('图片转MP4工具  v9')
        self.resizable(False, False)
        self.img_list = []
        self.max_w = 0
        self.max_h = 0
        self._widget_list = []
        self._overlay = None
        self._wait_box = None
        self._minimized_with_overlay = False
        # 绑定最小化/恢复事件
        self.bind('<Unmap>', self._on_minimize)   # 最小化
        self.bind('<Map>',    self._on_restore)   # 恢复
        self.build_ui()

    # -------------------- 提示框 --------------------
    # -------------- 自制居中 messagebox 族 --------------
    def _win_msg(self, title, msg, kind='info'):
        """内部通用弹窗"""
        #parent = self._overlay if self._overlay else self
        top = tk.Toplevel(self)
        top.title(title)
        top.resizable(False, False)
        top.transient(self)
        top.grab_set()               # 模态
        # 自动激活
        top.focus_force()
        top.attributes('-topmost', True)

        # 图标
        icons = {'info': 'ℹ', 'warn': '⚠', 'error': '❌'}
        ico_lbl = ttk.Label(top, text=icons.get(kind, 'ℹ'), font=('Segoe UI', 24))
        ico_lbl.grid(row=0, column=0, padx=15, pady=15, sticky='n')
        
        # 图标用系统字体
        # ico = ttk.Label(top, text=self._icon(kind),
        #                 font=('Segoe MDL2 Assets', 32),
        #                 foreground={'info': '#0078d4', 'warn': '#ff8c00', 'error': '#d13438'}[kind])
        # ico.grid(row=0, column=0, padx=15, pady=15, sticky='n')

        # 文字
        msg_lbl = ttk.Label(top, text=msg, padding=10, justify='left')
        msg_lbl.grid(row=0, column=1, padx=(0, 20), pady=15, sticky='w')

        # 确定按钮
        btn = ttk.Button(top, text='确定', command=top.destroy)
        btn.grid(row=1, column=0, columnspan=2, pady=(0, 15))

        # 点 × 也关闭
        top.protocol('WM_DELETE_WINDOW', top.destroy)

        # 居中到主窗
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width()  // 2) - (top.winfo_reqwidth()  // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (top.winfo_reqheight() // 2)
        top.geometry(f'+{x}+{y}')

        # 等待用户关闭
        self.wait_window(top)

    def _icon(self, kind='info'):
        """返回系统对应图标字符"""
        return {'info': '\uEA39', 'warn': '\uEA38', 'error': '\uEA3A'}.get(kind, '\uEA39')
    # 三个快捷封装
    def win_info(self, title='提示', msg='操作完成'):
        self._win_msg(title, msg, 'info')

    def win_warn(self, title='警告', msg='请注意'):
        self._win_msg(title, msg, 'warn')

    def win_error(self, title='错误', msg='操作失败'):
        self._win_msg(title, msg, 'error')
    # -------------- 自制居中 askyesno --------------
    def win_askyesno(self, title='确认', msg='是否继续？'):
        self._yesno_flag = None                      # 放类实例变量里
        top = tk.Toplevel(self)
        top.title(title)
        top.resizable(False, False)
        top.grab_set()
        top.focus_force()
        top.attributes('-topmost', True)
        top.protocol('WM_DELETE_WINDOW', lambda: self._yesno_close(top, False))

        # 图标 / 文字
        # ico = ttk.Label(top, text='\uEA36', font=('Segoe MDL2 Assets', 32),foreground='#0078d4')
        # ico.grid(row=0, column=0, padx=15, pady=15)
        ttk.Label(top, text='❓', font=('Segoe UI', 24)).grid(row=0, column=0, padx=15, pady=15)
        
        ttk.Label(top, text=msg, justify='left').grid(row=0, column=1, padx=20, pady=15)

        # 按钮
        frm = ttk.Frame(top)
        frm.grid(row=1, column=0, columnspan=2, pady=10)
        ttk.Button(frm, text='是', width=8, command=lambda: self._yesno_close(top, True)).pack(side='left', padx=5)
        ttk.Button(frm, text='否', width=8, command=lambda: self._yesno_close(top, False)).pack(side='left', padx=5)

        # 居中
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (top.winfo_reqwidth() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (top.winfo_reqheight() // 2)
        top.geometry(f'+{x}+{y}')

        top.wait_window(top)          # 等窗口销毁
        return bool(self._yesno_flag)

    def _yesno_close(self, top, flag):
        self._yesno_flag = flag
        top.destroy()
    def _on_minimize(self, _evt=None):
        """最小化时如果遮罩在，就隐藏它并做标记"""
        if self._overlay and self._overlay.winfo_viewable():
            self._overlay.withdraw()
            self._minimized_with_overlay = True

    def _on_restore(self, _evt=None):
        """恢复时如果之前有遮罩，就重新显示"""
        if self._minimized_with_overlay and self._overlay:
            self._overlay.deiconify()
            self._minimized_with_overlay = False
    # -------------------- 界面 --------------------
    def build_ui(self):
        pad = {'padx': 6, 'pady': 6}
        top = ttk.Frame(self)
        top.pack(fill='both', **pad)

        # 左侧列表
        list_frm = ttk.LabelFrame(top, text='图片列表')
        list_frm.pack(side='left', fill='both', expand=True)
        # 滚动条
        vsb = ttk.Scrollbar(list_frm, orient='vertical')
        hsb = ttk.Scrollbar(list_frm, orient='horizontal')
        # self.lb = tk.Listbox(list_frm, width=70, height=10)
        self.lb = tk.Listbox(list_frm, width=70, height=10,
                             yscrollcommand=vsb.set,
                             xscrollcommand=hsb.set,
                             selectmode='extended')
        self.lb.pack(fill='both', expand=True)
        self.lb.drop_target_register(DND_FILES)
        self.lb.dnd_bind('<<Drop>>', self.on_drop)
        # 布局
        self.lb.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        # 让容器行列可扩展
        list_frm.grid_rowconfigure(0, weight=1)
        list_frm.grid_columnconfigure(0, weight=1)

        # 反向绑定
        vsb.config(command=self.lb.yview)
        hsb.config(command=self.lb.xview)


        # 右侧按钮列
        btn_frm = ttk.Frame(top)
        btn_frm.pack(side='left', fill='y', padx=(6, 0))
        btns = [('添加', self.add_imgs),
                ('上移', self.move_up),
                ('下移', self.move_down),
                ('移除', self.remove_sel),
                ('清空', self.clear_imgs)]
        for txt, cmd in btns:
            b = ttk.Button(btn_frm, text=txt, width=8, command=cmd)
            b.pack(fill='x', pady=(10 if txt == '添加' else 2, 0))
            self._widget_list.append(b)

        # 参数区
        parm = ttk.Frame(self)
        parm.pack(fill='x', **pad)

        # 第0行：停留时间 + 帧率
        ttk.Label(parm, text='每张停留(秒)：').grid(row=0, column=0, sticky='e', pady=3)
        self.var_dur = tk.StringVar(value='2.0')
        e = ttk.Entry(parm, textvariable=self.var_dur, width=10)
        e.grid(row=0, column=1, sticky='w', pady=3)
        self._widget_list.append(e)

        ttk.Label(parm, text='帧率(fps)：').grid(row=0, column=2, sticky='e', padx=(5, 0), pady=3)
        self.var_fps = tk.StringVar(value='24')
        e = ttk.Entry(parm, textvariable=self.var_fps, width=10)
        e.grid(row=0, column=3, sticky='w', pady=3)
        self._widget_list.append(e)

        # 第1行：宽度 + 高度
        ttk.Label(parm, text='视频宽度：').grid(row=1, column=0, sticky='e', pady=3)
        self.var_w = tk.StringVar()
        e = ttk.Entry(parm, textvariable=self.var_w, width=10)
        e.grid(row=1, column=1, sticky='w', pady=3)
        self._widget_list.append(e)

        ttk.Label(parm, text='高度：').grid(row=1, column=2, sticky='e', padx=(5, 0), pady=3)
        self.var_h = tk.StringVar()
        e = ttk.Entry(parm, textvariable=self.var_h, width=10)
        e.grid(row=1, column=3, sticky='w', pady=3)
        self._widget_list.append(e)

        # 第2行：输出目录
        ttk.Label(parm, text='输出目录：').grid(row=2, column=0, sticky='e', pady=3)
        self.var_out_dir = tk.StringVar(value=str(pathlib.Path.home() / 'Desktop'))
        e_out = ttk.Entry(parm, textvariable=self.var_out_dir, width=53, state='readonly')
        e_out.grid(row=2, column=1, columnspan=4, sticky='w', pady=3)
        self._widget_list.append(e_out)
        btn_out = ttk.Button(parm, text='浏览', command=self.browse_out)
        btn_out.grid(row=2, column=5, pady=3)
        self._widget_list.append(btn_out)

        # 第3行：输出文件名 + 打开文件夹 + 打开
        ttk.Label(parm, text='输出文件名：').grid(row=3, column=0, sticky='e', pady=3)
        default_name = datetime.datetime.now().strftime('%Y%m%d%H%M') + '.mp4'
        self.var_out_name = tk.StringVar(value=default_name)
        e_name = ttk.Entry(parm, textvariable=self.var_out_name, width=40)
        e_name.grid(row=3, column=1, columnspan=3, sticky='w', pady=3)
        self._widget_list.append(e_name)

        btn_openoutputdir = ttk.Button(parm, text='打开文件夹', command=self.open_out_dir)
        btn_openoutputdir.grid(row=3, column=4, padx=(2, 0), pady=3)
        btn_openoutputmp4 = ttk.Button(parm, text='打开', command=self.open_out_file)
        btn_openoutputmp4.grid(row=3, column=5, padx=(2, 0), pady=3)
        self._widget_list.append(btn_openoutputdir)
        self._widget_list.append(btn_openoutputmp4)

        # 按钮区
        frm3 = ttk.Frame(self)
        frm3.pack(**pad)
        self.btn_gen = ttk.Button(frm3, text='生成MP4', command=self.generate)
        self.btn_gen.pack(side='left', padx=6)
        self.btn_close = ttk.Button(frm3, text='关闭', command=self.destroy)
        self.btn_close.pack(side='left')
        self._widget_list.extend([self.btn_gen, self.btn_close, self.lb])

    # -------------------- 列表操作 --------------------
    def on_drop(self, event):
        files = self.tk.splitlist(event.data)
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in ('.bmp', '.jpg', '.jpeg', '.png'):
                # if f not in self.img_list:
                self.img_list.append(f)
                self.lb.insert('end', f)
        self.calc_default_resolution()

    def add_imgs(self):
        files = filedialog.askopenfilenames(
            title='添加图片（bmp/jpg/png）',
            filetypes=[('图片', '*.bmp *.jpg *.jpeg *.png'), ('全部', '*.*')])
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in ('.bmp', '.jpg', '.jpeg', '.png'):
                # if f not in self.img_list:
                self.img_list.append(f)
                self.lb.insert('end', f)
        self.calc_default_resolution()

    def clear_imgs(self):
        self.img_list.clear()
        self.lb.delete(0, 'end')
        self.max_w = self.max_h = 0
        self.var_w.set('')
        self.var_h.set('')

    # -------------------- 多选版 上移 --------------------
    def move_up(self):
        sel = list(self.lb.curselection())
        if not sel:
            # messagebox.showwarning('提示', '请先选中图片！')
            self.win_info('提示', f'请先选中图片！')
            return
        # 若最顶端已选中，则整体无法再向上
        if sel[0] == 0:
            # messagebox.showinfo('提示', '已在最顶端！')
            self.win_info('提示', '已在最顶端！')
            return
        # 整体向左“滑动”一格：先抽出来，再插到前面
        block = [self.img_list[i] for i in sel]
        # 删除原位置（逆序删，索引才不会乱）
        for i in reversed(sel):
            del self.img_list[i]
            self.lb.delete(i)
        # 插入点：原最小索引 - 1
        ins = sel[0] - 1
        for txt in block:
            self.img_list.insert(ins, txt)
            self.lb.insert(ins, txt)
            ins += 1
        # 重新选中
        new_sel = list(range(sel[0] - 1, sel[0] - 1 + len(block)))
        for i in new_sel:
            self.lb.selection_set(i)
        self.lb.see(new_sel[0])          # 滚到视野

    # -------------------- 多选版 下移 --------------------
    def move_down(self):
        sel = list(self.lb.curselection())
        if not sel:
            # messagebox.showwarning('提示', '请先选中图片！')
            self.win_info('提示', '请先选中图片！')
            return
        # 若最底端已选中，则整体无法再向下
        if sel[-1] == len(self.img_list) - 1:
            #messagebox.showinfo('提示', '已在最底端！')
            self.win_info('提示', '已在最底端！')
            return
        # 整体向右“滑动”一格：先抽出来，再插到后面
        block = [self.img_list[i] for i in sel]
        # 删除原位置（逆序删）
        for i in reversed(sel):
            del self.img_list[i]
            self.lb.delete(i)
        # 插入点：原最大索引 + 1 - (len-1)  → 紧接在整块后面
        ins = sel[0] + 1
        for txt in block:
            self.img_list.insert(ins, txt)
            self.lb.insert(ins, txt)
            ins += 1
        # 重新选中
        new_sel = list(range(sel[0] + 1, sel[0] + 1 + len(block)))
        for i in new_sel:
            self.lb.selection_set(i)
        self.lb.see(new_sel[-1])         # 滚到视野

    # -------------------- 多选版 移除 --------------------
    def remove_sel(self):
        sel = list(self.lb.curselection())
        if not sel:
            # messagebox.showwarning('提示', '请先选中要移除的图片！')
            self.win_info('提示', '请先选中要移除的图片！')
            return
        # 逆序删除，索引不漂移
        for i in reversed(sel):
            self.lb.delete(i)
            self.img_list.pop(i)


    def swap_rows(self, a, b):
        self.img_list[a], self.img_list[b] = self.img_list[b], self.img_list[a]
        txt_a, txt_b = self.lb.get(a), self.lb.get(b)
        self.lb.delete(a)
        self.lb.insert(a, txt_b)
        self.lb.delete(b)
        self.lb.insert(b, txt_a)

    def calc_default_resolution(self):
        self.max_w = self.max_h = 0
        for f in self.img_list:
            try:
                w, h = Image.open(f).size
                self.max_w = max(self.max_w, w)
                self.max_h = max(self.max_h, h)
            except Exception:
                pass
        self.var_w.set(str(self.max_w) if self.max_w else '')
        self.var_h.set(str(self.max_h) if self.max_h else '')

    def browse_out(self):
        d = filedialog.askdirectory(title='选择输出目录')
        if d:
            self.var_out_dir.set(d)

    def _get_out_path(self):
        out_dir = self.var_out_dir.get().strip() or str(pathlib.Path.home() / 'Desktop')
        out_name = self.var_out_name.get().strip() or datetime.datetime.now().strftime('%Y%m%d%H%M')
        if not out_name.lower().endswith('.mp4'):
            out_name += '.mp4'
        return os.path.join(out_dir, out_name)

    def open_out_dir(self):
        out_file = self._get_out_path()
        if not os.path.isfile(out_file):
            # messagebox.showwarning('提示', '文件尚未生成！')
            self.win_warn('提示', '文件尚未生成！')
            return
        subprocess.run(f'explorer /select,"{out_file}"')

    def open_out_file(self):
        out_file = self._get_out_path()
        if not os.path.isfile(out_file):
            # messagebox.showwarning('提示', '文件尚未生成！')
            self.win_warn('提示', '文件尚未生成！')
            return
        os.startfile(out_file)

    # -------------------- 遮罩 --------------------
    def _show_wait_layer(self):
        if self._overlay:
            return
        # 1. 确保主窗口尺寸已更新
        self.update_idletasks()
        # 2. 创建顶层
        self._overlay = tk.Toplevel(self)
        # 3. 关键：不要 transient，强制置顶
        self._overlay.attributes('-topmost', True)
        self._overlay.overrideredirect(True)
        self._overlay.configure(bg='black')
        self._overlay.attributes('-alpha', 0.6)
        # 4. 尺寸/位置与主窗完全一致
        x, y, w, h = (self.winfo_x()+5, self.winfo_y(),
                      self.winfo_width()+5, self.winfo_height()+33)
        self._overlay.geometry(f'{w}x{h}+{x}+{y}')
        # 5. 居中提示
        self._wait_box = ttk.Label(
            self._overlay, text='正在生成，请稍候...',
            background='white', foreground='black',
            font=('Segoe UI', 14), padding=20)
        self._wait_box.place(relx=0.5, rely=0.5, anchor='center')
        # 6. 再刷新一次，确保显示
        self._overlay.update()


    def _destroy_wait_layer(self):
        if self._overlay:
            self._overlay.destroy()
            self._overlay = None
            self._wait_box = None

    # def _run_ffmpeg_hidden(self, cmd):
    #     subprocess.run(cmd, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    def _run_ffmpeg_hidden(self, cmd):
        """执行 ffmpeg 并不弹黑窗，同时防止主窗无响应"""
        log_write('log.txt', 'RUN: ' + ' '.join(cmd))
        subprocess.run(cmd, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        """
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        # 每秒喂一次事件，直到进程结束
        
        while True:
            rc = proc.poll()
            if rc is not None:          # 已结束
                break
            self.update()               # 喂 UI 事件
            time.sleep(0.5)

        out, err = proc.communicate()
        if rc != 0:
            log_write('llog.txt', err.decode())
            raise RuntimeError(err.decode().strip() or 'ffmpeg 异常终止')
        """


    # -------------------- 生成逻辑 --------------------
    def generate(self):
        try:
            if not self.img_list:
                # messagebox.showwarning('提示', '图片列表为空！')
                self.win_warn('提示', '图片列表为空！')
                return
            try:
                fps = float(self.var_fps.get() or '24')
                dur = float(self.var_dur.get() or '2')
                w, h = int(self.var_w.get() or '0'), int(self.var_h.get() or '0')
            except ValueError:
                # messagebox.showerror('错误', '参数必须是数字！')
                self.win_error('错误', '参数必须是数字！')
                return
             # ----- 强制偶数化 -----
            w = w + 1 if w % 2 else w
            h = h + 1 if h % 2 else h
            # 回写到界面
            self.var_w.set(str(w))
            self.var_h.set(str(h))
            if w <= 0 or h <= 0:
                self.calc_default_resolution()
                w, h = self.max_w, self.max_h
                if w <= 0 or h <= 0:
                    raise RuntimeError('未能获取有效图片宽高，请手动填写偶数宽高！')
            out_file = self._get_out_path()
            if os.path.exists(out_file):
                # if not messagebox.askyesno('确认', f'文件已存在，是否覆盖？\n{out_file}'):
                #    return
                if not self.win_askyesno('确认', f'文件已存在，是否覆盖？\n{out_file}'):
                    return

            # 禁用控件 + 遮罩
            for w in self._widget_list:
                w.config(state='disabled')
            self._show_wait_layer()
            self.update()

            cmd, frame_dir, pic_dir = self.build_ffmpeg_cmd(dur, fps, w, h, out_file)
            self._run_ffmpeg_hidden(cmd)
            # messagebox.showinfo('完成', f'已生成：{out_file}')
            self.win_info('完成', f'已生成：{out_file}')
        except Exception as e:
            log_write('llog.txt', str(e))
            # self._destroy_wait_layer()
            # messagebox.showerror('失败', str(e))
            self.win_error('失败', str(e), self._overlay)
        finally:
            # ② 清理临时目录（无论成功失败）
            for folder in (frame_dir, pic_dir):
                if folder and os.path.isdir(folder):
                    shutil.rmtree(folder, ignore_errors=True)
                    log_write('log.txt', f'清理临时目录：{folder}')
            # 恢复控件 + 去掉遮罩
            # ① 恢复界面
            self._destroy_wait_layer()
            for w in self._widget_list:
                w.config(state='normal')
            self.nametowidget(self.var_out_dir).config(state='readonly')

    def build_ffmpeg_cmd(self, dur, fps, w, h, out_file):
        try:
            w = int(w) if str(w).isdigit() else int(self.var_w.get() or '0')
            h = int(h) if str(h).isdigit() else int(self.var_h.get() or '0')
        except ValueError:
            raise ValueError('宽高必须是数字！')
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        frame_dir = os.path.join(base_dir, f'f_{datetime.datetime.now():%Y%m%d%H%M%S}')
        os.makedirs(frame_dir, exist_ok=True)

        pic_dir = os.path.join(base_dir, 'pic')
        os.makedirs(pic_dir, exist_ok=True)
        for idx, src in enumerate(self.img_list, 1):
            ext = os.path.splitext(src)[1].lower()
            dst_png = os.path.join(pic_dir, f'{idx:06d}.png')
            if ext == '.png':
                shutil.copy2(src, dst_png)
            else:
                cmd = ['ffmpeg', '-y', '-i', src, dst_png]
                subprocess.run(cmd, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            log_write('log.txt', f'转 png：{src} -> {dst_png}')

        frame_idx = 1
        frames_per_img = max(1, int(dur * fps))
        png_files = sorted([f for f in os.listdir(pic_dir) if f.lower().endswith('.png')])
        for idx, png in enumerate(png_files, 1):
            src_png = os.path.join(pic_dir, png)
            sub_dir = os.path.join(frame_dir, f'pic_{idx:03d}')
            os.makedirs(sub_dir, exist_ok=True)

            cmd_loop = [
                'ffmpeg', '-y',
                '-loop', '1',
                '-i', src_png,
                '-vf', f'scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:({w}-iw)/2:({h}-ih)/2',
                '-frames:v', str(frames_per_img),
                '-r', str(fps),
                os.path.join(sub_dir, f'%06d.png')
            ]
            log_write('log.txt', 'ffmpeg loop: ' + ' '.join(cmd_loop))
            # subprocess.run(cmd_loop, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self._run_ffmpeg_hidden(cmd_loop)

            for k in range(frames_per_img):
                old = os.path.join(sub_dir, f'{k + 1:06d}.png')
                new = os.path.join(frame_dir, f'{frame_idx:06d}.png')
                if os.path.isfile(old):
                    shutil.move(old, new)
                else:
                    log_write('llog.txt', f'帧文件缺失：{old}')
                    raise RuntimeError(f'帧文件不存在：{old}')
                frame_idx += 1
            os.rmdir(sub_dir)

        cmd_final = [
            'ffmpeg', '-y',
            '-framerate', str(fps),
            '-i', os.path.join(frame_dir, f'%06d.png'),
            '-c:v', 'libx264',
            '-profile:v', 'baseline',
            '-level', '3.0',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',
            '-crf', '18',
            '-r', str(fps),
            out_file
        ]
        log_write('log.txt', 'ffmpeg final: ' + ' '.join(cmd_final))
        #subprocess.run(cmd_final, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        #shutil.rmtree(frame_dir, ignore_errors=True)
        #shutil.rmtree(pic_dir, ignore_errors=True)
        #log_write('log.txt', f'中间帧已清理：{frame_dir}')
        return cmd_final, frame_dir, pic_dir


if __name__ == '__main__':
    try:
        ffmpeg_exe = os.path.join(getattr(sys, '_MEIPASS', os.path.dirname(__file__)), 'ffmpeg.exe')
        if os.path.isfile(ffmpeg_exe):
            os.environ['PATH'] = os.path.dirname(ffmpeg_exe) + os.pathsep + os.environ['PATH']
        App().mainloop()
    except Exception as e:
        log_write('llog.txt', f'Unhandled: {e}')
        raise
