# Hyper-Vision

Hyper-Vision is a cross-platform video monitoring application built using Python, Qt5, and OpenCV. It allows users to view live camera feeds, capture snapshots, and record videos. The application includes features such as focus peaking, RGB and luminance histograms, and a rule of thirds grid to assist with video composition.

## Features

- **Live Camera Feed**: Automatically detects connected cameras and allows users to switch between different video sources.
- **Snapshot and Video Recording**: Capture snapshots and record videos directly from the live feed. A red tally border indicates when recording is active.
- **Focus Peaking**: Enables focus peaking with adjustable sensitivity and selectable colors (red, blue, green) to assist in ensuring subjects are in focus.
- **RGB and Luminance Histograms**: Displays real-time histograms for the video feed, including separate RGB histograms and a combined luminance histogram.
- **Rule of Thirds Grid**: An overlay to assist in composing shots according to the rule of thirds.

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/hyper-vision.git
   cd hyper-vision
   pip install -r requirements.txt
   python main.py
