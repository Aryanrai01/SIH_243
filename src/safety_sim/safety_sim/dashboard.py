#!/usr/bin/env python3
"""Live Tkinter dashboard for the ITI workshop safety simulation."""
import json
import threading
import tkinter as tk
from tkinter import ttk

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

COLORS = {
    'SAFE': '#2ecc71',
    'WARNING': '#f1c40f',
    'PPE_VIOLATION': '#e67e22',
    'DANGER': '#e74c3c',
}
BG = '#1e1e24'
PANEL = '#2a2a32'
FG = '#ecf0f1'
SCALE = 36   # pixels per metre
PAD = 10


class DashboardNode(Node):

    def __init__(self):
        super().__init__('safety_dashboard')
        self.lock = threading.Lock()
        self.status = None
        self.alerts = []
        self.create_subscription(String, '/safety/status', self.on_status, 10)
        self.create_subscription(String, '/safety/alerts', self.on_alert, 50)

    def on_status(self, msg):
        try:
            data = json.loads(msg.data)
        except ValueError:
            return
        with self.lock:
            self.status = data

    def on_alert(self, msg):
        try:
            data = json.loads(msg.data)
        except ValueError:
            return
        with self.lock:
            self.alerts.append(data)
            self.alerts = self.alerts[-200:]

    def snapshot(self):
        with self.lock:
            return self.status, list(self.alerts)


class DashboardUI:

    def __init__(self, root, node):
        self.root = root
        self.node = node
        self.seen_alerts = 0
        root.title('ITI Workshop Safety Dashboard')
        root.configure(bg=BG)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview', background=PANEL, fieldbackground=PANEL,
                        foreground=FG, rowheight=24, borderwidth=0)
        style.configure('Treeview.Heading', background='#3a3a45',
                        foreground=FG)

        left = tk.Frame(root, bg=BG)
        left.pack(side=tk.LEFT, padx=8, pady=8)
        right = tk.Frame(root, bg=BG)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.canvas = tk.Canvas(left, width=20 * SCALE + 2 * PAD,
                                height=12 * SCALE + 2 * PAD, bg='#14141a',
                                highlightthickness=0)
        self.canvas.pack()

        # KPI cards
        kpi = tk.Frame(right, bg=BG)
        kpi.pack(fill=tk.X)
        self.kpis = {}
        for key, title in (('score', 'SAFETY SCORE'), ('alerts', 'ALERTS'),
                           ('danger', 'DANGER'), ('ppe', 'PPE')):
            card = tk.Frame(kpi, bg=PANEL, padx=10, pady=6)
            card.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=3)
            tk.Label(card, text=title, bg=PANEL, fg='#95a5a6',
                     font=('Helvetica', 8, 'bold')).pack()
            lbl = tk.Label(card, text='--', bg=PANEL, fg=FG,
                           font=('Helvetica', 18, 'bold'))
            lbl.pack()
            self.kpis[key] = lbl

        # Score bar
        self.bar = tk.Canvas(right, height=14, bg=PANEL,
                             highlightthickness=0)
        self.bar.pack(fill=tk.X, padx=3, pady=(8, 8))

        # Worker table
        cols = ('worker', 'state', 'machine', 'dist', 'ppe')
        self.tree = ttk.Treeview(right, columns=cols, show='headings',
                                 height=6)
        for c, w in zip(cols, (90, 110, 110, 60, 50)):
            self.tree.heading(c, text=c.upper())
            self.tree.column(c, width=w, anchor=tk.CENTER)
        for state, color in COLORS.items():
            self.tree.tag_configure(state, foreground=color)
        self.tree.pack(fill=tk.X, padx=3)

        tk.Label(right, text='LIVE ALERTS', bg=BG, fg='#95a5a6',
                 font=('Helvetica', 9, 'bold')).pack(anchor=tk.W,
                                                     pady=(10, 2), padx=3)
        self.log = tk.Text(right, height=12, bg=PANEL, fg=FG,
                           relief=tk.FLAT, state=tk.DISABLED,
                           font=('Courier', 9))
        self.log.pack(fill=tk.BOTH, expand=True, padx=3)
        self.log.tag_configure('DANGER', foreground=COLORS['DANGER'])
        self.log.tag_configure('PPE_VIOLATION',
                               foreground=COLORS['PPE_VIOLATION'])

        self.refresh()

    # ------------------------------------------------------------------
    def px(self, x, y):
        return (PAD + (x + 10.0) * SCALE, PAD + (6.0 - y) * SCALE)

    def draw_map(self, status):
        c = self.canvas
        c.delete('all')
        x0, y0 = self.px(-10, 6)
        x1, y1 = self.px(10, -6)
        c.create_rectangle(x0, y0, x1, y1, outline='#555566', width=2)
        for gx in range(-10, 11, 2):
            a = self.px(gx, 6)
            b = self.px(gx, -6)
            c.create_line(a[0], a[1], b[0], b[1], fill='#22222c')
        for gy in range(-6, 7, 2):
            a = self.px(-10, gy)
            b = self.px(10, gy)
            c.create_line(a[0], a[1], b[0], b[1], fill='#22222c')

        for m in status['machines']:
            cx, cy = self.px(m['x'], m['y'])
            rw = m['warn'] * SCALE
            rd = m['danger'] * SCALE
            c.create_oval(cx - rw, cy - rw, cx + rw, cy + rw,
                          outline=COLORS['WARNING'], dash=(4, 4))
            c.create_oval(cx - rd, cy - rd, cx + rd, cy + rd,
                          outline=COLORS['DANGER'], fill='#3a1d1d')
            hx, hy = m['sx'] * SCALE / 2, m['sy'] * SCALE / 2
            c.create_rectangle(cx - hx, cy - hy, cx + hx, cy + hy,
                               fill='#5a6577', outline='')
            c.create_text(cx, cy - rd - 8, text=m['name'], fill=FG,
                          font=('Helvetica', 8, 'bold'))

        for w in status['workers']:
            cx, cy = self.px(w['x'], w['y'])
            col = COLORS.get(w['state'], '#ffffff')
            c.create_oval(cx - 8, cy - 8, cx + 8, cy + 8, fill=col,
                          outline='#ffd400' if w['ppe'] else '#ffffff',
                          width=3)
            c.create_text(cx, cy + 16, text=w['name'], fill=FG,
                          font=('Helvetica', 8))

    def draw_bar(self, score):
        self.bar.delete('all')
        width = max(self.bar.winfo_width(), 10)
        color = COLORS['SAFE'] if score >= 90 else (
            COLORS['WARNING'] if score >= 70 else COLORS['DANGER'])
        self.bar.create_rectangle(0, 0, width * score / 100.0, 14,
                                  fill=color, outline='')

    def refresh(self):
        status, alerts = self.node.snapshot()
        if status is None:
            self.canvas.delete('all')
            self.canvas.create_text(
                360, 216, text='Waiting for /safety/status ...', fill=FG,
                font=('Helvetica', 14))
        else:
            self.draw_map(status)
            stats = status['stats']
            self.kpis['score'].config(text='%.1f%%' % stats['score'])
            self.kpis['alerts'].config(text=str(stats['alerts']))
            self.kpis['danger'].config(text=str(stats['danger']))
            self.kpis['ppe'].config(text=str(stats['ppe']))
            self.draw_bar(stats['score'])

            self.tree.delete(*self.tree.get_children())
            for w in status['workers']:
                dist = '-' if w['dist'] is None else '%.1f m' % w['dist']
                self.tree.insert(
                    '', tk.END, tags=(w['state'],),
                    values=(w['name'], w['state'], w['machine'] or '-',
                            dist, 'ON' if w['ppe'] else 'OFF'))

        # The node keeps only the last 200 alerts, so track by total count
        # of alerts reported in status when possible.
        if alerts and status is not None:
            total = status['stats']['alerts']
            fresh = total - self.seen_alerts
            if fresh > 0:
                self.seen_alerts = total
                self.log.config(state=tk.NORMAL)
                for a in alerts[-fresh:]:
                    self.log.insert(
                        '1.0',
                        '[%7.1fs] %s\n' % (a['time'], a['message']),
                        a['level'])
                self.log.config(state=tk.DISABLED)

        self.root.after(100, self.refresh)


def main(args=None):
    rclpy.init(args=args)
    node = DashboardNode()
    spinner = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spinner.start()

    root = tk.Tk()
    DashboardUI(root, node)

    def on_close():
        root.destroy()

    root.protocol('WM_DELETE_WINDOW', on_close)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
