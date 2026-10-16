import psutil

for process in psutil.process_iter(["pid", "ppid", "name", "cmdline"]):
    if (process.info["name"] or "").lower() in {"winword.exe", "cscript.exe"}:
        print(process.info)
