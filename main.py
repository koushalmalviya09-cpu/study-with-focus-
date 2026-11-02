import json
import os
import random
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.properties import ColorProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import FadeTransition, Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.utils import escape_markup

# ---------------------------------------------------------------- palette
BG = (0.04, 0.06, 0.12, 1)
CARD = (0.09, 0.12, 0.21, 1)
CARD2 = (0.14, 0.18, 0.30, 1)
ACCENT = (0.38, 0.40, 0.94, 1)
GREEN = (0.13, 0.77, 0.50, 1)
RED = (0.94, 0.27, 0.27, 1)
TEXT = (0.93, 0.95, 1, 1)
MUTED = (0.58, 0.64, 0.76, 1)

Window.clearcolor = BG
Window.softinput_mode = 'below_target'

# ---------------------------------------------------------------- android
ANDROID = False
try:
    from jnius import autoclass
    from android.runnable import run_on_ui_thread
    ANDROID = True
except ImportError:
    def run_on_ui_thread(func):
        return func

if ANDROID:
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    View = autoclass('android.view.View')
    LayoutParams = autoclass('android.view.WindowManager$LayoutParams')


@run_on_ui_thread
def set_immersive(enable):
    """Hide status + nav bars; they stay hidden even if the user swipes."""
    if not ANDROID:
        return
    try:
        activity = PythonActivity.mActivity
        window = activity.getWindow()
        decor = window.getDecorView()
        if enable:
            decor.setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_FULLSCREEN
                | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
            )
            window.addFlags(LayoutParams.FLAG_KEEP_SCREEN_ON)
        else:
            decor.setSystemUiVisibility(View.SYSTEM_UI_FLAG_VISIBLE)
            window.clearFlags(LayoutParams.FLAG_KEEP_SCREEN_ON)
    except Exception as e:
        print(f"Immersive error: {e}")


@run_on_ui_thread
def start_pin():
    if not ANDROID:
        return
    try:
        PythonActivity.mActivity.startLockTask()
    except Exception as e:
        print(f"startLockTask error: {e}")


@run_on_ui_thread
def stop_pin():
    if not ANDROID:
        return
    try:
        PythonActivity.mActivity.stopLockTask()
    except Exception as e:
        print(f"stopLockTask error: {e}")


def kiosk_is_strict():
    """True when the app is whitelisted by device-owner (no pin prompt,
    power menu and gestures blocked by Android itself)."""
    if not ANDROID:
        return False
    try:
        Context = autoclass('android.content.Context')
        activity = PythonActivity.mActivity
        dpm = activity.getSystemService(Context.DEVICE_POLICY_SERVICE)
        return bool(dpm.isLockTaskPermitted(activity.getPackageName()))
    except Exception:
        return False


def bring_to_front():
    if not ANDROID:
        return
    try:
        activity = PythonActivity.mActivity
        Intent = autoclass('android.content.Intent')
        intent = Intent(activity, activity.getClass())
        intent.addFlags(Intent.FLAG_ACTIVITY_REORDER_TO_FRONT
                        | Intent.FLAG_ACTIVITY_SINGLE_TOP)
        activity.startActivity(intent)
    except Exception as e:
        print(f"Bring-to-front error: {e}")


# ---------------------------------------------------------------- widgets
def make_label(text, size=14, color=TEXT, bold=False, halign='left', **kw):
    lbl = Label(text=text, font_size=sp(size), color=color, bold=bold,
                halign=halign, valign='middle', markup=True, **kw)
    lbl.bind(size=lambda inst, val: setattr(inst, 'text_size', val))
    return lbl


class Card(BoxLayout):
    bg = ColorProperty(CARD)
    radius = NumericProperty(16)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            self._c = Color(*self.bg)
            self._r = RoundedRectangle(pos=self.pos, size=self.size,
                                       radius=[dp(self.radius)])
        self.bind(pos=self._upd, size=self._upd, bg=self._upd)

    def _upd(self, *args):
        self._c.rgba = self.bg
        self._r.pos = self.pos
        self._r.size = self.size
        self._r.radius = [dp(self.radius)]


class RoundedButton(Button):
    bg_color = ColorProperty(ACCENT)

    def __init__(self, **kwargs):
        kwargs.setdefault('bold', True)
        kwargs.setdefault('font_size', sp(15))
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        with self.canvas.before:
            self._c = Color(*self.bg_color)
            self._r = RoundedRectangle(pos=self.pos, size=self.size,
                                       radius=[dp(14)])
        self.bind(pos=self._upd, size=self._upd, bg_color=self._upd,
                  state=self._upd, disabled=self._upd)

    def _upd(self, *args):
        r, g, b, a = self.bg_color
        if self.state == 'down':
            r, g, b = r * 0.75, g * 0.75, b * 0.75
        if self.disabled:
            a = 0.45
        self._c.rgba = (r, g, b, a)
        self._r.pos = self.pos
        self._r.size = self.size


class Bar(Widget):
    value = NumericProperty(0)  # 0..1

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            Color(*CARD2)
            self._t = RoundedRectangle(radius=[dp(6)])
            Color(*GREEN)
            self._f = RoundedRectangle(radius=[dp(6)])
        self.bind(pos=self._upd, size=self._upd, value=self._upd)

    def _upd(self, *args):
        self._t.pos = self.pos
        self._t.size = self.size
        w = self.width * max(0.0, min(1.0, self.value))
        if 0 < w < dp(12):
            w = dp(12)
        self._f.pos = self.pos
        self._f.size = (w, self.height)


class Ring(Widget):
    progress = NumericProperty(1.0)  # 1 = full

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            Color(*CARD2)
            self._track = Line(width=dp(9))
            self._arc_color = Color(*ACCENT)
            self._arc = Line(width=dp(9), cap='round')
        self.bind(pos=self._upd, size=self._upd, progress=self._upd)

    def set_color(self, rgba):
        self._arc_color.rgba = rgba

    def _upd(self, *args):
        r = min(self.width, self.height) / 2 - dp(12)
        if r <= 0:
            return
        cx, cy = self.center
        self._track.circle = (cx, cy, r)
        self._arc.circle = (cx, cy, r, 0, max(1.0, 360 * self.progress))


def header_bar(title, back_text, on_back):
    bar = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(12))
    back = RoundedButton(text=back_text, bg_color=CARD2,
                         size_hint_x=None, width=dp(88))
    back.bind(on_press=on_back)
    bar.add_widget(back)
    bar.add_widget(make_label(f"[b]{title}[/b]", size=19))
    return bar, back


# ---------------------------------------------------------------- screens
class DashboardScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(14))

        head = BoxLayout(orientation='vertical', size_hint_y=None,
                         height=dp(70), spacing=dp(2))
        head.add_widget(make_label("[b]STUDY LOCKDOWN[/b]", size=26))
        head.add_widget(make_label("Lock in. Finish the syllabus.",
                                   size=13, color=MUTED))
        root.add_widget(head)

        prog = Card(orientation='vertical', size_hint_y=None, height=dp(130),
                    padding=dp(18), spacing=dp(10))
        self.pct_label = make_label("[b]0%[/b]", size=34, color=GREEN)
        self.bar = Bar(size_hint_y=None, height=dp(12))
        self.sub_label = make_label("Overall syllabus progress", size=12,
                                    color=MUTED)
        prog.add_widget(self.pct_label)
        prog.add_widget(self.bar)
        prog.add_widget(self.sub_label)
        root.add_widget(prog)

        row = BoxLayout(size_hint_y=None, height=dp(86), spacing=dp(12))
        self.done_num, c1 = self._stat("Done")
        self.left_num, c2 = self._stat("Left")
        self.focus_num, c3 = self._stat("Focus min")
        for c in (c1, c2, c3):
            row.add_widget(c)
        root.add_widget(row)

        b1 = RoundedButton(text="SYLLABUS TRACKER", bg_color=ACCENT,
                           size_hint_y=None, height=dp(58))
        b1.bind(on_press=lambda *a: setattr(self.manager, 'current', 'syllabus'))
        b2 = RoundedButton(text="START FOCUS LOCKDOWN", bg_color=RED,
                           size_hint_y=None, height=dp(58))
        b2.bind(on_press=lambda *a: setattr(self.manager, 'current', 'focus'))
        root.add_widget(b1)
        root.add_widget(b2)
        root.add_widget(Widget())
        self.add_widget(root)

    def _stat(self, caption):
        card = Card(orientation='vertical', padding=dp(10), spacing=dp(2))
        num = make_label("[b]0[/b]", size=24, halign='center')
        card.add_widget(num)
        card.add_widget(make_label(caption, size=11, color=MUTED,
                                   halign='center'))
        return num, card

    def on_enter(self):
        data = App.get_running_app().load_data()
        topics = data["topics"]
        total = len(topics)
        done = sum(1 for t in topics if t["done"])
        frac = done / total if total else 0
        self.pct_label.text = f"[b]{int(frac * 100)}%[/b]"
        self.bar.value = frac
        self.sub_label.text = f"{done} of {total} chapters completed"
        self.done_num.text = f"[b]{done}[/b]"
        self.left_num.text = f"[b]{total - done}[/b]"
        self.focus_num.text = f"[b]{data['focus_minutes']}[/b]"


class TopicRow(Card):
    def __init__(self, idx, topic, on_toggle, on_delete, **kwargs):
        super().__init__(orientation='horizontal', size_hint_y=None,
                         height=dp(60), padding=[dp(10), dp(9)],
                         spacing=dp(10), **kwargs)
        self.idx = idx
        self.done = topic["done"]
        self.name = topic["name"]
        self.on_toggle = on_toggle

        self.tick = RoundedButton(size_hint_x=None, width=dp(44), font_size=sp(12))
        self.tick.bind(on_press=self._toggle)
        self.lbl = make_label("", size=15)
        dele = RoundedButton(text="X", bg_color=(0.55, 0.16, 0.2, 1),
                             size_hint_x=None, width=dp(44))
        dele.bind(on_press=lambda *a: on_delete(idx))

        self.add_widget(self.tick)
        self.add_widget(self.lbl)
        self.add_widget(dele)
        self._paint()

    def _toggle(self, *args):
        self.done = not self.done
        self.on_toggle(self.idx, self.done)
        self._paint()

    def _paint(self):
        safe = escape_markup(self.name)
        if self.done:
            self.tick.bg_color = GREEN
            self.tick.text = "OK"
            self.lbl.text = f"[s]{safe}[/s]"
            self.lbl.color = MUTED
        else:
            self.tick.bg_color = CARD2
            self.tick.text = ""
            self.lbl.text = safe
            self.lbl.color = TEXT


class SyllabusScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(14))
        bar, _ = header_bar("Syllabus", "< Back",
                            lambda *a: setattr(self.manager, 'current', 'dashboard'))
        root.add_widget(bar)

        box = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(10))
        self.input = TextInput(
            hint_text="Add chapter, e.g. Accountancy - Partnership",
            multiline=False, write_tab=False,
            background_normal='', background_active='',
            background_color=CARD, foreground_color=TEXT,
            hint_text_color=MUTED, cursor_color=TEXT,
            padding=[dp(14), dp(15)], font_size=sp(14))
        self.input.bind(on_text_validate=self.add_topic)
        add = RoundedButton(text="ADD", bg_color=GREEN,
                            size_hint_x=None, width=dp(84))
        add.bind(on_press=self.add_topic)
        box.add_widget(self.input)
        box.add_widget(add)
        root.add_widget(box)

        self.scroll = ScrollView(bar_width=dp(3))
        self.list = BoxLayout(orientation='vertical', size_hint_y=None,
                              spacing=dp(10))
        self.list.bind(minimum_height=self.list.setter('height'))
        self.scroll.add_widget(self.list)
        root.add_widget(self.scroll)
        self.add_widget(root)

    def on_enter(self):
        self.refresh()

    def refresh(self):
        self.list.clear_widgets()
        app = App.get_running_app()
        topics = app.load_data()["topics"]
        if not topics:
            self.list.add_widget(make_label(
                "No chapters yet. Add your first one above.",
                color=MUTED, halign='center', size_hint_y=None, height=dp(80)))
        for i, t in enumerate(topics):
            self.list.add_widget(
                TopicRow(i, t, app.toggle_topic, self.delete_topic))

    def add_topic(self, *args):
        text = self.input.text.strip()
        if not text:
            return
        app = App.get_running_app()
        data = app.load_data()
        data["topics"].append({"name": text, "done": False})
        app.save_data(data)
        self.input.text = ""
        self.refresh()

    def delete_topic(self, idx):
        App.get_running_app().delete_topic(idx)
        self.refresh()


class FocusScreen(Screen):
    MOTIVATION = [
        "Discipline over motivation. Stay locked in.",
        "Scrolling will not pass your exams. Studying will.",
        "Pain of discipline or pain of regret. Choose one.",
        "Every minute now is a minute your future self thanks you for.",
        "Close the distractions. Open your mind.",
        "You are building your destiny right now. Keep pushing.",
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.total_seconds = 3600
        self.seconds_left = 3600
        self.end_time = 0
        self.running = False
        self.timer_event = None
        self.quote_event = None

        root = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(12))
        bar, self.back_btn = header_bar("Focus Lockdown", "< Exit", self.go_back)
        root.add_widget(bar)

        # duration controls (hidden while locked)
        self.adjust = BoxLayout(orientation='vertical', size_hint_y=None,
                                height=dp(108), spacing=dp(8))
        r1 = BoxLayout(spacing=dp(10))
        minus = RoundedButton(text="- 15m", bg_color=CARD2)
        minus.bind(on_press=lambda *a: self.adjust_time(-900))
        plus = RoundedButton(text="+ 15m", bg_color=CARD2)
        plus.bind(on_press=lambda *a: self.adjust_time(900))
        self.dur_label = make_label("", size=15, bold=True, halign='center')
        r1.add_widget(minus)
        r1.add_widget(self.dur_label)
        r1.add_widget(plus)
        r2 = BoxLayout(spacing=dp(8))
        for m in (25, 45, 60, 90):
            b = RoundedButton(text=f"{m}m", bg_color=CARD, font_size=sp(13))
            b.bind(on_press=lambda inst, mm=m: self.set_minutes(mm))
            r2.add_widget(b)
        self.adjust.add_widget(r1)
        self.adjust.add_widget(r2)
        root.add_widget(self.adjust)

        # ring + timer
        ring_box = FloatLayout(size_hint_y=None, height=dp(290))
        self.ring = Ring(size_hint=(1, 1))
        self.time_label = make_label("[b]60:00[/b]", size=54, halign='center',
                                     pos_hint={'center_x': .5, 'center_y': .54})
        self.caption = make_label("READY", size=12, color=MUTED,
                                  halign='center',
                                  pos_hint={'center_x': .5, 'center_y': .36})
        ring_box.add_widget(self.ring)
        ring_box.add_widget(self.time_label)
        ring_box.add_widget(self.caption)
        root.add_widget(ring_box)

        quote = Card(size_hint_y=None, height=dp(72), padding=dp(14))
        self.quote_label = make_label(
            "Pick a duration, then lock in.", size=13, color=MUTED,
            halign='center')
        quote.add_widget(self.quote_label)
        root.add_widget(quote)

        self.action = RoundedButton(text="START LOCKDOWN", bg_color=RED,
                                    size_hint_y=None, height=dp(62))
        self.action.bind(on_press=self.on_action)
        root.add_widget(self.action)

        self.mode_label = make_label("", size=11, color=MUTED, halign='center',
                                     size_hint_y=None, height=dp(20))
        root.add_widget(self.mode_label)
        root.add_widget(Widget())
        self.add_widget(root)
        self._show_duration()

    # -- duration
    def _show_duration(self):
        m = self.total_seconds // 60
        self.dur_label.text = f"{m} min"
        self.time_label.text = f"[b]{m:02d}:00[/b]"
        self.ring.progress = 1.0

    def adjust_time(self, delta):
        if self.running:
            return
        self.total_seconds = max(900, min(14400, self.total_seconds + delta))
        self.seconds_left = self.total_seconds
        self._show_duration()

    def set_minutes(self, minutes):
        if self.running:
            return
        self.total_seconds = minutes * 60
        self.seconds_left = self.total_seconds
        self._show_duration()

    def on_enter(self):
        if not self.running:
            self.mode_label.text = (
                "Strict kiosk mode ready" if kiosk_is_strict()
                else "Standard mode: Android will ask to pin the screen")

    # -- lockdown
    def on_action(self, *args):
        if self.running:
            self.quote_label.text = "Locked. There is no way out but finishing."
            return
        self.start_lockdown_session(self.seconds_left)

    def start_lockdown_session(self, duration, end_time=None):
        app = App.get_running_app()
        self.running = True
        self.total_seconds = max(self.total_seconds, duration)
        self.end_time = end_time or (time.time() + duration)
        self.seconds_left = duration
        app.focus_active = True
        app.save_lockdown_state(True, self.end_time, self.total_seconds)

        self.adjust.opacity = 0
        self.adjust.disabled = True
        self.back_btn.disabled = True
        self.action.text = "LOCKED IN"
        self.action.bg_color = CARD2
        self.caption.text = "STAY FOCUSED"
        self.ring.set_color(RED)
        self.mode_label.text = ""

        set_immersive(True)
        start_pin()

        self.timer_event = Clock.schedule_interval(self.tick, 0.5)
        self.quote_event = Clock.schedule_interval(self.rotate_quote, 8)
        self.rotate_quote(0)
        self.tick(0)

    def rotate_quote(self, dt):
        self.quote_label.text = random.choice(self.MOTIVATION)

    def tick(self, dt):
        left = int(round(self.end_time - time.time()))
        if left <= 0:
            self.end_lockdown_session(completed=True)
            return
        self.seconds_left = left
        m, s = divmod(left, 60)
        self.time_label.text = f"[b]{m:02d}:{s:02d}[/b]"
        self.ring.progress = left / float(self.total_seconds)

    def end_lockdown_session(self, completed=True):
        if self.timer_event:
            self.timer_event.cancel()
        if self.quote_event:
            self.quote_event.cancel()
        app = App.get_running_app()
        self.running = False
        app.focus_active = False
        app.save_lockdown_state(False, 0, 0)
        if completed:
            app.add_focus_minutes(self.total_seconds // 60)

        stop_pin()
        set_immersive(False)

        self.adjust.opacity = 1
        self.adjust.disabled = False
        self.back_btn.disabled = False
        self.action.text = "START LOCKDOWN"
        self.action.bg_color = RED
        self.caption.text = "DONE"
        self.ring.set_color(GREEN)
        self.seconds_left = self.total_seconds
        self._show_duration()
        self.quote_label.text = "Session complete. You beat the distraction."

    def go_back(self, *args):
        if not self.running:
            self.manager.current = 'dashboard'


# ---------------------------------------------------------------- app
class StudyTrackerApp(App):
    title = "Study Lockdown"

    def build(self):
        self.focus_active = False
        Window.bind(on_keyboard=self.on_keyboard)

        self.sm = ScreenManager(transition=FadeTransition(duration=0.15))
        self.sm.add_widget(DashboardScreen(name='dashboard'))
        self.sm.add_widget(SyllabusScreen(name='syllabus'))
        self.sm.add_widget(FocusScreen(name='focus'))

        state = self.load_lockdown_state()
        if state["active"]:
            remaining = int(state["end_time"] - time.time())
            if remaining > 0:
                self.focus_active = True
                self.sm.current = 'focus'
                Clock.schedule_once(
                    lambda dt: self.sm.get_screen('focus').start_lockdown_session(
                        remaining, state["end_time"]), 0.5)
            else:
                self.save_lockdown_state(False, 0, 0)
        return self.sm

    # -- anti-escape
    def on_keyboard(self, window, key, *args):
        if self.focus_active and key == 27:  # Back button
            return True
        return False

    def on_pause(self):
        if self.focus_active:
            bring_to_front()
            return True
        return True

    def on_resume(self):
        if self.focus_active:
            set_immersive(True)

    # -- storage
    def _p(self, name):
        return os.path.join(self.user_data_dir, name)

    def load_data(self):
        data = {}
        try:
            with open(self._p('syllabus_data.json'), 'r') as f:
                data = json.load(f)
        except Exception:
            pass
        data.setdefault("topics", [])
        data.setdefault("focus_minutes", 0)
        return data

    def save_data(self, data):
        with open(self._p('syllabus_data.json'), 'w') as f:
            json.dump(data, f)

    def load_lockdown_state(self):
        try:
            with open(self._p('lockdown_state.json'), 'r') as f:
                s = json.load(f)
                return {"active": bool(s.get("active")),
                        "end_time": s.get("end_time", 0),
                        "total": s.get("total", 0)}
        except Exception:
            return {"active": False, "end_time": 0, "total": 0}

    def save_lockdown_state(self, active, end_time, total=0):
        with open(self._p('lockdown_state.json'), 'w') as f:
            json.dump({"active": active, "end_time": end_time,
                       "total": total}, f)

    def toggle_topic(self, index, value):
        data = self.load_data()
        if 0 <= index < len(data["topics"]):
            data["topics"][index]["done"] = value
            self.save_data(data)

    def delete_topic(self, index):
        data = self.load_data()
        if 0 <= index < len(data["topics"]):
            data["topics"].pop(index)
            self.save_data(data)

    def add_focus_minutes(self, minutes):
        data = self.load_data()
        data["focus_minutes"] += int(minutes)
        self.save_data(data)


if __name__ == '__main__':
    StudyTrackerApp().run()
