from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QFont, QLinearGradient

class TankSplashScreen(QWidget):
    """
    A custom splash screen featuring an animation of tanks filling up.
    """
    loading_complete = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Dimensions
        self.setFixedSize(400, 300)
        
        # Animation state
        self.fill_level = 0.0  # 0.0 to 1.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(30)  # Update every 30ms
        
        # Colors
        self.tank_border_color = QColor("#2c3e50")
        self.liquid_color_start = QColor("#3498db")
        self.liquid_color_end = QColor("#2980b9")
        self.bg_color = QColor("#ffffff")
        
    def update_animation(self):
        """Increments the fill level."""
        self.fill_level += 0.01
        
        if self.fill_level >= 1.0:
            self.fill_level = 1.0
            self.timer.stop()
            # Hold for a moment then finish
            QTimer.singleShot(500, self.loading_complete.emit)
            QTimer.singleShot(500, self.close)
            
        self.update()  # Trigger paintEvent

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Draw Background (Rounded Card)
        painter.setBrush(QBrush(self.bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 15, 15)

        # 2. Draw Title
        painter.setPen(QColor("#2c3e50"))
        font = QFont("Segoe UI", 24, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(0, 30, 400, 50), Qt.AlignmentFlag.AlignCenter, "UllageMaster")
        
        sub_font = QFont("Segoe UI", 10)
        painter.setFont(sub_font)
        painter.setPen(QColor("#7f8c8d"))
        painter.drawText(QRectF(0, 70, 400, 20), Qt.AlignmentFlag.AlignCenter, "Loading Modules...")

        # 3. Draw Tanks
        tank_width = 60
        tank_height = 120
        spacing = 20
        start_x = (400 - (3 * tank_width + 2 * spacing)) / 2
        start_y = 120
        
        for i in range(3):
            x = start_x + i * (tank_width + spacing)
            y = start_y
            
            # Draw Tank Outline
            painter.setPen(QPen(self.tank_border_color, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(int(x), int(y), int(tank_width), int(tank_height))
            
            # Calculate Liquid Height based on animation + slight offset for "wave" effect
            # We stagger the fill slightly for visual interest
            local_fill = max(0.0, min(1.0, self.fill_level * (1.0 + i * 0.1) - (i * 0.1)))
            
            current_liquid_height = tank_height * local_fill
            
            if current_liquid_height > 0:
                # Gradient for liquid
                gradient = QLinearGradient(x, y + tank_height, x, y + tank_height - current_liquid_height)
                gradient.setColorAt(0, self.liquid_color_end)
                gradient.setColorAt(1, self.liquid_color_start)
                
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(gradient))
                painter.drawRect(
                    int(x + 1), 
                    int(y + tank_height - current_liquid_height), 
                    int(tank_width - 2), 
                    int(current_liquid_height)
                )
                
                # Draw "Ullage" line at the top of the liquid
                painter.setPen(QPen(QColor("white"), 1, Qt.PenStyle.DashLine))
                painter.drawLine(
                    int(x + 2), 
                    int(y + tank_height - current_liquid_height), 
                    int(x + tank_width - 2), 
                    int(y + tank_height - current_liquid_height)
                )

        # 4. Draw Loading Text / Percentage
        painter.setPen(QColor("#34495e"))
        painter.setFont(QFont("Monospace", 9))
        pct = int(self.fill_level * 100)
        painter.drawText(QRectF(0, 260, 400, 30), Qt.AlignmentFlag.AlignCenter, f"Initializing... {pct}%")
