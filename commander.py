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

        # Load settings from external file
        self.output_height, self.output_width = self.load_settings("config.txt")
        
        # Create a frame to hold the list of commands
        self.command_frame = tk.Frame(root)
        self.command_frame.pack(pady=5)

        # Frame for buttons
        button_frame = tk.Frame(root)
        button_frame.pack(pady=5)

        # Reload button
        reload_button = tk.Button(button_frame, text="Reload Commands", command=self.reload_commands)
        reload_button.pack(side=tk.LEFT, padx=5)

        # Settings button
        settings_button = tk.Button(button_frame, text="Settings", command=self.open_settings)
        settings_button.pack(side=tk.LEFT, padx=5)

        # Create a wider frame for the output
        self.output_display = scrolledtext.ScrolledText(root, height=self.output_height, width=self.output_width, state='disabled')
        self.output_display.pack(pady=10)

        # Dictionary to store process objects and labels for each command
        self.process_info = {}

        # Dynamically create rows for each command with Start/Stop buttons, PID label, and an Entry field for extra arguments
        self.commands_list = self.load_commands("commands.txt")
        self.create_command_rows()

    def load_settings(self, filename):
        """Load settings (output height and width) from an external file."""
        try:
            with open(filename, 'r') as f:
                lines = f.readlines()
                height = int(lines[0].strip()) if len(lines) > 0 else 20
                width = int(lines[1].strip()) if len(lines) > 1 else 100
                return height, width
        except FileNotFoundError:
            return 20, 100  # Default values
        except ValueError:
            return 20, 100  # Default values on error

    def save_settings(self, filename):
        """Save settings (output height and width) to an external file."""
        with open(filename, 'w') as f:
            f.write(f"{self.output_height}\n")
            f.write(f"{self.output_width}\n")

    def load_commands(self, filename):
        """Load commands from an external file and return them as a list of tuples (label, command)."""
        commands = []
        try:
            with open(filename, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        # Split the label and command using shlex for proper handling of quotes
                        split_line = shlex.split(line)
                        if len(split_line) >= 2:
                            label = split_line[0].strip('"')  # The label without quotes
                            command = " ".join(split_line[1:])  # The rest is the command
                            commands.append((label, command))
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.")
        return commands

    def create_command_rows(self):
        """Create a row with Start/Stop buttons, PID label, and an Entry field for each command."""
        # Clear previous commands
        for widget in self.command_frame.winfo_children():
            widget.destroy()

        # Recreate process_info
        self.process_info = {}

        for label, command in self.commands_list:
            row_frame = tk.Frame(self.command_frame)
            row_frame.pack(fill=tk.X, padx=5, pady=2)

            # Command Label
            label_widget = tk.Label(row_frame, text=label, width=40, anchor='w')
            label_widget.pack(side=tk.LEFT)

            # Start Button
            start_button = tk.Button(row_frame, text="Start", command=lambda cmd=command, lbl=label: self.run_command(cmd, lbl))
            start_button.pack(side=tk.LEFT, padx=5)

            # Stop Button (initially disabled)
            stop_button = tk.Button(row_frame, text="Stop", command=lambda lbl=label: self.stop_command(lbl), state='disabled')
            stop_button.pack(side=tk.LEFT, padx=5)

            # Extra Arguments Entry Field
            extra_args_entry = tk.Entry(row_frame, width=20)
            extra_args_entry.pack(side=tk.LEFT, padx=5)

            # PID Label
            pid_label = tk.Label(row_frame, text="PID: None", width=10)
            pid_label.pack(side=tk.LEFT, padx=5)

            # Store the buttons, label, and extra args for this command
            self.process_info[label] = {
                'command': command,
                'start_button': start_button,
                'stop_button': stop_button,
                'pid_label': pid_label,
                'extra_args_entry': extra_args_entry,
                'process': None
            }

    def reload_commands(self):
        """Reload the commands from the file and rebuild the command list."""
        self.commands_list = self.load_commands("commands.txt")
        self.create_command_rows()

    def run_command(self, command, label):
        """Run the selected command in a new thread and update the PID label."""
        # Clear previous output
        self.clear_output()

        # Retrieve any extra arguments entered by the user
        extra_args = self.process_info[label]['extra_args_entry'].get().strip()
        full_command = command
        if extra_args:
            full_command += f" {extra_args}"

        # Check if the command requires sudo
        if "sudo" in full_command:
            password = simpledialog.askstring("Sudo Password", "Enter your sudo password:", show='*')
            if password:
                # Prepend the password input as an echo to the command
                full_command = f'echo {shlex.quote(password)} | sudo -S {full_command}'

        # Disable Start button and enable Stop button for this command
        self.process_info[label]['start_button'].config(state='disabled')
        self.process_info[label]['stop_button'].config(state='normal')

        # Run the command in a separate thread to prevent GUI freezing
        thread = threading.Thread(target=self.execute_command, args=(full_command, label))
        thread.start()

    def execute_command(self, command, label):
        """Execute the command and update the output in real-time, showing the PID."""
        try:
            # Start the process in a new process group
            if os.name == 'posix':
                process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, preexec_fn=os.setpgrp)
            else:
                process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            self.process_info[label]['process'] = process

            # Update the PID in the UI
            pid = process.pid
            self.process_info[label]['pid_label'].config(text=f"PID: {pid}")

            # Read the output in real-time
            while True:
                output = process.stdout.readline()
                if output == "" and process.poll() is not None:
                    break
                if output:
                    self.update_output(output)
            
            # Capture any errors
            err = process.stderr.read()
            if err:
                self.update_output(err)
        except Exception as e:
            self.update_output(f"Error: {str(e)}\n")
        finally:
            # When the process finishes, reset the buttons and clear the PID label
            self.process_info[label]['start_button'].config(state='normal')
            self.process_info[label]['stop_button'].config(state='disabled')
            self.process_info[label]['pid_label'].config(text="PID: None")
            self.process_info[label]['process'] = None

    def stop_command(self, label):
        """Stop the running command."""
        process = self.process_info[label]['process']
        if process and process.poll() is None:
            if os.name == 'posix':
                # For Unix-like systems, kill the whole process group
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            else:
                # For Windows, terminate the process
                process.terminate()

            self.update_output(f"\nCommand '{label}' terminated by user.\n")
            self.process_info[label]['stop_button'].config(state='disabled')
            self.process_info[label]['start_button'].config(state='normal')
            self.process_info[label]['pid_label'].config(text="PID: None")
            self.process_info[label]['process'] = None

    def update_output(self, message):
        """Update the text box with the output."""
        self.output_display.config(state='normal')
        self.output_display.insert(tk.END, message)
        self.output_display.yview(tk.END)  # Auto scroll to the bottom
        self.output_display.config(state='disabled')

    def clear_output(self):
        """Clear the output display."""
        self.output_display.config(state='normal')
        self.output_display.delete(1.0, tk.END)
        self.output_display.config(state='disabled')

    def open_settings(self):
        """Open a settings dialog to adjust output height and width."""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")

        # Height Label and Entry
        height_label = tk.Label(settings_window, text="Output Height:")
        height_label.grid(row=0, column=0, padx=10, pady=10)
        height_entry = tk.Entry(settings_window)
        height_entry.grid(row=0, column=1, padx=10, pady=10)
        height_entry.insert(0, str(self.output_height))  # Default value

        # Width Label and Entry
        width_label = tk.Label(settings_window, text="Output Width:")
        width_label.grid(row=1, column=0, padx=10, pady=10)
        width_entry = tk.Entry(settings_window)
        width_entry.grid(row=1, column=1, padx=10, pady=10)
        width_entry.insert(0, str(self.output_width))  # Default value

        # Apply Button
        apply_button = tk.Button(settings_window, text="Apply", command=lambda: self.apply_settings(height_entry.get(), width_entry.get()))
        apply_button.grid(row=2, columnspan=2, pady=10)

    def apply_settings(self, height, width):
        """Apply the height and width settings to the output display and save them."""
        try:
            self.output_height = int(height)
            self.output_width = int(width)
            self.output_display.config(height=self.output_height, width=self.output_width)
            self.save_settings("config.txt")  # Save settings to the config file
        except ValueError:
            self.update_output("Invalid input for height or width. Please enter valid integers.\n")

# Initialize the Tkinter window
if __name__ == "__main__":
    root = tk.Tk()
    app = CommandMonitorApp(root)
    root.mainloop()

