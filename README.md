# ITI Workshop Safety Simulation (ROS 2 Humble + Gazebo Fortress)

Simulates workers moving around an ITI workshop with four machines. Each machine
has a **warning zone** and a smaller **danger zone**. The node raises alerts when
a worker enters a danger zone, or enters a warning zone without PPE.

## Contents

| Path | Purpose |
|---|---|
| `src/safety_sim/safety_sim/safety_sim_node.py` | Simulation, zone logic, alerts, RViz markers |
| `src/safety_sim/safety_sim/dashboard.py` | Tkinter live dashboard (map, KPIs, worker table, alert log) |
| `src/safety_sim/launch/safety_sim.launch.py` | Starts Gazebo, simulation node, dashboard, RViz |
| `src/safety_sim/worlds/iti_workshop.sdf` | Gazebo workshop world (floor, walls, machines, zone markings) |
| `src/safety_sim/rviz/safety.rviz` | RViz layout |
| `setup_workspace.sh` | Installs dependencies and builds |

## Quick start

```bash
bash setup_workspace.sh
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch safety_sim safety_sim.launch.py
```

## Launch arguments

| Argument | Default | Meaning |
|---|---|---|
| `use_gazebo` | `true` | Start Gazebo with the workshop world |
| `headless` | `false` | Gazebo server only, no GUI |
| `use_rviz` | `true` | Start RViz |
| `use_dashboard` | `true` | Start the Tkinter dashboard |
| `num_workers` | `4` | Number of simulated workers |

## Topics

| Topic | Type | Content |
|---|---|---|
| `/safety/status` | `std_msgs/String` (JSON) | Workers, machines, KPIs at 10 Hz |
| `/safety/alerts` | `std_msgs/String` (JSON) | One message per new alert |
| `/safety/zones` | `visualization_msgs/MarkerArray` | Machines and zone discs |
| `/safety/workers` | `visualization_msgs/MarkerArray` | Workers coloured by state |

## States

| State | Meaning | Colour |
|---|---|---|
| SAFE | Outside all zones | Green |
| WARNING | In a warning zone, PPE on | Yellow |
| PPE_VIOLATION | In a warning zone, PPE off | Orange |
| DANGER | Inside a danger zone | Red |

## Notes

- Workers are shown in the dashboard and RViz. The Gazebo world is the static
  workshop environment; workers are not spawned inside Gazebo.
- Machine positions in `iti_workshop.sdf` must stay in sync with `MACHINES` in
  `safety_sim_node.py` if you edit either.
- Needs a desktop session (`DISPLAY`) for the dashboard, RViz and Gazebo GUI.
