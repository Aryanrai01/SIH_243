import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'safety_sim'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'worlds'),
            glob('worlds/*.sdf')),
        (os.path.join('share', package_name, 'rviz'),
            glob('rviz/*.rviz')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Safety Sim Maintainer',
    maintainer_email='user@example.com',
    description='ITI workshop safety simulation with live dashboard, '
                'Gazebo world and RViz visualization',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'safety_sim_node = safety_sim.safety_sim_node:main',
            'dashboard = safety_sim.dashboard:main',
        ],
    },
)
