import os
import sys
import platform
import subprocess

def get_pid(port):
    # Get the PID using the port
    if platform.system() == "Windows":
        # For Windows
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
        lines = result.stdout.splitlines()
        for line in lines:
            if f':{port}' in line:
                parts = line.split()
                pid = parts[-1]
                return pid
    else:
        # For Unix-like systems
        result = subprocess.run(['lsof', '-i', f':{port}'], capture_output=True, text=True)
        lines = result.stdout.splitlines()
        for line in lines:
            if 'LISTEN' in line:
                parts = line.split()
                pid = parts[1]
                return pid
    return None

def kill_process(pid):
    if platform.system() == "Windows":
        # For Windows
        subprocess.run(['taskkill', '/PID', pid, '/F'])
    else:
        # For Unix-like systems
        os.kill(int(pid), 9)

def main():
    port = 5000
    pid = get_pid(port)
    if pid:
        print(f"Terminating process with PID {pid} on port {port}")
        kill_process(pid)
        print("Process terminated successfully.")
    else:
        print(f"No process found on port {port}.")

if __name__ == "__main__":
    main()
