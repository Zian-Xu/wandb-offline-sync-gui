import sys
import os

# 处理 PyInstaller 打包后的 vendor 路径问题
if hasattr(sys, "_MEIPASS"):
    sys.path.append(os.path.join(sys._MEIPASS, "wandb", "vendor"))


def cmd_login(key: str):
    import wandb
    try:
        wandb.login(key=key.strip(), relogin=True)
        print("登录成功")
        return 0
    except wandb.errors.UsageError as e:
        print(f"[UsageError] {e}")
        return 2
    except Exception as e:
        print(f"[Exception] {e}")
        return 3


def cmd_status():
    from wandb import Api
    try:
        api = Api()
        key = api.api_key
        if key:
            print(f"key: {key[:8]}******")
            return 0
        else:
            print("未登录")
            return 1
    except Exception as e:
        print(f"无法获取登录状态: {e}")
        return 1


def cmd_sync(folder: str):
    try:
        import wandb.cli.cli
        sys.argv = ["wandb", "sync", folder]
        wandb.cli.cli.cli()
        print("同步完成")
        return 0
    except Exception as e:
        print(f"同步失败: {e}")
        return 1


def main():
    if len(sys.argv) < 2:
        print("使用方法: wandb_sync.exe <login|status|sync> [参数]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "login":
        if len(sys.argv) < 3:
            print("用法: wandb_sync.exe login <api_key>")
            sys.exit(1)
        sys.exit(cmd_login(sys.argv[2]))

    elif cmd == "status":
        sys.exit(cmd_status())

    elif cmd == "sync":
        if len(sys.argv) < 3:
            print("用法: wandb_sync.exe sync <log_folder>")
            sys.exit(1)
        sys.exit(cmd_sync(sys.argv[2]))

    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
