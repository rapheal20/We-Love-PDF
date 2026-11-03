import threading
import webview
from app import app 
import os 

def run_flask():
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    webview.settings['ALLOW_DOWNLOADS'] = True

    app_data_path = os.path.join(os.path.expanduser('~'), '.welovepdf_data')

    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

    # Create a native desktop application window
    webview.create_window('We Love PDF', 'http://127.0.0.1:5000', width=1200, height=800)
    webview.start()