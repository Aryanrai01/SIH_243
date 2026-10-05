#!/usr/bin/env bash
# Installs dependencies, builds the workspace and prints run instructions.
# Usage:  bash setup_workspace.sh            (from inside safety_ws/)
set -euo pipefail

ROS_DISTRO_NAME="${ROS_DISTRO:-humble}"
WS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -f "/opt/ros/${ROS_DISTRO_NAME}/setup.bash" ]; then
  echo "ERROR: /opt/ros/${ROS_DISTRO_NAME}/setup.bash not found."
  echo "Install ROS 2 Humble first: https://docs.ros.org/en/humble/Installation.html"
  exit 1
fi

echo "==> Installing system packages (sudo required)"
sudo apt-get update
sudo apt-get install -y \
  python3-tk python3-colcon-common-extensions \
  "ros-${ROS_DISTRO_NAME}-ros-gz" \
  "ros-${ROS_DISTRO_NAME}-ros-gz-sim" \
  "ros-${ROS_DISTRO_NAME}-rviz2" \
  "ros-${ROS_DISTRO_NAME}-tf2-ros" \
  "ros-${ROS_DISTRO_NAME}-visualization-msgs"

echo "==> Building workspace"
# shellcheck disable=SC1090
source "/opt/ros/${ROS_DISTRO_NAME}/setup.bash"
cd "${WS_DIR}"
colcon build --symlink-install

cat <<MSG

Build finished. Run the simulation with:

  source /opt/ros/${ROS_DISTRO_NAME}/setup.bash
  source ${WS_DIR}/install/setup.bash
  ros2 launch safety_sim safety_sim.launch.py

Launch options:
  headless:=true        Gazebo server only (no Gazebo window)
  use_gazebo:=false     skip Gazebo entirely
  use_rviz:=false       skip RViz
  use_dashboard:=false  skip the Tkinter dashboard
  num_workers:=6        number of simulated workers
MSG
