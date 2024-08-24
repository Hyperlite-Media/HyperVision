import os
import cv2
import numpy as np
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QIcon
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, \
    QSpacerItem, QSizePolicy, QSplashScreen


# SplashScreen class to display an animated splash screen
class SplashScreen(QSplashScreen):
    def __init__(self, animation_frames):
        super().__init__()
        self.animation_frames = animation_frames
        self.current_frame = 0
        # Set window to stay on top and frameless
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setPixmap(QPixmap(self.animation_frames[0]))

    # Start the timer to update the splash screen animation
    def showEvent(self, event):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(100)  # Update frame every 100ms

    # Update the current frame for the animation
    def update_frame(self):
        self.current_frame = (self.current_frame + 1) % len(self.animation_frames)
        self.setPixmap(QPixmap(self.animation_frames[self.current_frame]))


# Widget to display a histogram
class HistogramWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.histogram = None
        self.setFixedSize(256, 100)

    # Set histogram data and update the widget
    def set_histogram(self, histogram):
        self.histogram = histogram
        self.update()

    # Paint the histogram
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 180))
        painter.drawRoundedRect(self.rect(), 5, 5)

        if self.histogram is not None and self.isVisible():
            # Ensure max_value is a float scalar
            max_value = float(np.max(self.histogram))
            if max_value > 0:
                for i in range(256):
                    # Ensure self.histogram[i] is a scalar
                    value = int(float(self.histogram[i].item()) * self.height() / max_value)
                    painter.setPen(QColor(i, i, i))
                    painter.drawLine(i, self.height(), i, self.height() - value)


# Widget to display RGB histograms
class RGBWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(768, 100)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.RGBhistograms = [None, None, None]

    # Set RGB histograms data
    def set_histograms(self, RGBhistograms):
        self.RGBhistograms = RGBhistograms[:3]
        self.update()

    # Paint the RGB histograms
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 180))
        painter.drawRoundedRect(self.rect(), 5, 5)

        if self.isVisible():
            max_value = max((max(hist) for hist in self.RGBhistograms if hist is not None), default=0)
            if max_value > 0:
                for channel, hist in enumerate(self.RGBhistograms):
                    if hist is not None:
                        color = QColor(255, 0, 0) if channel == 0 else QColor(0, 255, 0) if channel == 1 else QColor(0,
                                                                                                                     0,
                                                                                                                     255)
                        painter.setPen(color)
                        for i in range(256):
                            value = int(hist[i] * self.height() / max_value)
                            painter.drawLine(i + channel * 256, self.height(), i + channel * 256, self.height() - value)


# Widget to display the rule of thirds grid
class RuleOfThirdsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

    # Paint the rule of thirds grid lines
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QColor(255, 255, 255, 180))
        width = self.width()
        height = self.height()

        # Draw vertical lines
        painter.drawLine(width // 3, 0, width // 3, height)
        painter.drawLine(2 * width // 3, 0, 2 * width // 3, height)
        # Draw horizontal lines
        painter.drawLine(0, height // 3, width, height // 3)
        painter.drawLine(0, 2 * height // 3, width, 2 * height // 3)


# Main application class
class App(QWidget):
    def __init__(self):
        super().__init__()
        # Initialize the splash screen
        splash_screen = SplashScreen(["SplashScreen2.jpg"])
        splash_screen.show()
        QTimer.singleShot(5000, lambda: splash_screen.close())  # Close splash screen after 5 seconds

        self.setWindowTitle("Hyper-Vision")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        self.showFullScreen()
        self.setStyleSheet("background-color: #111111;")
        self.video_sources = self.detect_video_sources()
        self.histogram_widget = HistogramWidget()
        self.RGBhistogram_widget = RGBWidget()
        self.rule_of_thirds_widget = RuleOfThirdsWidget()
        self.video_counter = 1
        self.photo_counter = 1
        self.setup_ui()

        self.selected_video_source = self.video_sources[0]
        self.vid = MyVideoCapture(self.selected_video_source)
        self.fps = 60
        self.delay = int(1000 / self.fps)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(self.delay)

        self.threshold_value = 20
        self.focus_peaking_color = (255, 0, 0)

        self.recording = False
        self.out = None
        self.output_path = self.generate_video_path()

    # Generate file path for saving video
    def generate_video_path(self):
        return f"/Users/bradanderson/desktop/ScreenShots/Video{self.video_counter}.mov"  # Set path for video to be
        # saved

    # Generate file path for saving photo
    def generate_photo_path(self):
        return f"/Users/bradanderson/desktop/ScreenShots/Photo{self.photo_counter}.jpg"  # Set path for photo to be
        # saved

    # Apply red border to indicate recording
    def apply_tally_border(self, frame):
        border_thickness = 10
        color = (0, 0, 255)  # BGR color for red
        frame_with_border = frame.copy()
        height, width = frame.shape[:2]
        cv2.rectangle(frame_with_border, (0, 0), (width, height), color, thickness=border_thickness)
        return frame_with_border

    # Handle window close event
    def closeEvent(self, event):
        if self.histogram_widget.isVisible():
            self.histogram_widget.close()
        if self.RGBhistogram_widget.isVisible():
            self.RGBhistogram_widget.close()
        if self.recording:
            self.stop_recording()
        event.accept()

    # Setup the user interface
    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.addItem(QSpacerItem(80, 50, QSizePolicy.Expanding, QSizePolicy.Minimum))

        video_and_controls_layout = QVBoxLayout()

        button_stylesheet = """
        QPushButton {
            background: transparent;
            border-radius: 15px;
            color: white;
            font-family: Orbitron;
            font-size: 10pt;
        }
        QPushButton:hover {
            text-decoration: underline;
        }
        """
        combobox_stylesheet = """
        QComboBox {
            background: transparent;
            border-radius: 5px;
            color: white;
            font-family: Orbitron;
            font-size: 10pt;
        }
        """

        # Display area for the video feed
        self.video_label = QLabel(self)
        self.video_label.setFixedSize(1366, 768)
        video_and_controls_layout.addWidget(self.video_label, alignment=Qt.AlignCenter)

        control_layout = QHBoxLayout()
        control_layout.addItem(QSpacerItem(80, 70, QSizePolicy.Expanding, QSizePolicy.Minimum))

        #photo_icon = QIcon("/Users/bradanderson/PycharmProjects/HyperView/take-photo-icon.png")

        # Menu button to toggle control visibility
        self.menu_btn = QPushButton("Menu")
        self.menu_btn.setFixedSize(108, 30)
        self.menu_btn.setCheckable(True)
        self.menu_btn.clicked.connect(self.toggle_menu)
        control_layout.addWidget(self.menu_btn)
        self.menu_btn.setStyleSheet(button_stylesheet)

        # Combobox to select video source
        self.source_combobox = QComboBox()
        self.source_combobox.addItems([f"Camera {i + 1}" for i in range(len(self.video_sources))])
        self.source_combobox.currentIndexChanged.connect(self.change_video_source)
        self.source_combobox.setFixedSize(108, 30)
        self.source_combobox.setStyleSheet(combobox_stylesheet)
        control_layout.addWidget(self.source_combobox)

        # Button to take a snapshot
        self.snapshot_btn = QPushButton("Photo")
        self.snapshot_btn.setCheckable(True)
        self.snapshot_btn.clicked.connect(self.snapshot)
        self.snapshot_btn.setFixedSize(108, 30)
        control_layout.addWidget(self.snapshot_btn)
        self.snapshot_btn.setStyleSheet(button_stylesheet)

        # Button to start/stop recording
        self.record_btn = QPushButton("Record")
        self.record_btn.setCheckable(True)
        self.record_btn.setFixedSize(108, 30)
        self.record_btn.toggled.connect(self.toggle_recording)
        control_layout.addWidget(self.record_btn)
        self.record_btn.setStyleSheet(button_stylesheet)

        # Button to enable/disable focus peaking
        self.focus_peaking_btn = QPushButton("Focus Peaking")
        self.focus_peaking_btn.setCheckable(True)
        self.focus_peaking_btn.setChecked(False)
        self.focus_peaking_btn.clicked.connect(self.toggle_focus_peaking)
        self.focus_peaking_btn.setFixedSize(108, 30)
        control_layout.addWidget(self.focus_peaking_btn)
        self.focus_peaking_btn.setStyleSheet(button_stylesheet)

        # Combobox to change focus peaking color
        self.color_combobox = QComboBox()
        self.color_combobox.addItems(["Red", "Blue", "Green"])
        self.color_combobox.setCurrentIndex(0)
        self.color_combobox.currentIndexChanged.connect(self.change_focus_peaking_color)
        self.color_combobox.setFixedSize(108, 30)
        self.color_combobox.setStyleSheet(combobox_stylesheet)
        control_layout.addWidget(self.color_combobox)

        # Buttons to adjust focus peaking threshold
        self.increase_threshold_btn = QPushButton("Decrease Peaking")
        self.increase_threshold_btn.clicked.connect(self.increase_threshold)
        self.increase_threshold_btn.setFixedSize(108, 30)
        control_layout.addWidget(self.increase_threshold_btn)
        self.increase_threshold_btn.setStyleSheet(button_stylesheet)

        control_layout.addItem(QSpacerItem(10, 10, QSizePolicy.Fixed, QSizePolicy.Minimum))

        self.decrease_threshold_btn = QPushButton("Increase Peaking")
        self.decrease_threshold_btn.clicked.connect(self.decrease_threshold)
        self.decrease_threshold_btn.setFixedSize(108, 30)
        control_layout.addWidget(self.decrease_threshold_btn)
        self.decrease_threshold_btn.setStyleSheet(button_stylesheet)

        # Buttons to toggle visibility of histograms and rule of thirds grid
        self.toggle_histogram_btn = QPushButton("Histogram")
        self.toggle_histogram_btn.clicked.connect(self.toggle_histogram)
        self.toggle_histogram_btn.setFixedSize(108, 30)
        control_layout.addWidget(self.toggle_histogram_btn)
        self.toggle_histogram_btn.setStyleSheet(button_stylesheet)

        self.toggle_RGBhistogram_btn = QPushButton("RGBHistogram")
        self.toggle_RGBhistogram_btn.clicked.connect(self.toggle_RGBhistogram)
        self.toggle_RGBhistogram_btn.setFixedSize(108, 30)
        self.toggle_RGBhistogram_btn.setStyleSheet(button_stylesheet)
        control_layout.addWidget(self.toggle_RGBhistogram_btn)
        self.toggle_RGBhistogram_btn.setStyleSheet(button_stylesheet)

        self.toggle_thirds_grid_btn = QPushButton("Compose")
        self.toggle_thirds_grid_btn.clicked.connect(self.toggle_thirds_grid)
        self.toggle_thirds_grid_btn.setFixedSize(108, 30)
        control_layout.addWidget(self.toggle_thirds_grid_btn)
        self.toggle_thirds_grid_btn.setStyleSheet(button_stylesheet)

        # Exit button to close the application
        self.exit_button = QPushButton("Exit App")
        self.exit_button.clicked.connect(QApplication.instance().quit)
        self.exit_button.setFixedSize(108, 30)
        control_layout.addWidget(self.exit_button)
        self.exit_button.setStyleSheet(button_stylesheet)

        control_layout.addStretch(0)
        video_and_controls_layout.addLayout(control_layout)
        video_and_controls_layout.addStretch(1)
        main_layout.addLayout(video_and_controls_layout)
        main_layout.addStretch(1)
        self.setLayout(main_layout)
        self.hide_controls()

    # Toggle visibility of menu controls
    def toggle_menu(self):
        if self.menu_btn.isChecked():
            self.show_controls()
        else:
            self.hide_controls()

    # Show menu controls
    def show_controls(self):
        self.source_combobox.show()
        self.snapshot_btn.show()
        self.record_btn.show()
        self.focus_peaking_btn.show()
        self.color_combobox.show()
        self.increase_threshold_btn.show()
        self.decrease_threshold_btn.show()
        self.toggle_histogram_btn.show()
        self.toggle_RGBhistogram_btn.show()
        self.toggle_thirds_grid_btn.show()
        self.exit_button.show()

    # Hide menu controls
    def hide_controls(self):
        self.source_combobox.hide()
        self.snapshot_btn.hide()
        self.record_btn.hide()
        self.focus_peaking_btn.hide()
        self.color_combobox.hide()
        self.increase_threshold_btn.hide()
        self.decrease_threshold_btn.hide()
        self.toggle_histogram_btn.hide()
        self.toggle_RGBhistogram_btn.hide()
        self.toggle_thirds_grid_btn.hide()
        self.exit_button.hide()

    # Toggle visibility of the histogram widget
    def toggle_histogram(self):
        if self.histogram_widget.isVisible():
            self.histogram_widget.hide()
        else:
            self.histogram_widget.setVisible(True)
            video_label_geometry = self.video_label.geometry()
            histogram_widget_width = self.histogram_widget.width()
            histogram_widget_height = self.histogram_widget.height()
            offset_x = 72
            offset_y = 69
            histogram_x = self.video_label.mapToGlobal(
                video_label_geometry.bottomRight()).x() - histogram_widget_width - offset_x
            histogram_y = self.video_label.mapToGlobal(
                video_label_geometry.bottomRight()).y() - histogram_widget_height - offset_y
            self.histogram_widget.move(histogram_x, histogram_y)

    # Toggle visibility of the RGB histogram widget
    def toggle_RGBhistogram(self):
        if self.RGBhistogram_widget.isVisible():
            self.RGBhistogram_widget.hide()
        else:
            self.RGBhistogram_widget.setVisible(True)
            video_label_geometry = self.video_label.geometry()
            RGBhistogramwidget_width = self.RGBhistogram_widget.width()
            RGBhistogramwidget_height = self.RGBhistogram_widget.height()
            offset_x = 597
            offset_y = -38
            RGBhistogram_x = video_label_geometry.bottomRight().x() - RGBhistogramwidget_width - offset_x
            RGBhistogram_y = video_label_geometry.bottomRight().y() - RGBhistogramwidget_height - offset_y
            self.RGBhistogram_widget.move(RGBhistogram_x, RGBhistogram_y)

    # Toggle visibility of the rule of thirds grid
    def toggle_thirds_grid(self):
        if self.rule_of_thirds_widget.isVisible():
            self.rule_of_thirds_widget.hide()
        else:
            self.rule_of_thirds_widget.setVisible(True)
            self.rule_of_thirds_widget.resize(self.video_label.size())
            video_label_geometry = self.video_label.geometry()
            rule_of_thirds_widget_width = self.rule_of_thirds_widget.width()
            rule_of_thirds_widget_height = self.rule_of_thirds_widget.height()
            offset_x = 72
            offset_y = 69
            thirds_x = self.video_label.mapToGlobal(
                video_label_geometry.bottomRight()).x() - rule_of_thirds_widget_width - offset_x
            thirds_y = self.video_label.mapToGlobal(
                video_label_geometry.bottomRight()).y() - rule_of_thirds_widget_height - offset_y
            self.rule_of_thirds_widget.move(thirds_x, thirds_y)

    # Detect available video sources (cameras)
    def detect_video_sources(self):
        available_sources = []
        for i in range(3):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available_sources.append(i)
                cap.release()
        return available_sources

    # Change the video source based on the selected index
    def change_video_source(self, index):
        selected_video_source = self.video_sources[index]
        self.vid = MyVideoCapture(selected_video_source)

    # Update the video frame displayed on the label
    def update_frame(self):
        ret, frame = self.vid.get_frame()

        if ret:
            frame.copy()
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            histogram = cv2.calcHist([gray_frame], [0], None, [256], [0, 256])
            self.histogram_widget.set_histogram(histogram)

            # Calculate histograms for Red, Green, and Blue channels
            red_histogram = cv2.calcHist([frame], [0], None, [256], [0, 256]).reshape(-1)
            green_histogram = cv2.calcHist([frame], [1], None, [256], [0, 256]).reshape(-1)
            blue_histogram = cv2.calcHist([frame], [2], None, [256], [0, 256]).reshape(-1)
            # Normalize histograms to values between 0 and 1
            red_histogram /= np.max(red_histogram)
            green_histogram /= np.max(green_histogram)
            blue_histogram /= np.max(blue_histogram)

            # Pass histograms to the RGB Parade widget
            self.RGBhistogram_widget.set_histograms([red_histogram, green_histogram, blue_histogram])

        if ret:
            frame_with_effects = frame.copy()
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            histogram = cv2.calcHist([gray_frame], [0], None, [256], [0, 256])
            self.histogram_widget.set_histogram(histogram)

            if self.focus_peaking_btn.isChecked():
                frame_with_effects = self.apply_focus_peaking(frame_with_effects)

            self.display_frame(frame_with_effects)

            # Convert frame to BGR color format if focus peaking is turned off
            if not self.focus_peaking_btn.isChecked():
                frame_with_effects = cv2.cvtColor(frame_with_effects, cv2.COLOR_RGB2BGR)

            if self.recording:
                frame_with_effects = self.apply_tally_border(frame_with_effects)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.out.write(frame_rgb)

            self.display_frame(frame_with_effects)

            # Record the raw frame if recording is active
            if self.recording:
                # Convert the frame to BGR format for recording
                recording_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                self.out.write(recording_frame)

    # Handle key press events, like taking a snapshot with space bar
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.snapshot()

    # Capture a snapshot and save it to the specified location
    def snapshot(self):
        ret, frame = self.vid.get_frame()

        if ret:
            target_resolution = (3840, 2160)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            resized_frame = cv2.resize(frame_rgb, target_resolution)
            save_dir = "/Users/bradanderson/desktop/ScreenShots"  # Path where images will be saved
            os.makedirs(save_dir, exist_ok=True)
            filename = f"Photo{self.photo_counter}.jpg"
            filepath = os.path.join(save_dir, filename)
            cv2.imwrite(filepath, resized_frame)
            self.photo_counter += 1

    # Toggle focus peaking effect
    def toggle_focus_peaking(self):
        pass

    # Increase focus peaking threshold
    def increase_threshold(self):
        self.threshold_value += 2
        self.update_frame()

    # Decrease focus peaking threshold
    def decrease_threshold(self):
        if self.threshold_value > 5:
            self.threshold_value -= 5
        self.update_frame()

    # Change the color used for focus peaking
    def change_focus_peaking_color(self, index):
        colors = [(255, 0, 0), (0, 0, 255), (0, 255, 0)]
        self.focus_peaking_color = colors[index]
        self.update_frame()

    # Apply focus peaking effect to the frame
    def apply_focus_peaking(self, frame):
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray_frame, cv2.CV_64F)
        laplacian = np.uint8(np.absolute(laplacian))
        _, binary_threshold = cv2.threshold(laplacian, self.threshold_value, 255, cv2.THRESH_BINARY)
        color_outline = frame.copy()
        color_outline[binary_threshold != 0] = self.focus_peaking_color
        # Swap red and blue channels to fix color inversion
        color_outline[:, :, [0, 2]] = color_outline[:, :, [2, 0]]
        return color_outline

    # Start or stop video recording
    def toggle_recording(self, checked):
        if checked:
            self.start_recording()
        else:
            self.stop_recording()

    # Start recording video
    def start_recording(self):
        self.output_path = self.generate_video_path()
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.out = cv2.VideoWriter(self.output_path, fourcc, 29.97, (int(self.vid.width), int(self.vid.height)))
        self.recording = True

    # Stop recording video
    def stop_recording(self):
        if self.recording:
            self.recording = False
            self.out.release()
            self.video_counter += 1
            self.output_path = self.generate_video_path()

    # Display the frame on the video label
    def display_frame(self, frame):
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Resize the frame while maintaining aspect ratio
        aspect_ratio = frame.shape[1] / frame.shape[0]  # width / height
        target_width = self.video_label.width()
        target_height = int(target_width / aspect_ratio)
        resized_frame = cv2.resize(frame, (target_width, target_height))

        h, w, ch = resized_frame.shape
        bytes_per_line = ch * w
        q_img = QImage(resized_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        self.video_label.setPixmap(pixmap)


# Class for video capture and management
class MyVideoCapture:
    def __init__(self, video_source=0):
        self.vid = cv2.VideoCapture(video_source)
        self.vid.set(cv2.CAP_PROP_BUFFERSIZE, 10)

        if not self.vid.isOpened():
            raise ValueError("Unable to open video source", video_source)

        self.width = int(self.vid.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.vid.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Change the video source
    def change_source(self, video_source):
        self.vid.release()
        self.vid = cv2.VideoCapture(video_source)
        if not self.vid.isOpened():
            raise ValueError("Unable to open video source", video_source)

    # Get the current frame from the video capture
    def get_frame(self):
        if self.vid.isOpened():
            ret, frame = self.vid.read()
            if ret:
                return ret, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return False, None

    # Release the video capture when the object is deleted
    def __del__(self):
        if self.vid.isOpened():
            self.vid.release()


# Entry point of the application
if __name__ == "__main__":
    app = QApplication([])
    window = App()
    app.exit(app.exec_())
