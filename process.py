import requests 
import os 
import time 

class ConvertPDf: 
    def __init__(self, pdf_path, app_key, app_id):
        self.pdf_path = pdf_path
        self.pdf_id = None
        self.headers = {'app_key': app_key, 'app_id': app_id}
        self.base_url = "https://api.mathpix.com/v3/pdf"
    def poll_conversion_status(self, max_wait=60, interval=5):

        elapsed_time = 0
        while elapsed_time < max_wait:
            response = requests.get(f"https://api.mathpix.com/v3/pdf/{self.pdf_id}", headers=self.headers)
            data = response.json()
            status = data.get("status")

            print(f"[{elapsed_time}s] Status: {status}")

            if status == "completed":
                print("PDF conversion completed.")
                return True
            elif status == "error":
                print("Error during conversion:", data.get("error", "Unknown error"))
                return False

            time.sleep(interval)
            elapsed_time += interval

        print("Timeout: Conversion did not complete in time.")
        return False

    def upload_to_mathpix(self):
        """Gửi PDF đến Mathpix API để convert"""
        try:
            with open(self.pdf_path, "rb") as f:
                print("Đang gửi request đến Mathpix...")

                files = {
                    "file": (os.path.basename(self.pdf_path), f, "application/pdf")
                }

                response = requests.post(
                    self.base_url,
                    headers=self.headers,
                    files=files
                )

                if response.status_code == 200:
                    result = response.json()
                    print("Gửi thành công!")
                    self.pdf_id = result['pdf_id']
                    return result
                else:
                    print(f"Lỗi API: {response.status_code} - {response.text}")
                    return None

        except Exception as e:
            print(f"Lỗi: {e}")
            return None

    def download_mmd(self, pdf_id, output_path):
        """Download file MMD đã convert"""

        print(pdf_id)
        # self.poll_conversion_status()
        # time.sleep(15)
        try:
            response = requests.get(f"{self.base_url}/{pdf_id}.mmd", headers=self.headers)
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
            with open(output_path, 'wb') as f:
                f.write(response.content)
                print(f"Downloaded: {output_path}")
            return output_path
        except Exception as e:
            print(f"Lỗi download: {str(e)}")
            return None


    def convert_pdf_to_mmd(self):
        """Convert PDF to MMD"""

        print("Bắt đầu convert PDF to MMD")
        
        if not os.path.exists(self.pdf_path):
            print(f"File không tồn tại: {self.pdf_path}")
            return None
        
        result = self.upload_to_mathpix()
        if not result:
            return None
        
        pdf_id = result['pdf_id']
    
        if not pdf_id:
            print("Không nhận được pdf_id")
            return None
        
        print(f"PDF ID: {pdf_id}")

        pdf_name = os.path.splitext(os.path.basename(self.pdf_path))[0]
        output_path = os.path.dirname(os.path.dirname(self.pdf_path)) + f"/output/{pdf_name}_converted.mmd"

        # Download
        status = self.poll_conversion_status()
        if status:       
            downloaded_file = self.download_mmd(pdf_id, output_path)
        
        if downloaded_file:
            print(f"Hoàn thành! File MMD: {downloaded_file}")
            return downloaded_file
        else:
            return None



