import sys
import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import subprocess
import threading


CREATE_NO_WINDOW = 0x08000000  # Windows 隐藏子进程控制台窗口标志


class WandbUploaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Wandb 日志上传工具")

        # 初始化参数
        self.center_frame = None
        self.set_key_button = None
        self.upload_button = None
        self.progress_label = None
        self.current_progress_message = None
        self.progress_win = None
        self.progress_bar = None
        self.selected_folder = ""
        self.upload_thread = None
        self.operation_cancelled = False
        self.current_process = None
        self.current_status = None
        self.wandb_sync_exe = None
        self.progress_countdown = None
        self.countdown_after_id = None

        # 初始界面只显示提示
        self.status_label = tk.Label(root, text="正在检测 Wandb 登录状态...")
        self.status_label.pack(pady=40)
        self.center_window(300, 100)
        self.root.update()  # 强制刷新界面以显示提示

        # 启动后台线程检查状态
        threading.Thread(target=self.init_check, daemon=True).start()

    def init_check(self):
        self.check_sync_exe()
        self.check_status()
        self.root.after(0, self.show_main_ui)  # 状态检查完成后切换为完整界面

    def show_main_ui(self):
        self.status_label.destroy()  # 移除提示

        # 主按钮布局
        self.center_frame = tk.Frame(self.root)
        self.center_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self.set_key_button = tk.Button(self.center_frame, text="设置 Wandb Key", command=self.set_wandb_key, height=1)
        self.set_key_button.grid(row=0, column=0, padx=10, pady=5)
        self.upload_button = tk.Button(self.center_frame, text="上传日志", command=self.choose_and_upload, height=1)
        self.upload_button.grid(row=0, column=1, padx=10, pady=5)

    def check_sync_exe(self):
        if getattr(sys, 'frozen', False):  # 打包环境 wandb_sync.exe 应与主程序位于同一目录下
            self.wandb_sync_exe = os.path.join(os.path.dirname(sys.executable), "wandb_sync.exe")
        else:  # 开发环境
            self.wandb_sync_exe = 'wandb_sync.py'
        if not os.path.exists(self.wandb_sync_exe):
            messagebox.showerror("组件缺失", f"未找到: {self.wandb_sync_exe}")
            self.root.destroy()  # 关闭主窗口
            sys.exit(1)  # 退出程序

    def check_status(self):
        try:
            proc = subprocess.Popen(
                self.build_command("status"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                creationflags=CREATE_NO_WINDOW,
            )
            stdout, stderr = proc.communicate()

            if proc.returncode == 0:  # 已登录
                key_part = stdout.split("key:")[-1]
                self.current_status = f"已登录，Key: {key_part}"
            elif proc.returncode == 1:  # 未登录或异常
                self.current_status = "未登录"
            else:  # 其他错误
                self.current_status = f"未定义: {stderr or stdout}"

        except Exception as e:
            self.current_status = f"程序错误: {str(e)}"

    def center_window(self, width=300, height=100):
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def choose_and_upload(self):
        folder = filedialog.askdirectory(title="选择 Wandb 日志文件夹")
        if folder:
            self.selected_folder = folder
            self.start_upload()

    def start_upload(self):
        self.operation_cancelled = False
        self.disable_buttons()
        self.show_progress("正在上传 Wandb 日志...")

        def _upload():
            try:
                if not self.current_status.startswith("已登录"):
                    self.close_progress()
                    messagebox.showerror("上传失败", "请先登录 Wandb 后再上传日志")
                    return

                self.current_process = subprocess.Popen(
                    self.build_command("sync", self.selected_folder),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    creationflags=CREATE_NO_WINDOW
                )
                stdout, stderr = self.current_process.communicate()
                self.close_progress()

                if self.operation_cancelled:
                    return

                if self.current_process.returncode == 0:
                    if "skipping directory" in stdout.lower():
                        messagebox.showerror("上传失败", "未找到有效的 Wandb 日志文件夹")
                    else:
                        messagebox.showinfo("上传成功", stdout)
                else:
                    messagebox.showerror("上传失败", stderr or stdout or "未知错误")

            except Exception as e:
                self.close_progress()
                if not self.operation_cancelled:
                    messagebox.showerror("程序错误", f"{str(e)}")
            finally:
                self.current_process = None
                self.enable_buttons()

        self.upload_thread = threading.Thread(target=_upload)
        self.upload_thread.start()

    def set_wandb_key(self):
        prompt_text = f"{self.current_status}\n\n请输入新的 Wandb API Key（留空或取消则跳过）:"
        key = simpledialog.askstring("设置 Wandb Key", prompt_text)

        if key is None or key.strip() == "":
            return

        self.operation_cancelled = False
        self.disable_buttons()
        self.show_progress("正在登录 Wandb...")

        def _login():
            try:
                self.current_process = subprocess.Popen(
                    self.build_command("login", key.strip()),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    creationflags=CREATE_NO_WINDOW
                )
                stdout, stderr = self.current_process.communicate()
                self.check_status()
                self.close_progress()

                # 响应取消按钮逻辑
                if self.operation_cancelled:
                    return

                # 反馈登录状态
                if self.current_process.returncode == 0:
                    self.current_status = f"已登录，Key: {key[:8]}******"
                    messagebox.showinfo("登录成功", "登录成功")
                elif self.current_process.returncode == 2:
                    self.current_status = "未登录"
                    messagebox.showerror("登录失败", stdout or "Wandb Key 无效")
                elif self.current_process.returncode == 3:
                    self.current_status = "未登录"
                    messagebox.showerror("服务错误", stdout or "wandb_sync.exe 错误")
                else:
                    self.current_status = "未登录"
                    messagebox.showerror("未定义", f"错误码 {self.current_process.returncode}: "
                                                     f"{stdout or stderr}")

            except Exception as e:
                self.close_progress()
                if not self.operation_cancelled:
                    messagebox.showerror("程序错误", f"{str(e)}")

            finally:
                self.current_process = None
                self.enable_buttons()

        threading.Thread(target=_login).start()

    def update_countdown(self):
        if self.progress_countdown <= 0:
            self.cancel_operation()
            self.close_progress()
            if hasattr(self, 'current_progress_message'):
                if "上传" in self.current_progress_message:
                    messagebox.showerror("超时", "上传超时")
                elif "登录" in self.current_progress_message:
                    messagebox.showerror("超时", "登录超时")
            return
        # 更新标签文本，显示倒计时数字
        self.progress_label.config(text=f"{self.current_progress_message}({self.progress_countdown})")
        self.progress_countdown -= 1
        self.countdown_after_id = self.progress_win.after(1000, self.update_countdown)  # noqa

    def show_progress(self, message):
        self.current_progress_message = message
        self.progress_win = tk.Toplevel(self.root)
        self.progress_win.title("进度")
        self.progress_win.geometry("300x100")
        self.progress_win.transient(self.root)
        self.progress_win.grab_set()

        self.progress_win.protocol("WM_DELETE_WINDOW", self.cancel_operation)

        self.progress_win.update_idletasks()
        w = self.progress_win.winfo_width()
        h = self.progress_win.winfo_height()
        sw = self.progress_win.winfo_screenwidth()
        sh = self.progress_win.winfo_screenheight()
        self.progress_win.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

        # 这里是带倒计时的标签
        self.progress_label = tk.Label(self.progress_win, text=f"{message}(60)")
        self.progress_label.pack(pady=(10, 5))

        row = tk.Frame(self.progress_win)
        row.pack(padx=20, pady=5, fill=tk.X)

        self.progress_bar = ttk.Progressbar(row, mode="indeterminate")
        self.progress_bar.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 10))
        self.progress_bar.start(10)

        cancel_button = tk.Button(row, text="取消", command=self.cancel_operation, height=1, width=8)
        cancel_button.pack(side=tk.RIGHT)

        self.progress_countdown = 100
        self.update_countdown()

    def close_progress(self):
        if hasattr(self, 'progress_win') and self.progress_win.winfo_exists():
            if self.countdown_after_id is not None:
                self.progress_win.after_cancel(self.countdown_after_id)
                self.countdown_after_id = None
            self.progress_bar.stop()
            self.progress_win.grab_release()
            self.progress_win.destroy()

    def cancel_operation(self):
        self.operation_cancelled = True
        if self.current_process and self.current_process.poll() is None:
            try:
                self.current_process.terminate()
            except Exception as e:
                print(f"终止失败: {e}")
        self.close_progress()
        self.enable_buttons()

    def disable_buttons(self):
        self.upload_button.config(state=tk.DISABLED)
        self.set_key_button.config(state=tk.DISABLED)

    def enable_buttons(self):
        self.upload_button.config(state=tk.NORMAL)
        self.set_key_button.config(state=tk.NORMAL)

    def build_command(self, *args):
        """根据 wandb_sync_exe 的类型返回完整命令行列表"""
        if self.wandb_sync_exe.endswith(".py"):
            return [sys.executable, self.wandb_sync_exe, *args]
        else:
            return [self.wandb_sync_exe, *args]

if __name__ == "__main__":
    root_ = tk.Tk()
    app = WandbUploaderApp(root_)
    root_.mainloop()