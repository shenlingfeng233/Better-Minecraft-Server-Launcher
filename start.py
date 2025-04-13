#请在打开时定位到与服务器jar文件相同的目录下
#否则有bug
#会导致服务器相关的文件重新生成到当前目录下

import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import re
from colorama import init

# 初始化 colorama
init(autoreset=True)

# 日志颜色映射
LOG_COLORS = {
    "INFO": "green",
    "WARN": "orange",
    "ERROR": "red",
    "FATAL": "magenta",
    "DEBUG": "cyan"
}

class MinecraftLauncherGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Minecraft 启动器")
        self.root.geometry("700x550")

        self.process = None
        self.create_widgets()

        # ✅ 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        frame = tk.Frame(self.root)
        frame.pack(pady=10)

        # 最小内存
        tk.Label(frame, text="最小内存:").grid(row=0, column=0)
        self.min_mem_entry = tk.Entry(frame, width=10)
        self.min_mem_entry.insert(0, "1G")
        self.min_mem_entry.grid(row=0, column=1)

        # 最大内存
        tk.Label(frame, text="最大内存:").grid(row=0, column=2)
        self.max_mem_entry = tk.Entry(frame, width=10)
        self.max_mem_entry.insert(0, "2G")
        self.max_mem_entry.grid(row=0, column=3)

        # JAR 路径
        tk.Label(frame, text="Jar路径:").grid(row=1, column=0)
        self.jar_entry = tk.Entry(frame, width=40)
        self.jar_entry.grid(row=1, column=1, columnspan=3, padx=5, pady=5)

        tk.Button(frame, text="浏览", command=self.browse_jar).grid(row=1, column=4)

        # 启动按钮
        tk.Button(self.root, text="启动服务器", command=self.start_server).pack(pady=5)

        # 日志输出框
        self.log_box = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, height=20)
        self.log_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        for level, color in LOG_COLORS.items():
            self.log_box.tag_config(level, foreground=color)
        self.log_box.tag_config("DEFAULT", foreground="white")

        # 指令输入区
        cmd_frame = tk.Frame(self.root)
        cmd_frame.pack(pady=5)

        self.command_entry = tk.Entry(cmd_frame, width=50)
        self.command_entry.pack(side=tk.LEFT, padx=5)

        tk.Button(cmd_frame, text="发送指令", command=self.send_command).pack(side=tk.LEFT)

    def browse_jar(self):
        filepath = filedialog.askopenfilename(filetypes=[("JAR files", "*.jar")])
        if filepath:
            self.jar_entry.delete(0, tk.END)
            self.jar_entry.insert(0, filepath)

    def log(self, text, level="DEFAULT"):
        self.log_box.insert(tk.END, text + "\n", level)
        self.log_box.see(tk.END)

    def colorize_log(self, line):
        match = re.search(r"(INFO|WARN|ERROR|FATAL|DEBUG)", line)
        if match:
            return match.group(1)
        return "DEFAULT"

    def read_output(self):
        for line in iter(self.process.stdout.readline, b''):
            decoded_line = line.decode('utf-8', errors='ignore').strip()
            level = self.colorize_log(decoded_line)
            self.log(decoded_line, level)

    def send_command(self):
        command = self.command_entry.get().strip()
        if command and self.process and self.process.poll() is None:
            try:
                self.process.stdin.write((command + "\n").encode('utf-8'))
                self.process.stdin.flush()
                self.log(f"> {command}", "DEBUG")
                self.command_entry.delete(0, tk.END)
            except Exception as e:
                messagebox.showerror("发送失败", str(e))
        else:
            messagebox.showwarning("警告", "服务器未启动或已关闭。")

    def start_server(self):
        jar = self.jar_entry.get().strip()
        xms = self.min_mem_entry.get().strip()
        xmx = self.max_mem_entry.get().strip()

        if not jar:
            messagebox.showerror("错误", "请指定 jar 文件路径")
            return

        # ✅ 清空日志框
        self.log_box.delete("1.0", tk.END)

        cmd = ["java", f"-Xms{xms}", f"-Xmx{xmx}", "-jar", jar, "nogui"]

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                bufsize=1
            )
            threading.Thread(target=self.read_output, daemon=True).start()
            self.log("服务器启动中...", "INFO")
        except Exception as e:
            messagebox.showerror("启动失败", str(e))

    def on_closing(self):
        if self.process and self.process.poll() is None:
            try:
                self.log("正在关闭服务器...", "WARN")
                self.process.stdin.write(b"stop\n")
                self.process.stdin.flush()
                self.process.wait(timeout=10)
            except Exception as e:
                self.log(f"正常关闭失败，尝试强制终止: {e}", "ERROR")
                self.process.kill()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = MinecraftLauncherGUI(root)
    root.mainloop()
