import requests 
import os 
import time 
from dotenv import load_dotenv

load_dotenv()

app_key = os.getenv('APP_KEY')
app_id = os.getenv('APP_ID')
headers = {'app_key': app_key, 'app_id': app_id}
base_url = "https://api.mathpix.com/v3/pdf"

def send_pdf_to_mathpix(file_path):
    """Gửi PDF đến Mathpix API để convert"""
    try:
        with open(file_path, "rb") as f:
            files = {
                "file": (os.path.basename(file_path), f, "application/pdf")
            }

            response = requests.post(
                base_url,
                headers=headers,
                files=files
            )

            if response.status_code == 200:
                result = response.json()
                print("Gửi thành công")
                print(result)
                return result
            else:
                print(f"Lỗi API: {response.status_code} - {response.text}")
                return None

    except Exception as e:
        print(f"Lỗi: {e}")
        return None

def check_conversion_status(pdf_id):
    """Kiểm tra trạng thái conversion"""
    
    try:
        response = requests.get(f"{base_url}/{pdf_id}", headers=headers)
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            print(f"Lỗi check status: {response.status_code}")
            return None
    except Exception as e:
        print(f"Lỗi check status: {e}")
        return None

def download_mmd(pdf_id, output_path):
    """Download file DOCX đã convert"""

    print(pdf_id)
    time.sleep(15)
    try:
        response = requests.get(f"{base_url}/{pdf_id}.mmd", headers=headers)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
        with open(output_path, 'wb') as f:
            f.write(response.content)
            print(f"Downloaded: {output_path}")
        return output_path
    except Exception as e:
        print(f"Lỗi download: {str(e)}")
        return None


def convert_pdf_to_mmd(pdf_path):
    """Convert PDF to DOCX"""

    print("Bắt đầu convert PDF to MMD")
    
    if not os.path.exists(pdf_path):
        print(f"File không tồn tại: {pdf_path}")
        return None
    
    result = send_pdf_to_mathpix(pdf_path)
    if not result:
        return None
    
    pdf_id = result['pdf_id']
   
    if not pdf_id:
        print("Không nhận được pdf_id")
        return None
    
    print(f"PDF ID: {pdf_id}")
  
    print("Đợi 15 giây để server cập nhật PDF ID")
    time.sleep(15)
    

   
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_path = os.path.dirname(os.path.dirname(pdf_path)) + f"/output/{pdf_name}_converted.mmd"

    # Download
    downloaded_file = download_mmd(pdf_id, output_path)
    
    if downloaded_file:
        print(f"Hoàn thành! File DOCX: {downloaded_file}")
        return downloaded_file
    else:
        return None


if __name__ == "__main__": 
    
    pdf_folder = r"D:\Tools\PDFConvert\unlock"
    
    for filename in os.listdir(pdf_folder):
        if filename.endswith('.pdf'):
            pdf_path = os.path.join(pdf_folder, filename)
            print(f"Đang convert: {pdf_path}")
            result = convert_pdf_to_mmd(pdf_path)
            if result:
                print(f"File đã convert: {result}")
            else:
                print(" Không thể convert file")
    if result:
        print(f"\nSUCCESS! File đã convert: {result}")
    else:
        print(f"\n FAILED! Không thể convert file")

