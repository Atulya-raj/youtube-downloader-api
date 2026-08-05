import os
import sys

# Redirect file descriptors 1 and 2 at the OS level BEFORE anything imports `logging` or `sys` captures them
try:
    fd_null = os.open(os.devnull, os.O_WRONLY)
    os.dup2(fd_null, 1)
    os.dup2(fd_null, 2)
except Exception:
    pass

# Add the parent directory to the python path so the 'app' module can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

sys.stdout = open(os.path.join(log_dir, 'stdout.log'), 'a', encoding='utf-8')
sys.stderr = open(os.path.join(log_dir, 'stderr.log'), 'a', encoding='utf-8')

from app import app

if __name__ == '__main__':
    # You can change the port here if needed
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
