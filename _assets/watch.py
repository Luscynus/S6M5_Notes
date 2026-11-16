import os, glob, time, subprocess

def get_mtimes():
    mtimes = {}
    for folder in ["1_Algebra", "2_Geometry", "3_Stochastics", "_assets"]:
        for root, _, files in os.walk(folder):
            for f in files:
                if f.endswith((".qmd", ".css", ".html")) and not f.startswith("ch"):
                    path = os.path.join(root, f)
                    mtimes[path] = os.path.getmtime(path)
    return mtimes

proc = subprocess.Popen(["quarto", "preview"])
last = get_mtimes()

try:
    while proc.poll() is None:
        time.sleep(0.8)
        curr = get_mtimes()
        if curr != last:
            changed = [p for p, t in curr.items() if last.get(p) != t]
            last = curr
            for ch in glob.glob("*_*/*/ch*.qmd"):
                chap_dir = os.path.dirname(ch)
                if any(p.startswith(chap_dir) or p.startswith("_assets") for p in changed):
                    os.utime(ch, None)
except KeyboardInterrupt:
    proc.terminate()
