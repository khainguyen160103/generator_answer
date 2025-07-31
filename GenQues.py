import sys
import os
import json
import re
from docx import Document
from docx.shared import Inches, Pt
from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QListWidget, QFileDialog, QMessageBox, QSplitter, QProgressBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QFont
import mammoth
from dotenv import load_dotenv
from google.oauth2 import service_account
from PIL import Image
from io import BytesIO
import requests
import validators

# Nhập các hàm từ các script khác
from json_to_docx import create_docx_from_json, parse_markdown_table, add_table_to_doc
from text2Image import generate_image_from_text
from main import ConvertPDf, VertexClient

# Tải biến môi trường
load_dotenv()



class ProcessingThread(QThread):
    """Luồng xử lý PDF trong nền."""
    progress = pyqtSignal(str)  # Tín hiệu để cập nhật giao diện với thông báo tiến độ
    error = pyqtSignal(str)     # Tín hiệu để báo lỗi
    finished = pyqtSignal(list) # Tín hiệu để gửi danh sách file DOCX đã tạo

    def __init__(self, pdf_file, prompt_path, app_key, app_id, project_id, creds):
        super().__init__()
        self.pdf_file = pdf_file
        self.prompt_path = prompt_path
        self.app_key = app_key
        self.app_id = app_id
        self.project_id = project_id
        self.creds = creds

    def run(self):
        generated_files = []
        try:
            # Đọc các file prompt
            with open(self.prompt_path, 'r', encoding='utf-8') as f:
                prompt_gen_answer = f.read()

            check_duplicate_path = os.path.join(os.path.dirname(self.prompt_path), 'check_duplicate.txt')
            check_true_false_path = os.path.join(os.path.dirname(self.prompt_path), 'check_trueFalse.txt')
            

            with open(check_duplicate_path, 'r', encoding='utf-8') as f:
                prompt_check_duplicate = f.read()
            with open(check_true_false_path, 'r', encoding='utf-8') as f:
                prompt_check_true_false = f.read()


            pdf_path = self.pdf_file
            self.progress.emit(f"Đang xử lý: {pdf_path}")

            # Chuyển PDF sang Markdown
            pdf_converter = ConvertPDf(pdf_path, self.app_key, self.app_id)
            path_md = pdf_converter.convert_pdf_to_mmd()
            if not path_md:
                self.error.emit(f"Không thể chuyển đổi {pdf_path} sang Markdown")
            else:
                self.progress.emit(f"Đã chuyển sang Markdown: {path_md}")
                filename_base = os.path.splitext(os.path.basename(path_md))[0]

                # Đọc nội dung Markdown
                with open(path_md, "rb") as f:
                    md_data = f.read()

                # Khởi tạo client Vertex AI
                gemini_client = VertexClient(project_id=self.project_id, creds=self.creds, model="gemini-2.0-flash")

                # Tạo nội dung JSON
                response = gemini_client.send_data_to_AI(
                    data=md_data,
                    mime_type="text/markdown",
                    prompt=prompt_gen_answer
                )

                if response:
                    cleaned = re.sub(r"^```json|```$", "", response, flags=re.MULTILINE).strip()
                    json_path = f"{filename_base}.json"
                    with open(json_path, "w", encoding="utf-8") as f:
                        f.write(cleaned)
                    self.progress.emit(f"Đã lưu JSON: {json_path}")

                    # Kiểm tra trùng lặp
                    gemini_client_check = VertexClient(project_id=self.project_id, creds=self.creds, model="gemini-2.0-flash-lite")
                    self.progress.emit("Đang kiểm tra trùng lặp...")
                    with open(json_path, "rb") as f:
                        json_content = f.read()
                    response_check = gemini_client_check.send_data_to_AI(
                        mime_type="text/plain",
                        data=json_content,
                        prompt=prompt_check_duplicate
                    )

                    if response_check:
                        cleaned_check = re.sub(r"^```json|```$", "", response_check, flags=re.MULTILINE).strip()
                        check_path = f"{filename_base}_check.json"
                        with open(check_path, "w", encoding="utf-8") as f:
                            f.write(cleaned_check)
                        self.progress.emit(f"Đã lưu kết quả kiểm tra trùng lặp: {check_path}")

                        if os.path.exists(check_path):
                            self.progress.emit("Đang check đúng sai..")
                           
                            with open(check_path, "r", encoding="utf-8") as f:
                                    try:
                                        objects = json.load(f)
                                    except Exception as e:
                                        self.error.emit(f"Lỗi đọc file trùng lặp: {str(e)}")
                                        objects = []

                            results = []
                            for idx, obj in enumerate(objects):
                                    # Ghép prompt với object
                                    prompt = f"{prompt_check_true_false}\n{json.dumps(obj, ensure_ascii=False, indent=2)}"
                                    response = gemini_client_check.send_data_to_AI(
                                        mime_type="text/plain",
                                        data=prompt.encode("utf-8"),
                                        prompt=""  # Nếu hàm yêu cầu prompt riêng, để trống vì đã ghép ở trên
                                    )
                                    if response:
                                        cleaned = re.sub(r"^```json|```$", "", response, flags=re.MULTILINE).strip()
                                        try:
                                            result_obj = json.loads(cleaned)
                                        except Exception:
                                            result_obj = {"raw": cleaned}
                                        results.append(result_obj)
                                        self.progress.emit(f"Đã xử lý đúng/sai cho câu hỏi {idx+1}/{len(objects)}")
                                    else:
                                        results.append({"error": "No response", "object": obj})

                                # Ghi toàn bộ kết quả ra file JSON
                            check_true_false_result_path = f"{filename_base}_true_false_results.json"
                            with open(check_true_false_result_path, "w", encoding="utf-8") as f:
                                    json.dump(results, f, ensure_ascii=False, indent=2)
                            self.progress.emit(f"Đã lưu kết quả đúng/sai cho từng câu hỏi: {check_true_false_result_path}")
                            generated_files.append(check_true_false_result_path)

                                # Chuyển JSON sang DOCX
                            docx_true_false_path = f"{filename_base}_true_false_results.docx"
                            create_docx_from_json(check_true_false_result_path, docx_true_false_path)
                            self.progress.emit(f"Đã tạo DOCX từ kết quả đúng/sai: {docx_true_false_path}")
                            generated_files.append(docx_true_false_path)

                    else:
                        self.error.emit(f"Không thể kiểm tra trùng lặp cho {json_path}")
                else:
                    self.error.emit(f"Không thể tạo JSON cho {path_md}")
        except Exception as e:
            self.error.emit(f"Lỗi trong quá trình xử lý: {str(e)}")
        self.finished.emit(generated_files)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF - Prompt - DOCX Processor")
        self.resize(1000, 700)
        self.generated_files = []
        self.init_ui()
        self.setup_credentials()

    def setup_credentials(self):
        """Thiết lập thông tin xác thực Google Cloud từ biến môi trường."""
        try:
            service_account_data = {
                "type": os.getenv("TYPE"),
                "project_id": os.getenv("PROJECT_ID"),
                "private_key_id": os.getenv("PRIVATE_KEY_ID"),
                "private_key": os.getenv("PRIVATE_KEY").replace('\\n', '\n'),
                "client_email": os.getenv("CLIENT_EMAIL"),
                "client_id": os.getenv("CLIENT_ID", ""),
                "auth_uri": os.getenv("AUTH_URI"),
                "token_uri": os.getenv("TOKEN_URI"),
                "auth_provider_x509_cert_url": os.getenv("AUTH_PROVIDER_X509_CERT_URL"),
                "client_x509_cert_url": os.getenv("CLIENT_X509_CERT_URL"),
                "universe_domain": os.getenv("UNIVERSE_DOMAIN")
            }
            self.credentials = service_account.Credentials.from_service_account_info(
                service_account_data,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            self.app_key = os.getenv('MATHPIX_APP_KEY')
            self.app_id = os.getenv('MATHPIX_APP_ID')
            self.project_id = os.getenv('PROJECT_ID')
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể tải thông tin xác thực: {str(e)}")
            self.process_button.setEnabled(False)

    def init_ui(self):
        font = QFont("Arial", 10)

        # Chọn thư mục PDF
        self.pdf_label = QLabel("Chưa chọn thư mục PDF")
        self.pdf_label.setFont(font)
        self.pdf_label.setFixedHeight(30)
        self.pdf_label.setStyleSheet("border: 1px solid black; padding: 3px;")
        self.pdf_button = QPushButton("Chọn Thư mục PDF")
        self.pdf_button.setFixedSize(120, 30)
        self.pdf_button.clicked.connect(self.select_pdf)

        pdf_layout = QHBoxLayout()
        pdf_layout.addWidget(self.pdf_label)
        pdf_layout.addWidget(self.pdf_button)

        # Chọn file Prompt
        self.prompt_label = QLabel("Chưa chọn file prompt")
        self.prompt_label.setFont(font)
        self.prompt_label.setFixedHeight(30)
        self.prompt_label.setStyleSheet("border: 1px solid black; padding: 3px;")
        self.prompt_button = QPushButton("Chọn Prompt")
        self.prompt_button.setFixedSize(120, 30)
        self.prompt_button.clicked.connect(self.select_prompt)
        self.edit_prompt_button = QPushButton("Sửa Prompt")
        self.edit_prompt_button.setFixedSize(120, 30)
        self.edit_prompt_button.clicked.connect(self.edit_prompt)

        prompt_layout = QHBoxLayout()
        prompt_layout.addWidget(self.prompt_label)
        prompt_layout.addWidget(self.prompt_button)
        prompt_layout.addWidget(self.edit_prompt_button)

        # Nút xử lý
        self.process_button = QPushButton("Bắt đầu xử lý")
        self.process_button.setFont(font)
        self.process_button.setFixedHeight(40)
        self.process_button.clicked.connect(self.process_files)
        self.process_button.setStyleSheet("border: 1px solid black;")

        # Thanh tiến độ và nhãn trạng thái
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_label = QLabel("Sẵn sàng")
        self.status_label.setFont(font)

        process_layout = QVBoxLayout()
        process_layout.addWidget(self.process_button)
        process_layout.addWidget(self.progress_bar)
        process_layout.addWidget(self.status_label)

        # Trình xem DOCX và danh sách
        self.docx_viewer = QWebEngineView()
        self.docx_viewer.setFont(font)
        self.docx_viewer.setStyleSheet("border: 1px solid black; padding: 5px;")
        self.docx_list = QListWidget()
        self.docx_list.setFont(font)
        self.docx_list.setFixedWidth(220)
        self.docx_list.itemClicked.connect(self.show_selected_docx)

        # Splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.docx_viewer)
        splitter.addWidget(self.docx_list)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        # Bố cục chính
        main_layout = QVBoxLayout()
        main_layout.addLayout(pdf_layout)
        main_layout.addLayout(prompt_layout)
        main_layout.addLayout(process_layout)
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

    def select_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn file PDF", "", "PDF Files (*.pdf)")
        if file_path:
            self.pdf_label.setText(file_path)

    def select_prompt(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn file prompt.txt", "", "Text Files (*.txt)")
        if file_path:
            self.prompt_label.setText(file_path)

    def edit_prompt(self):
        prompt_path = self.prompt_label.text()
        if os.path.isfile(prompt_path):
            os.system(f'notepad "{prompt_path}"')
        else:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn file prompt.txt trước.")

    def process_files(self):
        pdf_file = self.pdf_label.text()
        prompt_path = self.prompt_label.text()

        if not os.path.isfile(pdf_file) or pdf_file == "Chưa chọn thư mục PDF":
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn thư mục chứa file PDF.")
            return
        if not os.path.isfile(prompt_path) or prompt_path == "Chưa chọn file prompt":
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn file prompt.txt.")
            return

        # Vô hiệu hóa các thành phần giao diện trong khi xử lý
        self.process_button.setEnabled(False)
        self.pdf_button.setEnabled(False)
        self.prompt_button.setEnabled(False)
        self.edit_prompt_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Đang xử lý...")

        # Bắt đầu xử lý trong luồng riêng
        self.thread = ProcessingThread(pdf_file, prompt_path, self.app_key, self.app_id, self.project_id, self.credentials)
        self.thread.progress.connect(self.update_status)
        self.thread.error.connect(self.show_error)
        self.thread.finished.connect(self.processing_finished)
        self.thread.start()

    def update_status(self, message):
        self.status_label.setText(message)
        self.progress_bar.setValue(self.progress_bar.value() + 10 if self.progress_bar.value() < 90 else 90)

    def show_error(self, message):
        QMessageBox.critical(self, "Lỗi", message)
        self.status_label.setText("Lỗi xảy ra")
        self.progress_bar.setVisible(False)
        self.process_button.setEnabled(True)
        self.pdf_button.setEnabled(True)
        self.prompt_button.setEnabled(True)
        self.edit_prompt_button.setEnabled(True)

    def processing_finished(self, generated_files):
        self.generated_files = generated_files
        self.docx_list.clear()
        for fname in generated_files:
            self.docx_list.addItem(os.path.basename(fname))
        self.status_label.setText("Hoàn tất xử lý")
        self.progress_bar.setValue(100)
        self.progress_bar.setVisible(False)
        self.process_button.setEnabled(True)
        self.pdf_button.setEnabled(True)
        self.prompt_button.setEnabled(True)
        self.edit_prompt_button.setEnabled(True)
        if generated_files:
            self.docx_list.setCurrentRow(0)
            self.show_selected_docx(self.docx_list.item(0))

    def show_selected_docx(self, item):
        file_name = item.text()
        full_path = next((f for f in self.generated_files if os.path.basename(f) == file_name), None)
        if not full_path or not os.path.isfile(full_path):
            self.docx_viewer.setHtml(f"<h3>Lỗi:</h3><p>File không tồn tại: {file_name}</p>")
            return

        try:
            with open(full_path, "rb") as docx_file:
                result = mammoth.convert_to_html(docx_file)
                html = result.value.strip()
                if html:
                    self.docx_viewer.setHtml(html)
                else:
                    self.docx_viewer.setHtml(f"<p>Không có nội dung trong {file_name}</p>")
        except Exception as e:
            self.docx_viewer.setHtml(f"<h3>Lỗi khi mở {file_name}</h3><p>{str(e)}</p>")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())