#请在打开时定位到与服务器jar文件相同的目录下
#否则有bug
#会导致服务器相关的文件重新生成到当前目录下

import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, ttk
import re
from colorama import init

init(autoreset=True)

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
        self.root.geometry("800x600")

        self.process = None
        self.players = []
        self.create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        frame = tk.Frame(self.root)
        frame.pack(pady=10)

        tk.Label(frame, text="最小内存:").grid(row=0, column=0)
        self.min_mem_entry = tk.Entry(frame, width=10)
        self.min_mem_entry.insert(0, "1G")
        self.min_mem_entry.grid(row=0, column=1)

        tk.Label(frame, text="最大内存:").grid(row=0, column=2)
        self.max_mem_entry = tk.Entry(frame, width=10)
        self.max_mem_entry.insert(0, "2G")
        self.max_mem_entry.grid(row=0, column=3)

        tk.Label(frame, text="Jar路径:").grid(row=1, column=0)
        self.jar_entry = tk.Entry(frame, width=40)
        self.jar_entry.grid(row=1, column=1, columnspan=3, padx=5, pady=5)

        tk.Button(frame, text="浏览", command=self.browse_jar).grid(row=1, column=4)
        tk.Button(self.root, text="启动服务器", command=self.start_server).pack(pady=5)

        status_frame = tk.Frame(self.root)
        status_frame.pack()

        self.memory_label = tk.Label(status_frame, text="内存使用：--", anchor="w", width=30)
        self.memory_label.pack(side=tk.LEFT, padx=10)

        self.tps_label = tk.Label(status_frame, text="TPS：--", anchor="w", width=20)
        self.tps_label.pack(side=tk.LEFT, padx=10)

        self.players_label = tk.Label(status_frame, text="在线玩家：--", anchor="w", width=40)
        self.players_label.pack(side=tk.LEFT, padx=10)

        self.log_box = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, height=15)
        self.log_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        for level, color in LOG_COLORS.items():
            self.log_box.tag_config(level, foreground=color)
        self.log_box.tag_config("DEFAULT", foreground="white")

        cmd_frame = tk.Frame(self.root)
        cmd_frame.pack(pady=5)

        self.command_entry = tk.Entry(cmd_frame, width=50)
        self.command_entry.pack(side=tk.LEFT, padx=5)

        tk.Button(cmd_frame, text="发送指令", command=self.send_command).pack(side=tk.LEFT)

        # 玩家列表
        self.player_listbox = tk.Listbox(self.root)
        self.player_listbox.pack(padx=10, pady=5, fill=tk.X)
        self.player_listbox.bind("<Button-3>", self.on_player_right_click)

    def browse_jar(self):
        filepath = filedialog.askopenfilename(filetypes=[("JAR files", "*.jar")])
        if filepath:
            self.jar_entry.delete(0, tk.END)
            self.jar_entry.insert(0, filepath)

    def log(self, text, level="DEFAULT"):
        self.log_box.insert(tk.END, text + "\n", level)
        self.log_box.see(tk.END)

    def colorize_log(self, line):
        if "Used memory" in line or "Memory usage" in line:
            self.memory_label.config(text=f"内存使用：{line.strip()}")
        elif "TPS" in line:
            self.tps_label.config(text=f"TPS：{line.strip()}")
        elif "There are" in line and "players online" in line:
            self.players_label.config(text=f"在线玩家：{line.strip()}")
            self.update_player_list(line)

        match = re.search(r"(INFO|WARN|ERROR|FATAL|DEBUG)", line)
        return match.group(1) if match else "DEFAULT"

    def update_player_list(self, line):
        match = re.search(r"players online: (.*)", line)
        self.player_listbox.delete(0, tk.END)
        self.players = []
        if match:
            players_str = match.group(1).strip()
            if players_str:
                players = [p.strip() for p in players_str.split(",")]
                for p in players:
                    self.players.append(p)
                    self.player_listbox.insert(tk.END, p)

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
            self.root.after(5000, self.query_server_status)
        except Exception as e:
            messagebox.showerror("启动失败", str(e))

    def query_server_status(self):
        if self.process and self.process.poll() is None:
            try:
                self.process.stdin.write(b"memory\n")
                self.process.stdin.write(b"tps\n")
                self.process.stdin.write(b"list\n")
                self.process.stdin.flush()
            except:
                pass
            self.root.after(5000, self.query_server_status)

    def on_player_right_click(self, event):
        selection = self.player_listbox.curselection()
        if not selection:
            return
        player = self.player_listbox.get(selection[0])

        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label=f"踢出 {player}", command=lambda: self.kick_player(player))
        menu.add_command(label=f"封禁 {player}", command=lambda: self.ban_player(player))
        menu.tk_popup(event.x_root, event.y_root)

    def kick_player(self, player):
        self.send_command_to_server(f"kick {player}")

    def ban_player(self, player):
        self.send_command_to_server(f"ban {player}")

    def send_command_to_server(self, cmd):
        if self.process and self.process.poll() is None:
            try:
                self.process.stdin.write((cmd + "\n").encode('utf-8'))
                self.process.stdin.flush()
                self.log(f"> {cmd}", "WARN")
            except Exception as e:
                self.log(f"发送失败: {e}", "ERROR")

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
