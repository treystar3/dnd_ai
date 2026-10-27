"""Optional window for the game: python main.py --gui. The terminal stays the default."""

import sys
import threading
import time
import webbrowser

from ui.gui.bridge import Bridge
from ui.gui import server


def launch(game, title: str = "Meravia") -> None:
    """Run game() on a background thread behind a local server and show the page in a window (or the default browser)."""
    bridge = Bridge()
    real_out = sys.stdout
    bridge.install()
    bridge.pinned = server.load_prefs()["pinned"]
    srv = server.make_server(bridge)
    server.serve(srv)

    def run_game():
        try:
            game(bridge)
        except SystemExit:
            pass
        finally:
            bridge.flush_text()
            bridge.emit(k="ended")
            bridge.closed = True
            bridge.finished.set()
            with bridge.cv:
                bridge.cv.notify_all()

    from core import updates
    updates.check_in_background(bridge.update_found)
    t = threading.Thread(target=run_game, daemon=True, name="game")
    t.start()
    try:
        _window(bridge, srv.url, title, t)
    finally:
        bridge.close()
        t.join(timeout=10)
        srv.shutdown()
        bridge.uninstall()


def _window(bridge, url, title, game_thread) -> None:
    try:
        import webview
        window = webview.create_window(title, url, width=1320, height=860, min_size=(900, 560), text_select=True,
                                       background_color="#14110f")      # the dark theme's ground, so the window opens dark
        window.events.closed += bridge.close

        def watch():
            bridge.finished.wait()
            time.sleep(1.5)
            if not bridge.failed:
                window.destroy()
        threading.Thread(target=watch, daemon=True).start()
        webview.start()
        return
    except ImportError:
        reason = "pywebview is not installed (pip install pywebview)"
    except Exception as e:
        reason = f"could not open a window: {e}"
    print(f"{reason}\nOpening the game in your browser instead: {url}", file=sys.__stderr__, flush=True)
    webbrowser.open(url)
    try:
        while not bridge.finished.is_set():
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
