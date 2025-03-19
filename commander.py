import tkinter as tk
from tkinter import simpledialog, scrolledtext
import subprocess
import threading
import os
import shlex
import signal

class CommandMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Commander (Runner and Monitor)")
        self.root.minsize(800, 600)

        self.output_height, self.output_width = self.load_settings("config.txt")
        
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.command_frame = tk.Frame(self.main_frame)
        self.command_frame.pack(fill=tk.X, pady=5)

        self.button_frame = tk.Frame(self.main_frame)
        self.button_frame.pack(fill=tk.X, pady=5)

        reload_button = tk.Button(self.button_frame, text="Reload Commands", command=self.reload_commands)
        reload_button.pack(side=tk.LEFT, padx=5)

        settings_button = tk.Button(self.button_frame, text="Settings", command=self.open_settings)
        settings_button.pack(side=tk.LEFT, padx=5)

        self.output_display = scrolledtext.ScrolledText(self.main_frame, height=self.output_height, width=self.output_width, state='disabled')
        self.output_display.pack(fill=tk.BOTH, expand=True, pady=10)

        self.process_info = {}
        self.commands_list = self.load_commands("commands.txt")
        self.create_command_rows()
        self.create_add_command_interface()

        self.root.update_idletasks()

    def load_settings(self, filename):
        try:
            with open(filename, 'r') as f:
                lines = f.readlines()
                height = int(lines[0].strip()) if len(lines) > 0 else 20
                width = int(lines[1].strip()) if len(lines) > 1 else 100
                return height, width
        except FileNotFoundError:
            return 20, 100
        except ValueError:
            return 20, 100

    def save_settings(self, filename):
        with open(filename, 'w') as f:
            f.write(f"{self.output_height}\n")
            f.write(f"{self.output_width}\n")

    def load_commands(self, filename):
        commands = []
        try:
            with open(filename, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        split_line = shlex.split(line)
                        if len(split_line) >= 2:
                            label = split_line[0].strip('"')
                            command = " ".join(split_line[1:])
                            commands.append((label, command))
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.")
        return commands

    def save_commands(self):
        """Save the current commands_list back to commands.txt."""
        try:
            with open("commands.txt", 'w') as f:
                for label, command in self.commands_list:
                    if " " in label:
                        label = f'"{label}"'
                    f.write(f"{label} {command}\n")
        except Exception as e:
            self.update_output(f"Error saving commands: {str(e)}\n")

    def create_command_rows(self):
        running_processes = {
            label: info['process'] 
            for label, info in self.process_info.items() 
            if info['process'] is not None and info['process'].poll() is None
        }

        for widget in self.command_frame.winfo_children():
            widget.destroy()

        self.process_info = {}

        for label, command in self.commands_list:
            row_frame = tk.Frame(self.command_frame)
            row_frame.pack(fill=tk.X, padx=5, pady=2)

            label_widget = tk.Label(row_frame, text=label, width=25, anchor='w')
            label_widget.pack(side=tk.LEFT)

            command_entry = tk.Entry(row_frame, width=80)
            command_entry.insert(0, command)
            command_entry.pack(side=tk.LEFT, padx=5)

            start_button = tk.Button(row_frame, text="Start", 
                                   command=lambda cmd=command, lbl=label: self.run_command(cmd, lbl))
            start_button.pack(side=tk.LEFT, padx=5)

            stop_button = tk.Button(row_frame, text="Stop", 
                                  command=lambda lbl=label: self.stop_command(lbl), 
                                  state='disabled')
            stop_button.pack(side=tk.LEFT, padx=5)

            delete_button = tk.Button(row_frame, text="Delete", 
                                    command=lambda lbl=label: self.delete_command(lbl))
            delete_button.pack(side=tk.LEFT, padx=5)

            # Save Button
            save_button = tk.Button(row_frame, text="Save", 
                                  command=lambda lbl=label, entry=command_entry: self.save_command(lbl, entry))
            save_button.pack(side=tk.LEFT, padx=5)

            pid_label = tk.Label(row_frame, text="PID: None", width=10)
            pid_label.pack(side=tk.LEFT, padx=5)

            self.process_info[label] = {
                'command': command,
                'start_button': start_button,
                'stop_button': stop_button,
                'pid_label': pid_label,
                'command_entry': command_entry,
                'process': running_processes.get(label)
            }

            if label in running_processes:
                start_button.config(state='disabled')
                stop_button.config(state='normal')
                pid = running_processes[label].pid
                pid_label.config(text=f"PID: {pid}")

    def create_add_command_interface(self):
        self.add_command_frame = tk.Frame(self.main_frame)
        self.add_command_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)

        tk.Label(self.add_command_frame, text="Name:").pack(side=tk.LEFT, padx=5)
        self.new_name_entry = tk.Entry(self.add_command_frame, width=25)
        self.new_name_entry.pack(side=tk.LEFT, padx=5)

        tk.Label(self.add_command_frame, text="Command:").pack(side=tk.LEFT, padx=5)
        self.new_command_entry = tk.Entry(self.add_command_frame, width=80)
        self.new_command_entry.pack(side=tk.LEFT, padx=5)

        create_button = tk.Button(self.add_command_frame, text="Create", command=self.add_new_command)
        create_button.pack(side=tk.LEFT, padx=5)

    def save_command(self, label, command_entry):
        """Save the edited command for a specific label."""
        new_command = command_entry.get().strip()
        if new_command:
            # Update the command in commands_list
            self.commands_list = [(lbl, new_command if lbl == label else cmd) 
                                for lbl, cmd in self.commands_list]
            # Update the stored command in process_info
            self.process_info[label]['command'] = new_command
            # Save to file
            self.save_commands()
            self.update_output(f"Saved command: {label} {new_command}\n")
        else:
            self.update_output(f"Error: Command cannot be empty for {label}\n")

    def delete_command(self, label):
        if label in self.process_info and self.process_info[label]['process'] is not None:
            self.stop_command(label)

        self.commands_list = [(lbl, cmd) for lbl, cmd in self.commands_list if lbl != label]
        self.save_commands()
        self.create_command_rows()
        self.update_output(f"Deleted command: {label}\n")

    def reload_commands(self):
        self.commands_list = self.load_commands("commands.txt")
        self.create_command_rows()

    def add_new_command(self):
        name = self.new_name_entry.get().strip()
        command = self.new_command_entry.get().strip()
        
        if name and command:
            if " " in name:
                name = f'"{name}"'
            
            try:
                with open("commands.txt", 'a') as f:
                    f.write(f"{name} {command}\n")
                
                self.new_name_entry.delete(0, tk.END)
                self.new_command_entry.delete(0, tk.END)
                
                self.reload_commands()
                
                self.update_output(f"Added new command: {name} {command}\n")
            except Exception as e:
                self.update_output(f"Error adding command: {str(e)}\n")
        else:
            self.update_output("Error: Both name and command must be provided.\n")

    def run_command(self, command, label):
        self.clear_output()
        full_command = self.process_info[label]['command_entry'].get().strip()

        if "sudo" in full_command:
            password = simpledialog.askstring("Sudo Password", "Enter your sudo password:", show='*')
            if password:
                full_command = f'echo {shlex.quote(password)} | sudo -S {full_command}'

        self.process_info[label]['start_button'].config(state='disabled')
        self.process_info[label]['stop_button'].config(state='normal')

        thread = threading.Thread(target=self.execute_command, args=(full_command, label))
        thread.start()

    def execute_command(self, command, label):
        try:
            if os.name == 'posix':
                process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, 
                                        stderr=subprocess.PIPE, text=True, preexec_fn=os.setpgrp)
            else:
                process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, 
                                        stderr=subprocess.PIPE, text=True)

            self.process_info[label]['process'] = process
            pid = process.pid
            self.process_info[label]['pid_label'].config(text=f"PID: {pid}")

            while True:
                output = process.stdout.readline()
                if output == "" and process.poll() is not None:
                    break
                if output:
                    self.update_output(output)
            
            err = process.stderr.read()
            if err:
                self.update_output(err)
        except Exception as e:
            self.update_output(f"Error: {str(e)}\n")
        finally:
            self.process_info[label]['start_button'].config(state='normal')
            self.process_info[label]['stop_button'].config(state='disabled')
            self.process_info[label]['pid_label'].config(text="PID: None")
            self.process_info[label]['process'] = None

    def stop_command(self, label):
        process = self.process_info[label]['process']
        if process and process.poll() is None:
            if os.name == 'posix':
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            else:
                process.terminate()

            self.update_output(f"\nCommand '{label}' terminated by user.\n")
            self.process_info[label]['stop_button'].config(state='disabled')
            self.process_info[label]['start_button'].config(state='normal')
            self.process_info[label]['pid_label'].config(text="PID: None")
            self.process_info[label]['process'] = None

    def update_output(self, message):
        self.output_display.config(state='normal')
        self.output_display.insert(tk.END, message)
        self.output_display.yview(tk.END)
        self.output_display.config(state='disabled')

    def clear_output(self):
        self.output_display.config(state='normal')
        self.output_display.delete(1.0, tk.END)
        self.output_display.config(state='disabled')

    def open_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")

        height_label = tk.Label(settings_window, text="Output Height:")
        height_label.grid(row=0, column=0, padx=10, pady=10)
        height_entry = tk.Entry(settings_window)
        height_entry.grid(row=0, column=1, padx=10, pady=10)
        height_entry.insert(0, str(self.output_height))

        width_label = tk.Label(settings_window, text="Output Width:")
        width_label.grid(row=1, column=0, padx=10, pady=10)
        width_entry = tk.Entry(settings_window)
        width_entry.grid(row=1, column=1, padx=10, pady=10)
        width_entry.insert(0, str(self.output_width))

        apply_button = tk.Button(settings_window, text="Apply", 
                               command=lambda: self.apply_settings(height_entry.get(), width_entry.get()))
        apply_button.grid(row=2, columnspan=2, pady=10)

    def apply_settings(self, height, width):
        try:
            self.output_height = int(height)
            self.output_width = int(width)
            self.output_display.config(height=self.output_height, width=self.output_width)
            self.save_settings("config.txt")
        except ValueError:
            self.update_output("Invalid input for height or width. Please enter valid integers.\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = CommandMonitorApp(root)
    root.mainloop()
