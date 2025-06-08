import sys
import time
import subprocess
import re
import serial
import socket
import threading
import json
import os
from datetime import datetime, timedelta
from PyQt6 import uic
from PyQt6.QtWidgets import (QMainWindow, QApplication, QVBoxLayout, QRadioButton, 
                            QLabel, QTimeEdit, QListWidget, QPushButton, QWidget,
                            QGroupBox, QHBoxLayout, QComboBox, QSpinBox, QCheckBox,
                            QTextEdit, QMessageBox, QProgressBar, QGridLayout,
                            QTabWidget, QTableWidget, QTableWidgetItem, QLineEdit,
                            QFileDialog, QDialog, QDialogButtonBox)
from PyQt6.QtCore import QThread, pyqtSignal, QTime, QTimer, Qt, QDateTime, QSettings
from PyQt6.QtGui import QPixmap, QFont, QPalette, QColor, QIcon

# Thread สำหรับการเชื่อมต่อ WiFi
class WiFiConnection(QThread):
    status_update = pyqtSignal(str)
    connection_result = pyqtSignal(bool, str)
    
    def __init__(self, ip, port=80):
        super().__init__()
        self.ip = ip
        self.port = port
        self.socket = None
        
    def run(self):
        try:
            self.status_update.emit("Connecting to ESP32...")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.ip, self.port))
            self.connection_result.emit(True, f"Connected to {self.ip}:{self.port}")
        except Exception as e:
            self.connection_result.emit(False, f"Connection failed: {str(e)}")

# Thread สำหรับ Monitor Serial/WiFi
class DeviceMonitor(QThread):
    data_received = pyqtSignal(str)
    
    def __init__(self, device):
        super().__init__()
        self.device = device
        self.running = False
        
    def run(self):
        self.running = True
        while self.running:
            try:
                if isinstance(self.device, serial.Serial):
                    if self.device.in_waiting:
                        data = self.device.readline().decode('utf-8').strip()
                        if data:
                            self.data_received.emit(data)
                elif isinstance(self.device, socket.socket):
                    self.device.settimeout(0.1)
                    try:
                        data = self.device.recv(1024).decode('utf-8').strip()
                        if data:
                            self.data_received.emit(data)
                    except socket.timeout:
                        pass
            except Exception as e:
                print(f"Monitor error: {e}")
            time.sleep(0.1)
            
    def stop(self):
        self.running = False

# Dialog สำหรับตั้งค่าการเชื่อมต่อ
class ConnectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connection Settings")
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # Connection Type
        type_group = QGroupBox("Connection Type")
        type_layout = QHBoxLayout()
        self.serial_radio = QRadioButton("Serial (USB)")
        self.wifi_radio = QRadioButton("WiFi")
        self.serial_radio.setChecked(True)
        type_layout.addWidget(self.serial_radio)
        type_layout.addWidget(self.wifi_radio)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # Serial Settings
        self.serial_group = QGroupBox("Serial Settings")
        serial_layout = QGridLayout()
        serial_layout.addWidget(QLabel("Port:"), 0, 0)
        self.port_combo = QComboBox()
        self.refresh_ports()
        serial_layout.addWidget(self.port_combo, 0, 1)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_ports)
        serial_layout.addWidget(self.refresh_btn, 0, 2)
        
        serial_layout.addWidget(QLabel("Baudrate:"), 1, 0)
        self.baudrate_combo = QComboBox()
        self.baudrate_combo.addItems(['9600', '19200', '38400', '57600', '115200'])
        self.baudrate_combo.setCurrentText('9600')
        serial_layout.addWidget(self.baudrate_combo, 1, 1)
        
        self.serial_group.setLayout(serial_layout)
        layout.addWidget(self.serial_group)
        
        # WiFi Settings
        self.wifi_group = QGroupBox("WiFi Settings")
        wifi_layout = QGridLayout()
        wifi_layout.addWidget(QLabel("IP Address:"), 0, 0)
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("192.168.1.100")
        wifi_layout.addWidget(self.ip_input, 0, 1)
        
        wifi_layout.addWidget(QLabel("Port:"), 1, 0)
        self.port_input = QLineEdit()
        self.port_input.setText("80")
        wifi_layout.addWidget(self.port_input, 1, 1)
        
        self.wifi_group.setLayout(wifi_layout)
        self.wifi_group.setEnabled(False)
        layout.addWidget(self.wifi_group)
        
        # Connect radio buttons
        self.serial_radio.toggled.connect(self.on_type_changed)
        self.wifi_radio.toggled.connect(self.on_type_changed)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | 
                                  QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
        
    def on_type_changed(self):
        self.serial_group.setEnabled(self.serial_radio.isChecked())
        self.wifi_group.setEnabled(self.wifi_radio.isChecked())
        
    def refresh_ports(self):
        self.port_combo.clear()
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        else:
            ports = ['/dev/ttyUSB%s' % i for i in range(10)]
            ports += ['/dev/ttyACM%s' % i for i in range(10)]
            
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                self.port_combo.addItem(port)
            except:
                pass
                
        if self.port_combo.count() == 0:
            self.port_combo.addItem("No ports found")
            
    def get_connection_info(self):
        if self.serial_radio.isChecked():
            return {
                'type': 'serial',
                'port': self.port_combo.currentText(),
                'baudrate': int(self.baudrate_combo.currentText())
            }
        else:
            return {
                'type': 'wifi',
                'ip': self.ip_input.text(),
                'port': int(self.port_input.text())
            }

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Smart Irrigation Control System')
        self.setGeometry(100, 100, 1000, 700)
        
        # Settings
        self.settings = QSettings('SmartIrrigation', 'Settings')
        
        # Device connection
        self.device = None
        self.device_monitor = None
        self.connection_type = None
        
        # System state
        self.is_running = False
        self.auto_mode_enabled = True
        self.schedules = []
        self.watering_log = []
        
        # Create main UI
        self.setup_ui()
        
        # Timers
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        
        self.auto_timer = QTimer()
        self.auto_timer.timeout.connect(self.check_schedules)
        self.auto_timer.start(1000)
        
        # Progress timer for manual watering
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.update_progress)
        
        # Load saved settings
        self.load_settings()
        
    def setup_ui(self):
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Top toolbar
        toolbar_layout = QHBoxLayout()
        
        # Connection status
        self.connection_label = QLabel("⚡ Disconnected")
        self.connection_label.setStyleSheet("""
            QLabel {
                padding: 5px;
                border-radius: 5px;
                background-color: #ffcccc;
                font-weight: bold;
            }
        """)
        toolbar_layout.addWidget(self.connection_label)
        
        # Connect button
        self.connect_btn = QPushButton("🔌 Connect")
        self.connect_btn.clicked.connect(self.show_connection_dialog)
        toolbar_layout.addWidget(self.connect_btn)
        
        # Current time
        self.time_label = QLabel()
        self.time_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        toolbar_layout.addWidget(self.time_label)
        
        toolbar_layout.addStretch()
        
        # System status
        self.system_status = QLabel("System: Idle")
        self.system_status.setStyleSheet("""
            QLabel {
                padding: 5px;
                border-radius: 5px;
                background-color: #e0e0e0;
                font-weight: bold;
            }
        """)
        toolbar_layout.addWidget(self.system_status)
        
        main_layout.addLayout(toolbar_layout)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background: white;
            }
            QTabBar::tab {
                padding: 8px 15px;
                margin: 2px;
            }
            QTabBar::tab:selected {
                background: #4CAF50;
                color: white;
            }
        """)
        
        # Manual Control Tab
        manual_tab = self.create_manual_tab()
        self.tab_widget.addTab(manual_tab, "🚿 Manual Control")
        
        # Auto Schedule Tab
        auto_tab = self.create_auto_tab()
        self.tab_widget.addTab(auto_tab, "⏰ Auto Schedule")
        
        # History Tab
        history_tab = self.create_history_tab()
        self.tab_widget.addTab(history_tab, "📊 History")
        
        # Settings Tab
        settings_tab = self.create_settings_tab()
        self.tab_widget.addTab(settings_tab, "⚙️ Settings")
        
        main_layout.addWidget(self.tab_widget)
        
        # Status bar
        self.status_bar = self.statusBar()
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setMaximumHeight(100)
        self.status_bar.addPermanentWidget(self.log_display, 1)
        
    def create_manual_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Mode selection
        mode_group = QGroupBox("Watering Mode")
        mode_layout = QHBoxLayout()
        
        self.water_radio = QRadioButton("💧 Water Only")
        self.water_radio.setChecked(True)
        self.fertilizer_radio = QRadioButton("🌱 Water + Fertilizer")
        
        mode_layout.addWidget(self.water_radio)
        mode_layout.addWidget(self.fertilizer_radio)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # Duration setting
        duration_group = QGroupBox("Duration Settings")
        duration_layout = QGridLayout()
        
        duration_layout.addWidget(QLabel("Duration (minutes):"), 0, 0)
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 120)
        self.duration_spin.setValue(10)
        self.duration_spin.setSuffix(" min")
        duration_layout.addWidget(self.duration_spin, 0, 1)
        
        duration_layout.addWidget(QLabel("Water Amount:"), 1, 0)
        self.water_amount_label = QLabel("~10 Liters")
        duration_layout.addWidget(self.water_amount_label, 1, 1)
        
        # Update water amount when duration changes
        self.duration_spin.valueChanged.connect(
            lambda v: self.water_amount_label.setText(f"~{v} Liters")
        )
        
        duration_group.setLayout(duration_layout)
        layout.addWidget(duration_group)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶️ Start Watering")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 15px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.start_btn.clicked.connect(self.start_manual_watering)
        
        self.stop_btn = QPushButton("⏹️ Stop")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 15px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_watering)
        self.stop_btn.setEnabled(False)
        
        self.test_btn = QPushButton("🔧 Test System")
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 15px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        self.test_btn.clicked.connect(self.test_system)
        
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addWidget(self.test_btn)
        
        layout.addLayout(control_layout)
        
        # Progress display
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()
        
        self.progress_label = QLabel("Ready")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        progress_layout.addWidget(self.progress_bar)
        
        self.time_remaining_label = QLabel("")
        self.time_remaining_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self.time_remaining_label)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
        
    def create_auto_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Schedule input
        input_group = QGroupBox("Add New Schedule")
        input_layout = QGridLayout()
        
        # Time settings
        input_layout.addWidget(QLabel("Start Time:"), 0, 0)
        self.start_time = QTimeEdit()
        self.start_time.setDisplayFormat("HH:mm")
        self.start_time.setTime(QTime(8, 0))
        input_layout.addWidget(self.start_time, 0, 1)
        
        input_layout.addWidget(QLabel("Duration:"), 0, 2)
        self.schedule_duration = QSpinBox()
        self.schedule_duration.setRange(1, 120)
        self.schedule_duration.setValue(10)
        self.schedule_duration.setSuffix(" min")
        input_layout.addWidget(self.schedule_duration, 0, 3)
        
        # Days selection
        input_layout.addWidget(QLabel("Days:"), 1, 0)
        days_widget = QWidget()
        days_layout = QHBoxLayout()
        days_layout.setContentsMargins(0, 0, 0, 0)
        
        self.day_checkboxes = {}
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        for day in days:
            cb = QCheckBox(day)
            self.day_checkboxes[day] = cb
            days_layout.addWidget(cb)
        
        days_widget.setLayout(days_layout)
        input_layout.addWidget(days_widget, 1, 1, 1, 3)
        
        # Mode selection
        input_layout.addWidget(QLabel("Mode:"), 2, 0)
        self.schedule_mode = QComboBox()
        self.schedule_mode.addItems(['💧 Water Only', '🌱 Water + Fertilizer'])
        input_layout.addWidget(self.schedule_mode, 2, 1)
        
        # Repeat option
        self.repeat_checkbox = QCheckBox("Repeat every week")
        self.repeat_checkbox.setChecked(True)
        input_layout.addWidget(self.repeat_checkbox, 2, 2, 1, 2)
        
        # Add button
        self.add_schedule_btn = QPushButton("➕ Add Schedule")
        self.add_schedule_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                font-weight: bold;
                border-radius: 5px;
            }
        """)
        self.add_schedule_btn.clicked.connect(self.add_schedule)
        input_layout.addWidget(self.add_schedule_btn, 3, 0, 1, 4)
        
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # Schedule list
        list_group = QGroupBox("Active Schedules")
        list_layout = QVBoxLayout()
        
        # Enable/Disable auto mode
        auto_control_layout = QHBoxLayout()
        self.auto_enable_checkbox = QCheckBox("Enable Auto Mode")
        self.auto_enable_checkbox.setChecked(True)
        self.auto_enable_checkbox.stateChanged.connect(self.toggle_auto_mode)
        auto_control_layout.addWidget(self.auto_enable_checkbox)
        
        self.clear_all_btn = QPushButton("Clear All")
        self.clear_all_btn.clicked.connect(self.clear_all_schedules)
        auto_control_layout.addWidget(self.clear_all_btn)
        auto_control_layout.addStretch()
        
        list_layout.addLayout(auto_control_layout)
        
        # Schedule table
        self.schedule_table = QTableWidget()
        self.schedule_table.setColumnCount(5)
        self.schedule_table.setHorizontalHeaderLabels(['Time', 'Duration', 'Days', 'Mode', 'Actions'])
        self.schedule_table.horizontalHeader().setStretchLastSection(True)
        list_layout.addWidget(self.schedule_table)
        
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        widget.setLayout(layout)
        return widget
        
    def create_history_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Controls
        control_layout = QHBoxLayout()
        
        self.history_filter = QComboBox()
        self.history_filter.addItems(['All', 'Today', 'This Week', 'This Month'])
        self.history_filter.currentTextChanged.connect(self.filter_history)
        control_layout.addWidget(QLabel("Filter:"))
        control_layout.addWidget(self.history_filter)
        
        control_layout.addStretch()
        
        self.export_btn = QPushButton("📥 Export to CSV")
        self.export_btn.clicked.connect(self.export_history)
        control_layout.addWidget(self.export_btn)
        
        self.clear_history_btn = QPushButton("🗑️ Clear History")
        self.clear_history_btn.clicked.connect(self.clear_history)
        control_layout.addWidget(self.clear_history_btn)
        
        layout.addLayout(control_layout)
        
        # History table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(['Date & Time', 'Mode', 'Duration', 'Status', 'Notes'])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.history_table)
        
        # Statistics
        stats_group = QGroupBox("Statistics")
        stats_layout = QGridLayout()
        
        self.total_water_label = QLabel("Total Water Used: 0 L")
        self.total_sessions_label = QLabel("Total Sessions: 0")
        self.avg_duration_label = QLabel("Average Duration: 0 min")
        
        stats_layout.addWidget(self.total_water_label, 0, 0)
        stats_layout.addWidget(self.total_sessions_label, 0, 1)
        stats_layout.addWidget(self.avg_duration_label, 0, 2)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        widget.setLayout(layout)
        return widget
        
    def create_settings_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # General Settings
        general_group = QGroupBox("General Settings")
        general_layout = QGridLayout()
        
        general_layout.addWidget(QLabel("Flow Rate (L/min):"), 0, 0)
        self.flow_rate_spin = QSpinBox()
        self.flow_rate_spin.setRange(1, 20)
        self.flow_rate_spin.setValue(1)
        general_layout.addWidget(self.flow_rate_spin, 0, 1)
        
        general_layout.addWidget(QLabel("Default Duration:"), 1, 0)
        self.default_duration_spin = QSpinBox()
        self.default_duration_spin.setRange(1, 60)
        self.default_duration_spin.setValue(10)
        self.default_duration_spin.setSuffix(" min")
        general_layout.addWidget(self.default_duration_spin, 1, 1)
        
        self.sound_alert_checkbox = QCheckBox("Enable sound alerts")
        self.sound_alert_checkbox.setChecked(True)
        general_layout.addWidget(self.sound_alert_checkbox, 2, 0, 1, 2)
        
        general_group.setLayout(general_layout)
        layout.addWidget(general_group)
        
        # Safety Settings
        safety_group = QGroupBox("Safety Settings")
        safety_layout = QGridLayout()
        
        safety_layout.addWidget(QLabel("Max Duration:"), 0, 0)
        self.max_duration_spin = QSpinBox()
        self.max_duration_spin.setRange(10, 180)
        self.max_duration_spin.setValue(60)
        self.max_duration_spin.setSuffix(" min")
        safety_layout.addWidget(self.max_duration_spin, 0, 1)
        
        self.auto_stop_checkbox = QCheckBox("Auto stop on disconnect")
        self.auto_stop_checkbox.setChecked(True)
        safety_layout.addWidget(self.auto_stop_checkbox, 1, 0, 1, 2)
        
        safety_group.setLayout(safety_layout)
        layout.addWidget(safety_group)
        
        # Save button
        self.save_settings_btn = QPushButton("💾 Save Settings")
        self.save_settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                font-weight: bold;
                border-radius: 5px;
            }
        """)
        self.save_settings_btn.clicked.connect(self.save_settings)
        layout.addWidget(self.save_settings_btn)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
        
    def show_connection_dialog(self):
        dialog = ConnectionDialog(self)
        if dialog.exec():
            conn_info = dialog.get_connection_info()
            self.connect_device(conn_info)
            
    def connect_device(self, conn_info):
        # Disconnect if already connected
        if self.device:
            self.disconnect_device()
            
        try:
            if conn_info['type'] == 'serial':
                self.device = serial.Serial(
                    port=conn_info['port'],
                    baudrate=conn_info['baudrate'],
                    timeout=1
                )
                self.connection_type = 'serial'
                self.on_connection_success(f"Serial: {conn_info['port']}")
                
            else:  # WiFi
                self.wifi_thread = WiFiConnection(conn_info['ip'], conn_info['port'])
                self.wifi_thread.status_update.connect(self.log_message)
                self.wifi_thread.connection_result.connect(self.on_wifi_connection_result)
                self.wifi_thread.start()
                
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", str(e))
            
    def on_wifi_connection_result(self, success, message):
        if success:
            self.device = self.wifi_thread.socket
            self.connection_type = 'wifi'
            self.on_connection_success(message)
        else:
            QMessageBox.critical(self, "Connection Error", message)
            
    def on_connection_success(self, info):
        self.connection_label.setText(f"⚡ {info}")
        self.connection_label.setStyleSheet("""
            QLabel {
                padding: 5px;
                border-radius: 5px;
                background-color: #ccffcc;
                font-weight: bold;
            }
        """)
        self.connect_btn.setText("🔌 Disconnect")
        self.log_message(f"Connected: {info}")
        
        # Start device monitor
        self.device_monitor = DeviceMonitor(self.device)
        self.device_monitor.data_received.connect(self.on_device_data)
        self.device_monitor.start()
        
    def disconnect_device(self):
        if self.device_monitor:
            self.device_monitor.stop()
            self.device_monitor.wait()
            self.device_monitor = None
            
        if self.device:
            if isinstance(self.device, serial.Serial):
                self.device.close()
            elif isinstance(self.device, socket.socket):
                self.device.close()
            self.device = None
            
        self.connection_label.setText("⚡ Disconnected")
        self.connection_label.setStyleSheet("""
            QLabel {
                padding: 5px;
                border-radius: 5px;
                background-color: #ffcccc;
                font-weight: bold;
            }
        """)
        self.connect_btn.setText("🔌 Connect")
        self.log_message("Disconnected")
        
    def send_command(self, command):
        if not self.device:
            self.log_message("Error: Not connected to device", "error")
            return False
            
        try:
            if isinstance(self.device, serial.Serial):
                self.device.write((command + '\n').encode('utf-8'))
            else:  # Socket
                self.device.send((command + '\n').encode('utf-8'))
            self.log_message(f"Sent: {command}")
            return True
        except Exception as e:
            self.log_message(f"Send error: {e}", "error")
            return False
            
    def on_device_data(self, data):
        self.log_message(f"Received: {data}")
        
    def start_manual_watering(self):
        if not self.device:
            QMessageBox.warning(self, "Warning", "Please connect to device first")
            return
            
        mode = "Water Only" if self.water_radio.isChecked() else "Water + Fertilizer"
        duration = self.duration_spin.value()
        
        # Send appropriate command
        if self.water_radio.isChecked():
            success = self.send_command("LED1_ON")
        else:
            success = self.send_command("LED2_ON")
            
        if success:
            self.is_running = True
            self.watering_start_time = time.time()
            self.watering_duration = duration * 60  # Convert to seconds
            
            # Update UI
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.test_btn.setEnabled(False)
            self.system_status.setText(f"System: {mode}")
            self.system_status.setStyleSheet("""
                QLabel {
                    padding: 5px;
                    border-radius: 5px;
                    background-color: #ccffcc;
                    font-weight: bold;
                    color: green;
                }
            """)
            
            # Start progress timer
            self.progress_timer.start(100)  # Update every 100ms
            
            # Add to history
            self.add_to_history(mode, duration, "Manual", "Started")
            
            self.log_message(f"Started {mode} for {duration} minutes")
            
    def stop_watering(self):
        success = self.send_command("STOP")
        
        if success:
            self.is_running = False
            
            # Calculate actual duration
            if hasattr(self, 'watering_start_time'):
                actual_duration = int((time.time() - self.watering_start_time) / 60)
                self.log_message(f"Stopped after {actual_duration} minutes")
            
            # Update UI
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.test_btn.setEnabled(True)
            self.system_status.setText("System: Idle")
            self.system_status.setStyleSheet("""
                QLabel {
                    padding: 5px;
                    border-radius: 5px;
                    background-color: #e0e0e0;
                    font-weight: bold;
                }
            """)
            
            # Stop progress timer
            self.progress_timer.stop()
            self.progress_bar.setValue(0)
            self.progress_label.setText("Ready")
            self.time_remaining_label.setText("")
            
    def test_system(self):
        if not self.device:
            QMessageBox.warning(self, "Warning", "Please connect to device first")
            return
            
        reply = QMessageBox.question(self, "Test System", 
                                   "This will briefly activate all components.\nContinue?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.log_message("Testing water valve...")
            self.send_command("LED1_ON")
            QTimer.singleShot(2000, lambda: self.send_command("STOP"))
            
            QTimer.singleShot(3000, lambda: self.log_message("Testing fertilizer valve..."))
            QTimer.singleShot(3000, lambda: self.send_command("LED2_ON"))
            QTimer.singleShot(5000, lambda: self.send_command("STOP"))
            
            QTimer.singleShot(6000, lambda: self.log_message("Test complete"))
            
    def update_progress(self):
        if not self.is_running:
            return
            
        elapsed = time.time() - self.watering_start_time
        progress = min(100, int((elapsed / self.watering_duration) * 100))
        
        self.progress_bar.setValue(progress)
        
        # Update labels
        elapsed_min = int(elapsed / 60)
        elapsed_sec = int(elapsed % 60)
        self.progress_label.setText(f"Elapsed: {elapsed_min:02d}:{elapsed_sec:02d}")
        
        remaining = max(0, self.watering_duration - elapsed)
        remaining_min = int(remaining / 60)
        remaining_sec = int(remaining % 60)
        self.time_remaining_label.setText(f"Remaining: {remaining_min:02d}:{remaining_sec:02d}")
        
        # Auto stop when complete
        if progress >= 100:
            self.stop_watering()
            self.log_message("Watering completed")
            
    def add_schedule(self):
        # Get selected days
        selected_days = [day for day, cb in self.day_checkboxes.items() if cb.isChecked()]
        
        if not selected_days:
            QMessageBox.warning(self, "Warning", "Please select at least one day")
            return
            
        schedule = {
            'time': self.start_time.time().toString("HH:mm"),
            'duration': self.schedule_duration.value(),
            'days': selected_days,
            'mode': self.schedule_mode.currentText(),
            'repeat': self.repeat_checkbox.isChecked(),
            'active': True
        }
        
        self.schedules.append(schedule)
        self.update_schedule_table()
        
        # Clear selections
        for cb in self.day_checkboxes.values():
            cb.setChecked(False)
            
        self.log_message(f"Added schedule: {schedule['time']} on {', '.join(selected_days)}")
        
    def update_schedule_table(self):
        self.schedule_table.setRowCount(len(self.schedules))
        
        for i, schedule in enumerate(self.schedules):
            self.schedule_table.setItem(i, 0, QTableWidgetItem(schedule['time']))
            self.schedule_table.setItem(i, 1, QTableWidgetItem(f"{schedule['duration']} min"))
            self.schedule_table.setItem(i, 2, QTableWidgetItem(', '.join(schedule['days'])))
            self.schedule_table.setItem(i, 3, QTableWidgetItem(schedule['mode']))
            
            # Action buttons
            action_widget = QWidget()
            action_layout = QHBoxLayout()
            action_layout.setContentsMargins(0, 0, 0, 0)
            
            toggle_btn = QPushButton("Disable" if schedule['active'] else "Enable")
            toggle_btn.clicked.connect(lambda checked, idx=i: self.toggle_schedule(idx))
            
            delete_btn = QPushButton("Delete")
            delete_btn.clicked.connect(lambda checked, idx=i: self.delete_schedule(idx))
            
            action_layout.addWidget(toggle_btn)
            action_layout.addWidget(delete_btn)
            action_widget.setLayout(action_layout)
            
            self.schedule_table.setCellWidget(i, 4, action_widget)
            
    def toggle_schedule(self, index):
        self.schedules[index]['active'] = not self.schedules[index]['active']
        self.update_schedule_table()
        
    def delete_schedule(self, index):
        del self.schedules[index]
        self.update_schedule_table()
        
    def clear_all_schedules(self):
        reply = QMessageBox.question(self, "Clear All", 
                                   "Delete all schedules?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.schedules.clear()
            self.update_schedule_table()
            
    def toggle_auto_mode(self, state):
        self.auto_mode_enabled = state == 2  # Qt.CheckState.Checked = 2
        status = "enabled" if self.auto_mode_enabled else "disabled"
        self.log_message(f"Auto mode {status}")
        
    def check_schedules(self):
        if not self.auto_mode_enabled or self.is_running or not self.device:
            return
            
        current_time = QTime.currentTime()
        current_day = datetime.now().strftime('%a')
        
        for schedule in self.schedules:
            if not schedule['active']:
                continue
                
            if current_day not in schedule['days']:
                continue
                
            schedule_time = QTime.fromString(schedule['time'], "HH:mm")
            
            # Check if it's time to start (within 1 minute window)
            if (schedule_time.secsTo(current_time) >= 0 and 
                schedule_time.secsTo(current_time) < 60):
                
                # Check if not already started
                if not hasattr(self, 'last_auto_start') or \
                   time.time() - self.last_auto_start > 120:
                    
                    self.last_auto_start = time.time()
                    self.start_auto_watering(schedule)
                    
    def start_auto_watering(self, schedule):
        self.log_message(f"Auto schedule triggered: {schedule['time']}")
        
        # Set mode
        if "Water Only" in schedule['mode']:
            self.water_radio.setChecked(True)
        else:
            self.fertilizer_radio.setChecked(True)
            
        # Set duration
        self.duration_spin.setValue(schedule['duration'])
        
        # Start watering
        self.start_manual_watering()
        
        # Update history to show it was auto-triggered
        if self.watering_log:
            self.watering_log[-1]['notes'] = "Auto Schedule"
            
    def add_to_history(self, mode, duration, trigger, status):
        entry = {
            'datetime': datetime.now(),
            'mode': mode,
            'duration': duration,
            'trigger': trigger,
            'status': status,
            'notes': trigger
        }
        
        self.watering_log.append(entry)
        self.update_history_table()
        self.update_statistics()
        
    def update_history_table(self):
        # Filter history based on selection
        filter_text = self.history_filter.currentText()
        filtered_log = self.filter_watering_log(filter_text)
        
        self.history_table.setRowCount(len(filtered_log))
        
        for i, entry in enumerate(filtered_log):
            dt_item = QTableWidgetItem(entry['datetime'].strftime("%Y-%m-%d %H:%M"))
            self.history_table.setItem(i, 0, dt_item)
            self.history_table.setItem(i, 1, QTableWidgetItem(entry['mode']))
            self.history_table.setItem(i, 2, QTableWidgetItem(f"{entry['duration']} min"))
            self.history_table.setItem(i, 3, QTableWidgetItem(entry['status']))
            self.history_table.setItem(i, 4, QTableWidgetItem(entry['notes']))
            
    def filter_watering_log(self, filter_text):
        if filter_text == 'All':
            return self.watering_log
            
        now = datetime.now()
        
        if filter_text == 'Today':
            return [e for e in self.watering_log 
                   if e['datetime'].date() == now.date()]
        elif filter_text == 'This Week':
            week_start = now - timedelta(days=now.weekday())
            return [e for e in self.watering_log 
                   if e['datetime'].date() >= week_start.date()]
        elif filter_text == 'This Month':
            return [e for e in self.watering_log 
                   if e['datetime'].month == now.month and 
                      e['datetime'].year == now.year]
                      
        return self.watering_log
        
    def filter_history(self):
        self.update_history_table()
        
    def update_statistics(self):
        if not self.watering_log:
            return
            
        total_sessions = len(self.watering_log)
        total_duration = sum(e['duration'] for e in self.watering_log)
        total_water = total_duration * self.flow_rate_spin.value()
        avg_duration = total_duration / total_sessions if total_sessions > 0 else 0
        
        self.total_water_label.setText(f"Total Water Used: {total_water} L")
        self.total_sessions_label.setText(f"Total Sessions: {total_sessions}")
        self.avg_duration_label.setText(f"Average Duration: {avg_duration:.1f} min")
        
    def export_history(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export History", 
            f"irrigation_history_{datetime.now().strftime('%Y%m%d')}.csv",
            "CSV Files (*.csv)"
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write("Date,Time,Mode,Duration,Status,Notes\n")
                    for entry in self.watering_log:
                        f.write(f"{entry['datetime'].strftime('%Y-%m-%d')},"
                               f"{entry['datetime'].strftime('%H:%M')},"
                               f"{entry['mode']},"
                               f"{entry['duration']},"
                               f"{entry['status']},"
                               f"{entry['notes']}\n")
                               
                QMessageBox.information(self, "Success", f"History exported to {filename}")
                self.log_message(f"History exported to {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed: {e}")
                
    def clear_history(self):
        reply = QMessageBox.question(self, "Clear History", 
                                   "Delete all history records?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.watering_log.clear()
            self.update_history_table()
            self.update_statistics()
            
    def update_clock(self):
        current = QDateTime.currentDateTime()
        self.time_label.setText(current.toString("yyyy-MM-dd HH:mm:ss"))
        
    def log_message(self, message, level="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if level == "error":
            formatted = f'<span style="color: red;">[{timestamp}] {message}</span>'
        elif level == "warning":
            formatted = f'<span style="color: orange;">[{timestamp}] {message}</span>'
        else:
            formatted = f'[{timestamp}] {message}'
            
        self.log_display.append(formatted)
        
        # Auto scroll
        scrollbar = self.log_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def save_settings(self):
        self.settings.setValue('flow_rate', self.flow_rate_spin.value())
        self.settings.setValue('default_duration', self.default_duration_spin.value())
        self.settings.setValue('max_duration', self.max_duration_spin.value())
        self.settings.setValue('sound_alert', self.sound_alert_checkbox.isChecked())
        self.settings.setValue('auto_stop', self.auto_stop_checkbox.isChecked())
        self.settings.setValue('schedules', json.dumps(self.schedules))
        
        QMessageBox.information(self, "Success", "Settings saved successfully")
        self.log_message("Settings saved")
        
    def load_settings(self):
        self.flow_rate_spin.setValue(self.settings.value('flow_rate', 1, type=int))
        self.default_duration_spin.setValue(self.settings.value('default_duration', 10, type=int))
        self.max_duration_spin.setValue(self.settings.value('max_duration', 60, type=int))
        self.sound_alert_checkbox.setChecked(self.settings.value('sound_alert', True, type=bool))
        self.auto_stop_checkbox.setChecked(self.settings.value('auto_stop', True, type=bool))
        
        # Load schedules
        schedules_json = self.settings.value('schedules', '[]')
        try:
            self.schedules = json.loads(schedules_json)
            self.update_schedule_table()
        except:
            self.schedules = []
            
        # Set default duration
        self.duration_spin.setValue(self.default_duration_spin.value())
        
    def closeEvent(self, event):
        if self.is_running:
            reply = QMessageBox.question(self, "Confirm Exit", 
                                       "System is running. Stop and exit?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_watering()
            else:
                event.ignore()
                return
                
        # Save current schedules
        self.settings.setValue('schedules', json.dumps(self.schedules))
        
        # Disconnect device
        if self.device:
            self.disconnect_device()
            
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())
