from server import choose_window


def window(number, owner="reMarkable", width=1000, height=800, layer=0, onscreen=True, name=None):
    return {
        "kCGWindowNumber": number,
        "kCGWindowName": name,
        "kCGWindowOwnerName": owner,
        "kCGWindowLayer": layer,
        "kCGWindowIsOnscreen": onscreen,
        "kCGWindowBounds": {"Width": width, "Height": height},
    }


def test_picks_frontmost_visible_app_window():
    windows = [
        window(1, owner="Finder", width=3000, height=2000),
        window(2, width=900, height=1200),
        window(3, width=1400, height=1000),
    ]
    assert choose_window(windows)["kCGWindowNumber"] == 2


def test_prefers_screen_share_window_behind_library():
    windows = [
        window(1, name="reMarkable", width=1600, height=1366),
        window(2, name="Bildschirm teilen", width=1600, height=1252),
    ]
    assert choose_window(windows)["kCGWindowNumber"] == 2


def test_ignores_menu_bars_offscreen_and_overlays():
    windows = [
        window(1, width=2560, height=30),
        window(2, onscreen=None),
        window(3, layer=25),
    ]
    assert choose_window(windows) is None
