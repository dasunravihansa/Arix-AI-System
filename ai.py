import sys
import os
import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QPushButton, QScrollArea, QFrame,
    QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QThread, QObject
)
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QPalette, QKeyEvent
)

from groq import Groq


# ═══════════════════════════════════════════════════════════════
# Theme
# ═══════════════════════════════════════════════════════════════
class Theme:
    BG_PRIMARY     = "#0b0f19"
    BG_SECONDARY   = "#111827"
    BG_TERTIARY    = "#1c2333"
    BG_INPUT       = "#1a2234"
    ACCENT         = "#7C3AED"
    ACCENT_HOVER   = "#8B5CF6"
    ACCENT_GLOW    = "#6D28D9"
    GREEN          = "#10B981"
    CYAN           = "#06B6D4"
    TEXT_PRIMARY   = "#E6EDF3"
    TEXT_SECONDARY = "#8B949E"
    TEXT_MUTED     = "#484F58"
    BORDER         = "#1e293b"
    BORDER_FOCUS   = "#7C3AED"
    USER_BUBBLE    = "#1e1b4b"
    AI_BUBBLE      = "#0f172a"
    SCROLLBAR      = "#2A2F3A"
    DANGER         = "#F85149"


# ═══════════════════════════════════════════════════════════════
# Animated Typing Indicator (3 pulsing dots)
# ═══════════════════════════════════════════════════════════════
class TypingIndicator(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(44)
        self.dots = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(350)

    def _tick(self):
        self.dots = (self.dots + 1) % 4
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw "AI is thinking" label
        painter.setPen(QColor(Theme.TEXT_MUTED))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(52, 22, "Arix AI is thinking")

        # Draw animated dots
        for i in range(3):
            if i < self.dots:
                painter.setBrush(QColor(124, 58, 237, 240))
            else:
                painter.setBrush(QColor(124, 58, 237, 50))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(12 + i * 14, 14, 9, 9)

        painter.end()

    def stop(self):
        self.timer.stop()


# ═══════════════════════════════════════════════════════════════
# Chat Bubble (with avatar, name, timestamp, selectable text)
# ═══════════════════════════════════════════════════════════════
class ChatBubble(QFrame):
    def __init__(self, text, is_user, timestamp):
        super().__init__()
        self.setObjectName("bubble")

        if is_user:
            bg = Theme.USER_BUBBLE
            border_clr = "rgba(124, 58, 237, 0.35)"
            avatar_text, avatar_color = "You", Theme.ACCENT
            name = "You"
        else:
            bg = Theme.AI_BUBBLE
            border_clr = "rgba(6, 182, 212, 0.25)"
            avatar_text, avatar_color = "AI", Theme.CYAN
            name = "Arix AI"

        self.setStyleSheet(f"""
            QFrame#bubble {{
                background-color: {bg};
                border: 1px solid {border_clr};
                border-radius: 16px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 10)
        layout.setSpacing(6)

        # ── Header row: avatar + name + time ──
        header = QHBoxLayout()
        header.setSpacing(8)

        avatar = QLabel(avatar_text)
        avatar.setFixedSize(26, 26)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        avatar.setStyleSheet(f"""
            background-color: {avatar_color};
            color: white;
            border-radius: 13px;
            border: none;
        """)
        header.addWidget(avatar)

        name_lbl = QLabel(name)
        name_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        name_lbl.setStyleSheet(f"color: {Theme.TEXT_PRIMARY}; background: transparent; border: none;")
        header.addWidget(name_lbl)

        header.addStretch()

        time_lbl = QLabel(timestamp)
        time_lbl.setFont(QFont("Segoe UI", 8))
        time_lbl.setStyleSheet(f"color: {Theme.TEXT_MUTED}; background: transparent; border: none;")
        header.addWidget(time_lbl)

        layout.addLayout(header)

        # ── Message text (selectable) ──
        msg = QLabel(text)
        msg.setWordWrap(True)
        msg.setFont(QFont("Segoe UI", 11))
        msg.setStyleSheet(f"color: {Theme.TEXT_PRIMARY}; background: transparent; border: none; padding: 2px 0;")
        msg.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        layout.addWidget(msg)

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)


# ═══════════════════════════════════════════════════════════════
# Groq AI Worker (threaded)
# ═══════════════════════════════════════════════════════════════
class AIWorker(QObject):
    finished = pyqtSignal(str)

    def __init__(self, message):
        super().__init__()
        self.message = message
        self.client = Groq(api_key="Add Your Groq API Key")


    def run(self):
        try:
            res = self.client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Arix Super Market AI Assistant. "
                            "You help with product prices, stock, sales, and staff."
                        )
                    },
                    {"role": "user", "content": self.message}
                ],
                temperature=0.4,
                max_tokens=400
            )
            self.finished.emit(res.choices[0].message.content)
        except Exception as e:
            self.finished.emit(f"⚠️ AI Error:\n{e}")


# ═══════════════════════════════════════════════════════════════
# Chat Input (Enter = send, Shift+Enter = newline)
# ═══════════════════════════════════════════════════════════════
class ChatInput(QTextEdit):
    send = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setPlaceholderText("Message Arix AI...")
        self.setAcceptRichText(False)

    def keyPressEvent(self, e: QKeyEvent):
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if e.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(e)
            else:
                self.send.emit()
        else:
            super().keyPressEvent(e)


# ═══════════════════════════════════════════════════════════════
# Main Window
# ═══════════════════════════════════════════════════════════════
class ArixAI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Arix AI Assistant")
        self.setMinimumSize(780, 560)
        self.resize(920, 680)

        central = QWidget()
        self.setCentralWidget(central)
        central.setStyleSheet(f"background-color: {Theme.BG_PRIMARY};")

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ═══════════════════════════════════════════
        # Header Bar
        # ═══════════════════════════════════════════
        header = QFrame()
        header.setFixedHeight(66)
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.BG_SECONDARY};
                border-bottom: 1px solid {Theme.BORDER};
            }}
        """)

        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(22, 0, 22, 0)
        h_layout.setSpacing(14)

        # Gradient avatar icon
        ai_icon = QLabel("✦")
        ai_icon.setFixedSize(40, 40)
        ai_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ai_icon.setFont(QFont("Segoe UI", 17))
        ai_icon.setStyleSheet(f"""
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 {Theme.ACCENT}, stop:1 {Theme.CYAN}
            );
            color: white;
            border-radius: 20px;
        """)
        # Glow effect on avatar
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(24)
        glow.setColor(QColor(124, 58, 237, 100))
        glow.setOffset(0, 0)
        ai_icon.setGraphicsEffect(glow)
        h_layout.addWidget(ai_icon)

        # Title + status
        title_col = QVBoxLayout()
        title_col.setSpacing(1)

        title = QLabel("Arix AI Assistant")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {Theme.TEXT_PRIMARY}; background: transparent; border: none;")
        title_col.addWidget(title)

        status = QLabel("● Online — Powered by Groq")
        status.setFont(QFont("Segoe UI", 9))
        status.setStyleSheet(f"color: {Theme.GREEN}; background: transparent; border: none;")
        title_col.addWidget(status)

        h_layout.addLayout(title_col)
        h_layout.addStretch()

        # Clear chat button
        clear_btn = QPushButton("🗑  Clear")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setFont(QFont("Segoe UI", 9))
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {Theme.TEXT_SECONDARY};
                border: 1px solid {Theme.BORDER};
                border-radius: 10px;
                padding: 6px 16px;
            }}
            QPushButton:hover {{
                background-color: rgba(248, 81, 73, 0.1);
                color: {Theme.DANGER};
                border-color: {Theme.DANGER};
            }}
        """)
        clear_btn.clicked.connect(self._clear_chat)
        h_layout.addWidget(clear_btn)

        main_layout.addWidget(header)

        # ═══════════════════════════════════════════
        # Chat Scroll Area
        # ═══════════════════════════════════════════
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {Theme.BG_PRIMARY};
                border: none;
            }}
            QScrollBar:vertical {{
                background: {Theme.BG_PRIMARY};
                width: 8px;
            }}
            QScrollBar::handle:vertical {{
                background: {Theme.SCROLLBAR};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {Theme.TEXT_MUTED};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)

        self.chat_widget = QWidget()
        self.chat_widget.setStyleSheet(f"background-color: {Theme.BG_PRIMARY};")
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setContentsMargins(28, 20, 28, 20)
        self.chat_layout.setSpacing(14)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll.setWidget(self.chat_widget)
        main_layout.addWidget(self.scroll, 1)

        # ═══════════════════════════════════════════
        # Input Bar
        # ═══════════════════════════════════════════
        input_bar = QFrame()
        input_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.BG_SECONDARY};
                border-top: 1px solid {Theme.BORDER};
            }}
        """)

        input_layout = QHBoxLayout(input_bar)
        input_layout.setContentsMargins(22, 14, 22, 14)
        input_layout.setSpacing(12)

        self.input = ChatInput()
        self.input.setFixedHeight(50)
        self.input.setFont(QFont("Segoe UI", 11))
        self.input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Theme.BG_INPUT};
                color: {Theme.TEXT_PRIMARY};
                border: 1px solid {Theme.BORDER};
                border-radius: 14px;
                padding: 10px 18px;
                selection-background-color: {Theme.ACCENT};
            }}
            QTextEdit:focus {{
                border: 1px solid {Theme.BORDER_FOCUS};
            }}
        """)
        self.input.send.connect(self.send_message)
        input_layout.addWidget(self.input, 1)

        # Send button with gradient
        self.send_btn = QPushButton("➤")
        self.send_btn.setFixedSize(50, 50)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setFont(QFont("Segoe UI", 18))
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {Theme.ACCENT}, stop:1 {Theme.ACCENT_GLOW}
                );
                color: white;
                border: none;
                border-radius: 14px;
            }}
            QPushButton:hover {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {Theme.ACCENT_HOVER}, stop:1 {Theme.ACCENT}
                );
            }}
            QPushButton:pressed {{
                background-color: {Theme.ACCENT_GLOW};
            }}
        """)
        # Glow on send button
        btn_glow = QGraphicsDropShadowEffect()
        btn_glow.setBlurRadius(20)
        btn_glow.setColor(QColor(124, 58, 237, 90))
        btn_glow.setOffset(0, 2)
        self.send_btn.setGraphicsEffect(btn_glow)

        self.send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_btn)

        main_layout.addWidget(input_bar)

        # ── Welcome message ──
        self.add_ai(
            "Hello! 👋 I'm the **Arix Mart AI Assistant** powered by Groq.\n\n"
            "I can help you with:\n"
            "• 🛒  Product search & pricing\n"
            "• 📦  Inventory management\n"
            "• 📊  Sales reports & analytics\n"
            "• 👥  Staff & customer support\n\n"
            "Ask me anything!"
        )

    # ═══════════════════════════════════════════════════════════
    # Methods
    # ═══════════════════════════════════════════════════════════

    def _now(self):
        return datetime.datetime.now().strftime("%I:%M %p")

    def add_user(self, text):
        bubble = ChatBubble(text, is_user=True, timestamp=self._now())
        self.chat_layout.addWidget(bubble)
        self._scroll_bottom()

    def add_ai(self, text):
        bubble = ChatBubble(text, is_user=False, timestamp=self._now())
        self.chat_layout.addWidget(bubble)
        self._scroll_bottom()

    def send_message(self):
        text = self.input.toPlainText().strip()
        if not text:
            return

        self.input.clear()
        self.add_user(text)

        # Show typing indicator
        self.typing = TypingIndicator()
        self.chat_layout.addWidget(self.typing)
        self._scroll_bottom()

        # Disable input while waiting
        self.input.setEnabled(False)
        self.send_btn.setEnabled(False)

        # Run Groq API call in background thread
        self.thread = QThread()
        self.worker = AIWorker(text)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._on_response)
        self.worker.finished.connect(self.thread.quit)

        self.thread.start()

    def _on_response(self, text):
        # Remove typing indicator
        if hasattr(self, 'typing') and self.typing:
            self.typing.stop()
            self.chat_layout.removeWidget(self.typing)
            self.typing.deleteLater()
            self.typing = None

        self.add_ai(text)

        # Re-enable input
        self.input.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.input.setFocus()

    def _scroll_bottom(self):
        QTimer.singleShot(50, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        ))

    def _clear_chat(self):
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.add_ai("💬 Chat cleared. How can I help you?")


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════
def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(Theme.BG_PRIMARY))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(Theme.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Base, QColor(Theme.BG_SECONDARY))
    palette.setColor(QPalette.ColorRole.Text, QColor(Theme.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Button, QColor(Theme.BG_SECONDARY))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(Theme.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(Theme.ACCENT))
    app.setPalette(palette)

    win = ArixAI()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
