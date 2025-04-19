#请在打开时定位到与服务器jar文件相同的目录下
#否则有bug
#会导致服务器相关的文件重新生成到当前目录下

import subprocess
import threading
import re
from remi import start, App
from remi.gui import *

LOG_COLORS = {
    "INFO": "green",
    "WARN": "orange",
    "ERROR": "red",
    "FATAL": "magenta",
    "DEBUG": "cyan",
    "DEFAULT": "black"
}

class MinecraftLauncherRemi(App):
    def __init__(self, *args):
        super(MinecraftLauncherRemi, self).__init__(*args)
        self.process = None
        self.players = []
        self.available_commands = set()
        self.check_command_listening = False
        self.output_thread = None
        self.running = True
        self.log_entries = []

    def main(self):
        container = VBox(style={'width': '100%', 'padding': '10px'})

        self.min_mem = TextInput(single_line=True, style={'margin': '5px'})
        self.min_mem.set_text('1G')
        self.max_mem = TextInput(single_line=True, style={'margin': '5px'})
        self.max_mem.set_text('2G')
        self.jar_path = TextInput(single_line=True, style={'margin': '5px'})

        browse_button = Button('浏览', style={'margin': '5px'})
        browse_button.onclick.connect(self.browse_jar)
        start_button = Button('启动服务器', style={'margin': '5px'})
        start_button.onclick.connect(self.start_server)

        self.mem_label = Label('内存使用：--')
        self.tps_label = Label('TPS：--')
        self.players_label = Label('在线玩家：--')

        self.cmd_input = TextInput(single_line=True, style={'margin': '5px'})
        send_button = Button('发送指令', style={'margin': '5px'})
        send_button.onclick.connect(self.send_command)

        self.log_filter = DropDown.new_from_list(["ALL"] + list(LOG_COLORS.keys()), style={'margin': '5px'})
        self.log_filter.select_by_value("ALL")
        self.log_filter.onchange.connect(self.filter_logs)

        self.log_search = TextInput(single_line=True, style={'margin': '5px'})
        self.log_search.set_text("")
        self.log_search.onchange.connect(self.filter_logs)

        self.player_list = ListView()
        self.log_box = VBox(style={'margin': '5px', 'height': '300px', 'overflow': 'auto'})

        container.append(self.min_mem)
        container.append(self.max_mem)
        container.append(self.jar_path)
        container.append(browse_button)
        container.append(start_button)
        container.append(self.mem_label)
        container.append(self.tps_label)
        container.append(self.players_label)
        container.append(self.cmd_input)
        container.append(send_button)
        container.append(self.log_filter)
        container.append(self.log_search)
        container.append(self.player_list)
        container.append(self.log_box)

        return container

    def browse_jar(self, widget):
        self.log("请手动输入 JAR 文件路径，目前不支持文件对话框", "WARN")

    def log(self, text, level="DEFAULT"):
        color = LOG_COLORS.get(level, "black")
        entry = (level, text)
        self.log_entries.append(entry)
        if self.log_filter.get_value() in ["ALL", level] and self.log_search.get_text().lower() in text.lower():
            label = Label(f"[{level}] {text}", style={"color": color, "font-family": "monospace", "font-size": "12px"})
            self.log_box.append(label)

    def filter_logs(self, widget=None):
        selected_level = self.log_filter.get_value()
        search_term = self.log_search.get_text().lower()
        self.log_box.empty()
        for level, text in self.log_entries:
            if (selected_level == "ALL" or level == selected_level) and search_term in text.lower():
                color = LOG_COLORS.get(level, "black")
                label = Label(f"[{level}] {text}", style={"color": color, "font-family": "monospace", "font-size": "12px"})
                self.log_box.append(label)

    def colorize_log(self, line):
        if "Used memory" in line or "Memory usage" in line:
            self.mem_label.set_text(f"内存使用：{line.strip()}")
        elif "TPS" in line:
            self.tps_label.set_text(f"TPS：{line.strip()}")
        elif "There are" in line and "players online" in line:
            self.players_label.set_text(f"在线玩家：{line.strip()}")
            self.update_player_list(line)
        match = re.search(r"(INFO|WARN|ERROR|FATAL|DEBUG)", line)
        return match.group(1) if match else "DEFAULT"

    def read_output(self):
        try:
            while self.running and self.process and self.process.poll() is None:
                line = self.process.stdout.readline()
                if not line:
                    break
                decoded_line = line.decode('utf-8', errors='ignore').strip()
                if decoded_line:
                    level = self.colorize_log(decoded_line)
                    self.log(decoded_line, level)
        except Exception as e:
            self.log(f"读取输出时发生错误: {e}", "ERROR")
        finally:
            if self.process:
                try:
                    self.process.stdout.close()
                except:
                    pass

    def send_command(self, widget):
        if not self.process or self.process.poll() is not None:
            self.log("服务器未运行", "ERROR")
            return
        command = self.cmd_input.get_text().strip()
        if command:
            try:
                self.process.stdin.write((command + "\n").encode('utf-8'))
                self.process.stdin.flush()
                self.log(f"> {command}", "DEBUG")
                self.cmd_input.set_text("")
            except Exception as e:
                self.log(str(e), "ERROR")

    def start_server(self, widget):
        if self.process and self.process.poll() is None:
            self.log("服务器已经在运行", "WARN")
            return

        jar = self.jar_path.get_text().strip()
        xms = self.min_mem.get_text().strip()
        xmx = self.max_mem.get_text().strip()
        if not jar:
            self.log("未指定 JAR 文件", "ERROR")
            return

        self.log_entries.clear()
        self.log_box.empty()
        self.running = True

        cmd = ["java", f"-Xms{xms}", f"-Xmx{xmx}", "-jar", jar, "nogui"]

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                bufsize=1
            )
            self.output_thread = threading.Thread(target=self.read_output, daemon=True)
            self.output_thread.start()
            self.log("服务器启动中...", "INFO")
            self.check_command_listening = True
            self.process.stdin.write(b"help\n")
            self.process.stdin.flush()
        except Exception as e:
            self.log(str(e), "ERROR")

    def update_player_list(self, line):
        pass

    def on_stop(self):
        self.running = False
        if self.process and self.process.poll() is None:
            try:
                self.log("正在关闭服务器...", "WARN")
                self.process.stdin.write(b"stop\n")
                self.process.stdin.flush()
                self.process.wait(timeout=10)
            except Exception as e:
                self.log(f"正常关闭失败: {e}", "ERROR")
                self.process.kill()
            finally:
                try:
                    self.process.stdin.close()
                    self.process.stdout.close()
                except:
                    pass

if __name__ == "__main__":
    start(MinecraftLauncherRemi, address='0.0.0.0', port=8081, start_browser=True)

