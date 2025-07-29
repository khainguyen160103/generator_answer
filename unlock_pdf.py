import subprocess
import os

def remove_pdf_restrictions_batch(input_dir, output_dir):
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.lower().endswith('.pdf'):
                input_pdf_path = os.path.join(root, file)

                # Tạo đường dẫn tương ứng trong thư mục output
                relative_path = os.path.relpath(root, input_dir)
                output_folder = os.path.join(output_dir, relative_path)
                os.makedirs(output_folder, exist_ok=True)
                output_pdf_path = os.path.join(output_folder, file)
                try:
                    command = [
                        'qpdf',
                        '--decrypt',
                        input_pdf_path,
                        output_pdf_path
                    ]
                    subprocess.run(command, check=True, shell=True)
                    print(f"✅ Đã xử lý: {input_pdf_path}")
                except subprocess.CalledProcessError as e:
                    print(f"❌ Lỗi với file: {input_pdf_path} - {e}")

# 👉 Ví dụ sử dụng:
input_directory = r'D:\Tools\PDFConvert\input'      # Thư mục chứa các PDF gốc
output_directory = r'D:\Tools\PDFConvert\unlock'  # Thư mục lưu PDF đã xử lý

remove_pdf_restrictions_batch(input_directory, output_directory)
