#!/usr/bin/env python3
"""ITI workshop safety simulation node.

Simulates workers walking around a workshop with machines that have
danger and warning zones. Publishes:

  /safety/status  (std_msgs/String, JSON)  full state for the dashboard
  /safety/alerts  (std_msgs/String, JSON)  one message per new alert
  /safety/zones   (MarkerArray)            machines + zone discs for RViz
  /safety/workers (MarkerArray)            workers for RViz
"""
import json
import math
import random

import rclpy
from rclpy.node import Node
from std_msgs.msg import ColorRGBA, String
from visualization_msgs.msg import Marker, MarkerArray

FRAME = 'world'
BOUNDS = (-9.0, 9.0, -5.0, 5.0)  # xmin, xmax, ymin, ymax (walkable area)

# Must match worlds/iti_workshop.sdf
MACHINES = [
    {'name': 'Lathe', 'x': -6.0, 'y': 3.0, 'sx': 2.0, 'sy': 0.8,
     'sz': 1.2, 'danger': 1.6, 'warn': 2.8},
    {'name': 'Drill Press', 'x': -2.0, 'y': -3.5, 'sx': 0.6, 'sy': 0.6,
     'sz': 1.8, 'danger': 1.4, 'warn': 2.4},
    {'name': 'Welding Bay', 'x': 4.0, 'y': 3.5, 'sx': 1.6, 'sy': 1.6,
     'sz': 1.0, 'danger': 2.0, 'warn': 3.2},
    {'name': 'Grinder', 'x': 7.0, 'y': -2.5, 'sx': 0.6, 'sy': 0.5,
     'sz': 1.1, 'danger': 1.5, 'warn': 2.6},
]

COLORS = {
    'SAFE': (0.18, 0.80, 0.44),
    'WARNING': (0.95, 0.77, 0.06),
    'PPE_VIOLATION': (0.90, 0.49, 0.13),
    'DANGER': (0.91, 0.30, 0.24),
}
SEVERITY = {'SAFE': 0, 'WARNING': 1, 'PPE_VIOLATION': 2, 'DANGER': 3}


def rgba(rgb, a=1.0):
    return ColorRGBA(r=float(rgb[0]), g=float(rgb[1]),
                     b=float(rgb[2]), a=float(a))


class Worker:
    """A simulated worker doing a random walk between waypoints."""

    def __init__(self, idx, rng):
        self.name = 'Worker-%d' % (idx + 1)
        self.x = rng.uniform(BOUNDS[0], BOUNDS[1])
        self.y = rng.uniform(BOUNDS[2], BOUNDS[3])
        self.speed = rng.uniform(0.6, 1.2)
        self.ppe = True
        self.dwell = 0.0
        self.state = 'SAFE'
        self.machine = None
        self.dist = None
        self.tx = self.x
        self.ty = self.y
        self.pick_target(rng)

    def pick_target(self, rng):
        if rng.random() < 0.5:
            m = rng.choice(MACHINES)
            ang = rng.uniform(0.0, 2.0 * math.pi)
            r = rng.uniform(m['danger'] * 0.6, m['warn'])
            tx = m['x'] + r * math.cos(ang)
            ty = m['y'] + r * math.sin(ang)
        else:
            tx = rng.uniform(BOUNDS[0], BOUNDS[1])
            ty = rng.uniform(BOUNDS[2], BOUNDS[3])
        self.tx = min(max(tx, BOUNDS[0]), BOUNDS[1])
        self.ty = min(max(ty, BOUNDS[2]), BOUNDS[3])

    def step(self, dt, rng):
        # PPE randomly toggles: mostly on, occasionally removed
        if self.ppe and rng.random() < 0.004:
            self.ppe = False
        elif not self.ppe and rng.random() < 0.02:
            self.ppe = True

        if self.dwell > 0.0:
            self.dwell -= dt
            return
        dx, dy = self.tx - self.x, self.ty - self.y
        d = math.hypot(dx, dy)
        move = self.speed * dt
        if d <= max(move, 0.05):
            self.x, self.y = self.tx, self.ty
            self.dwell = rng.uniform(1.0, 4.0)
            self.pick_target(rng)
        else:
            self.x += dx / d * move
            self.y += dy / d * move

    def classify(self):
        """Return (state, machine_name, distance_to_machine_centre)."""
        worst = ('SAFE', None, None)
        nearest = None
        for m in MACHINES:
            d = math.hypot(self.x - m['x'], self.y - m['y'])
            if nearest is None or d < nearest[1]:
                nearest = (m['name'], d)
            if d < m['danger']:
                state = 'DANGER'
            elif d < m['warn']:
                state = 'WARNING' if self.ppe else 'PPE_VIOLATION'
            else:
                continue
            if SEVERITY[state] > SEVERITY[worst[0]]:
                worst = (state, m['name'], d)
        if worst[0] == 'SAFE' and nearest is not None:
            return 'SAFE', nearest[0], nearest[1]
        return worst


class SafetySimNode(Node):

    def __init__(self):
        super().__init__('safety_sim_node')
        self.declare_parameter('num_workers', 4)
        self.declare_parameter('rate_hz', 10.0)
        self.declare_parameter('seed', 7)

        n = int(self.get_parameter('num_workers').value)
        self.rate = float(self.get_parameter('rate_hz').value)
        self.rng = random.Random(int(self.get_parameter('seed').value))
        self.workers = [Worker(i, self.rng) for i in range(n)]

        self.pub_status = self.create_publisher(String, '/safety/status', 10)
        self.pub_alerts = self.create_publisher(String, '/safety/alerts', 50)
        self.pub_zones = self.create_publisher(MarkerArray, '/safety/zones', 1)
        self.pub_workers = self.create_publisher(
            MarkerArray, '/safety/workers', 10)

        self.elapsed = 0.0
        self.total_ticks = 0
        self.safe_ticks = 0
        self.alert_count = 0
        self.danger_count = 0
        self.ppe_count = 0

        self.dt = 1.0 / self.rate
        self.timer = self.create_timer(self.dt, self.tick)
        self.get_logger().info(
            'Safety simulation started with %d workers at %.1f Hz'
            % (n, self.rate))

    # ------------------------------------------------------------------
    def tick(self):
        self.elapsed += self.dt
        for w in self.workers:
            w.step(self.dt, self.rng)
            prev = w.state
            w.state, w.machine, w.dist = w.classify()

            self.total_ticks += 1
            if w.state in ('SAFE', 'WARNING'):
                self.safe_ticks += 1

            if w.state != prev and w.state in ('DANGER', 'PPE_VIOLATION'):
                self.raise_alert(w)

        self.publish_status()
        self.publish_markers()

    def raise_alert(self, w):
        self.alert_count += 1
        if w.state == 'DANGER':
            self.danger_count += 1
            msg = '%s entered DANGER zone of %s' % (w.name, w.machine)
        else:
            self.ppe_count += 1
            msg = '%s has no PPE near %s' % (w.name, w.machine)
        alert = {
            'time': round(self.elapsed, 1),
            'worker': w.name,
            'level': w.state,
            'machine': w.machine,
            'message': msg,
        }
        self.pub_alerts.publish(String(data=json.dumps(alert)))
        self.get_logger().warn(msg)

    def publish_status(self):
        score = 100.0
        if self.total_ticks:
            score = 100.0 * self.safe_ticks / self.total_ticks
        status = {
            'time': round(self.elapsed, 1),
            'bounds': {'xmin': -10.0, 'xmax': 10.0,
                       'ymin': -6.0, 'ymax': 6.0},
            'machines': MACHINES,
            'workers': [
                {'name': w.name, 'x': round(w.x, 2), 'y': round(w.y, 2),
                 'ppe': w.ppe, 'state': w.state, 'machine': w.machine,
                 'dist': None if w.dist is None else round(w.dist, 2)}
                for w in self.workers],
            'stats': {'alerts': self.alert_count,
                      'danger': self.danger_count,
                      'ppe': self.ppe_count,
                      'score': round(score, 1)},
        }
        self.pub_status.publish(String(data=json.dumps(status)))

    # ------------------------------------------------------------------
    def base_marker(self, ns, mid, mtype):
        m = Marker()
        m.header.frame_id = FRAME
        m.header.stamp = self.get_clock().now().to_msg()
        m.ns = ns
        m.id = mid
        m.type = mtype
        m.action = Marker.ADD
        m.pose.orientation.w = 1.0
        return m

    def publish_markers(self):
        zones = MarkerArray()
        for i, mc in enumerate(MACHINES):
            warn = self.base_marker('warn_zone', i, Marker.CYLINDER)
            warn.pose.position.x, warn.pose.position.y = mc['x'], mc['y']
            warn.pose.position.z = 0.01
            warn.scale.x = warn.scale.y = 2.0 * mc['warn']
            warn.scale.z = 0.02
            warn.color = rgba((0.95, 0.77, 0.06), 0.18)
            zones.markers.append(warn)

            dng = self.base_marker('danger_zone', i, Marker.CYLINDER)
            dng.pose.position.x, dng.pose.position.y = mc['x'], mc['y']
            dng.pose.position.z = 0.02
            dng.scale.x = dng.scale.y = 2.0 * mc['danger']
            dng.scale.z = 0.02
            dng.color = rgba((0.91, 0.30, 0.24), 0.30)
            zones.markers.append(dng)

            box = self.base_marker('machine', i, Marker.CUBE)
            box.pose.position.x, box.pose.position.y = mc['x'], mc['y']
            box.pose.position.z = mc['sz'] / 2.0
            box.scale.x, box.scale.y, box.scale.z = (
                mc['sx'], mc['sy'], mc['sz'])
            box.color = rgba((0.35, 0.40, 0.48), 1.0)
            zones.markers.append(box)

            txt = self.base_marker('machine_label', i, Marker.TEXT_VIEW_FACING)
            txt.pose.position.x, txt.pose.position.y = mc['x'], mc['y']
            txt.pose.position.z = mc['sz'] + 0.5
            txt.scale.z = 0.4
            txt.color = rgba((1.0, 1.0, 1.0), 1.0)
            txt.text = mc['name']
            zones.markers.append(txt)
        self.pub_zones.publish(zones)

        workers = MarkerArray()
        for i, w in enumerate(self.workers):
            body = self.base_marker('worker', i, Marker.CYLINDER)
            body.pose.position.x, body.pose.position.y = w.x, w.y
            body.pose.position.z = 0.85
            body.scale.x = body.scale.y = 0.5
            body.scale.z = 1.7
            body.color = rgba(COLORS[w.state], 0.95)
            workers.markers.append(body)

            head = self.base_marker('worker_head', i, Marker.SPHERE)
            head.pose.position.x, head.pose.position.y = w.x, w.y
            head.pose.position.z = 1.85
            head.scale.x = head.scale.y = head.scale.z = 0.35
            # yellow helmet when PPE is on, bare head otherwise
            head.color = rgba((1.0, 0.85, 0.0) if w.ppe
                              else (0.9, 0.7, 0.6), 1.0)
            workers.markers.append(head)

            label = self.base_marker('worker_label', i,
                                     Marker.TEXT_VIEW_FACING)
            label.pose.position.x, label.pose.position.y = w.x, w.y
            label.pose.position.z = 2.4
            label.scale.z = 0.35
            label.color = rgba(COLORS[w.state], 1.0)
            label.text = '%s [%s]' % (w.name, w.state)
            workers.markers.append(label)
        self.pub_workers.publish(workers)


def main(args=None):
    rclpy.init(args=args)
    node = SafetySimNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
