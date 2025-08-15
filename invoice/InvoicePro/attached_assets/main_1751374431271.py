import webbrowser
import threading
from app import app  # 👈 import the app object from app.py

def open_browser():
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == '__main__':
    threading.Timer(1.25, open_browser).start()
    app.run(debug=False, port=5000)
