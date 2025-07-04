# wandb-offline-sync-gui
A simple and intuitive GUI app for syncing offline Wandb logs. No need to write code or remember CLI commands — just select a folder and click upload.

## 说明

此代码生成 exe 文件，使用图形化界面便于上传 wandb 日志。代码能力有限，有问题欢迎交流。

## 打包问题记录（新）

>  由于旧的打包之后还是存在 bug，以此新记录为准。

由于 `wandb.exe` 不是一个可以独立运行的程序，而是需要 python 解释器相关环境，因此想要在客户机上运行这一程序是比较麻烦的。为了能够做到开箱即用，需要将 `wandb.exe` 换成一个真正可执行的 exe 封装。

于是将借助 wandb.exe 运行的命令修改为借助 CLI 运行：

```python
import wandb.cli.cli
sys.argv = ["wandb", "sync", folder]
wandb.cli.cli.cli()
```

随后我还将所有涉及到 wandb 的操作都写到一个 python 文件 `wandb_sync.py` 下，从而让封装两个 exe 时防止主程序文件过大。目前主程序 `wandb_gui.py` 只负责界面和逻辑，wandb 的功能全部移出。

目前的打包命令：

```bash
pyinstaller wandb_sync.py --onefile --noconsole --add-data "D:/conda/envs/exe/Lib/site-packages/wandb/vendor;wandb/vendor"
```

```bash
pyinstaller wandb_gui.py --onefile --noconsole
```

打包好的两个 exe 文件必须放在一个目录下运行。

## 打包问题记录（旧）

`wandb` 同步日志只能使用命令行命令：

```bash
wandb sync <folder_path>
```

这就需要在软件中使用：

```python
self.current_process = subprocess.Popen(
    [wandb_exe, "sync", self.selected_folder],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    creationflags=CREATE_NO_WINDOW
)
```

其中 `creationflags=CREATE_NO_WINDOW` 是隐藏 wandb.exe 命令行窗口的标识符，`Windows` 上为 `CREATE_NO_WINDOW = 0x08000000`。 

这时，由于使用到了 `wandb.exe`，因此需要将该 exe 文件一起打包。同时，`wandb.exe` 本身也依赖 Python 环境中的 `Lib\site-packages\wandb`，因此需要一起打包，尽管这样会造成 exe 文件比较大：

```bash
pyinstaller wandb_gui.py --onefile --noconsole --add-binary "D:\conda\envs\exe\Scripts\wandb.exe;." --add-data "D:\conda\envs\exe\Lib\site-packages\wandb;wandb"
```

上述步骤可以将依赖项打包到 exe 文件中，我们还需要在 python 代码中进行修改才能找到他们：

```python
# 这些代码放在最开头，为了能够找到 wandb
import sys
import os
if hasattr(sys, "_MEIPASS"):
    sys.path.append(os.path.join(sys._MEIPASS, "wandb"))
```

```python
# 该函数是从当前程序环境中自动查找 exe 文件的路径，为了能够找到 wandb.exe
@staticmethod
def _get_executable_path(name):
    """
    在 Windows 上安全获取可执行文件路径，支持 PyInstaller --onefile 模式。
    """
    if not name.lower().endswith('.exe'):
        name += '.exe'

    if getattr(sys, 'frozen', False):
        # 先尝试从 sys._MEIPASS 目录找，那里是 --onefile 解压目录
        base_path = getattr(sys, '_MEIPASS', None)
        if base_path:
            executable_path = os.path.join(base_path, name)
            if os.path.exists(executable_path):
                return executable_path

        # 备选方案：从 sys.executable 同目录找
        base_path = os.path.dirname(sys.executable)
        executable_path = os.path.join(base_path, name)
        if os.path.exists(executable_path):
            return executable_path

        # 开发环境，从系统 PATH 查找
    return shutil.which(name)


# 函数使用案例
wandb_exe = self._get_executable_path("wandb.exe")
if not wandb_exe:
    raise FileNotFoundError("未找到 wandb.exe 可执行文件")
```

