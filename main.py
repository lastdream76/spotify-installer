import re
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QThread, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


def get_downloads_dir() -> Path:
    downloads_dir = Path.home() / "Downloads" / "Spotify"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    return downloads_dir


def get_ffmpeg_path() -> Path | None:
    ffmpeg_path = Path(__file__).resolve().parent / "ffmpeg.exe"
    return ffmpeg_path if ffmpeg_path.exists() else None


def clean_console_output(text: str) -> str:
    text = re.sub(r"\x1b\[[0-9;]*m", "", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_progress(text: str) -> int | None:
    match = re.search(r"\b(\d{1,3})%", text)
    if not match:
        return None
    return max(0, min(100, int(match.group(1))))


def is_spotdl_error(text: str) -> bool:
    error_markers = (
        "LookupError:",
        "No results found",
        "returned no usable results",
        "FFmpegError:",
        "An error occurred",
    )
    return any(marker in text for marker in error_markers)


class DownloadWorker(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool)

    def __init__(self, url: str, output_dir: Path):
        super().__init__()
        self.url = url
        self.output_dir = output_dir

    def run(self):
        try:
            command = [
                "spotdl",
                self.url,
                "--audio",
                "youtube",
                "youtube-music",
                "soundcloud",
                "bandcamp",
                "--print-errors",
            ]
            ffmpeg_path = get_ffmpeg_path()
            if ffmpeg_path is not None:
                command.extend(["--ffmpeg", str(ffmpeg_path)])

            process = subprocess.Popen(
                command,
                cwd=str(self.output_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
            )

            has_spotdl_error = False
            last_line = None

            if process.stdout is not None:
                for line in iter(process.stdout.readline, ""):
                    line = clean_console_output(line).strip()
                    if line:
                        progress = parse_progress(line)
                        if progress is not None:
                            self.progress_signal.emit(progress)

                        if is_spotdl_error(line):
                            has_spotdl_error = True

                        if line == last_line:
                            continue
                        last_line = line
                        self.log_signal.emit(line)
                process.stdout.close()

            return_code = process.wait()
            self.finished_signal.emit(return_code == 0 and not has_spotdl_error)
        except Exception as exc:
            self.log_signal.emit(f"Failed to start spotdl: {exc}")
            self.finished_signal.emit(False)


class SpotifyDownloaderApp(QWidget):
    def __init__(self):
        super().__init__()
        self.downloads_dir = get_downloads_dir()
        self.worker = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Music Downloader")
        self.resize(760, 520)
        self.setMinimumSize(640, 440)

        root = QVBoxLayout()
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(18)

        title = QLabel("Music Downloader")
        title.setObjectName("title")
        root.addWidget(title)

        subtitle = QLabel("Paste a Spotify track, album, or playlist link.")
        subtitle.setObjectName("subtitle")
        root.addWidget(subtitle)

        input_card = QFrame()
        input_card.setObjectName("panel")
        input_layout = QVBoxLayout(input_card)
        input_layout.setContentsMargins(18, 18, 18, 18)
        input_layout.setSpacing(12)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste a Spotify link")
        self.url_input.returnPressed.connect(self.start_download)
        input_layout.addWidget(self.url_input)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        self.download_btn = QPushButton("Download")
        self.download_btn.setObjectName("primaryButton")
        self.download_btn.clicked.connect(self.start_download)
        buttons_layout.addWidget(self.download_btn)

        self.open_folder_btn = QPushButton("Open Folder")
        self.open_folder_btn.clicked.connect(self.open_downloads_folder)
        buttons_layout.addWidget(self.open_folder_btn)

        self.clear_btn = QPushButton("Clear Log")
        self.clear_btn.clicked.connect(self.clear_log)
        buttons_layout.addWidget(self.clear_btn)

        input_layout.addLayout(buttons_layout)
        root.addWidget(input_card)

        status_layout = QVBoxLayout()
        status_layout.setSpacing(8)

        self.status_label = QLabel("Files are saved to: Downloads\\Spotify")
        self.status_label.setObjectName("status")
        status_layout.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        status_layout.addWidget(self.progress)

        root.addLayout(status_layout)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setPlaceholderText("Download progress will appear here.")
        root.addWidget(self.log_area, 1)

        self.setLayout(root)
        self.apply_styles()

    def apply_styles(self):
        self.setStyleSheet(
            """
            QWidget {
                background: #0b0f17;
                color: #e6edf7;
                font-family: Segoe UI, Arial, sans-serif;
                font-size: 14px;
            }

            QLabel#title {
                color: #f8fafc;
                font-size: 30px;
                font-weight: 700;
            }

            QLabel#subtitle {
                color: #9aa7bd;
                font-size: 15px;
            }

            QLabel#status {
                color: #aab7ca;
                font-size: 13px;
            }

            QFrame#panel {
                background: #121824;
                border: 1px solid #263244;
                border-radius: 8px;
            }

            QLineEdit {
                background: #0f1521;
                color: #f8fafc;
                border: 1px solid #2b384c;
                border-radius: 6px;
                padding: 11px 12px;
                selection-background-color: #1db954;
            }

            QLineEdit:focus {
                border: 1px solid #1db954;
            }

            QLineEdit:disabled {
                color: #748197;
                background: #111722;
            }

            QPushButton {
                color: #e6edf7;
                background: #182233;
                border: 1px solid #2b384c;
                border-radius: 6px;
                padding: 10px 16px;
                font-weight: 600;
            }

            QPushButton:hover {
                background: #202d42;
            }

            QPushButton:disabled {
                color: #6d7890;
                background: #151c29;
                border: 1px solid #222c3d;
            }

            QPushButton#primaryButton {
                color: #ffffff;
                background: #1db954;
                border: 1px solid #1aa34a;
            }

            QPushButton#primaryButton:hover {
                background: #18a84b;
            }

            QProgressBar {
                height: 8px;
                background: #182233;
                border: 0;
                border-radius: 4px;
            }

            QProgressBar::chunk {
                background: #1db954;
                border-radius: 4px;
            }

            QTextEdit {
                background: #080c12;
                color: #dbe7ff;
                border: 1px solid #1f2937;
                border-radius: 8px;
                padding: 12px;
                font-family: Consolas, monospace;
                font-size: 13px;
            }
            """
        )

    def start_download(self):
        url = self.url_input.text().strip()
        if not url:
            self.append_log("Error: enter a Spotify link.")
            self.status_label.setText("Waiting for a link to download.")
            return

        self.download_btn.setEnabled(False)
        self.url_input.setEnabled(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.status_label.setText("Downloading to: Downloads\\Spotify")
        self.append_log(f"Starting download: {url}")

        self.worker = DownloadWorker(url, self.downloads_dir)
        self.worker.log_signal.connect(self.append_log)
        self.worker.progress_signal.connect(self.progress.setValue)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def append_log(self, text: str):
        self.log_area.append(text)

    def clear_log(self):
        self.log_area.clear()

    def open_downloads_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.downloads_dir)))

    def on_finished(self, success: bool):
        self.download_btn.setEnabled(True)
        self.url_input.setEnabled(True)
        self.progress.setRange(0, 100)
        self.progress.setValue(100 if success else 0)

        if success:
            self.status_label.setText("Done. Files saved to: Downloads\\Spotify")
            self.append_log("Download completed successfully.")
        else:
            self.status_label.setText("Download failed.")
            self.append_log("An error occurred during download.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SpotifyDownloaderApp()
    window.show()
    sys.exit(app.exec())
