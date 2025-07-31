from dotenv import load_dotenv
from google.oauth2 import service_account


import os 
import re

from callAI import VertexClient
from process import ConvertPDf
load_dotenv()


app_key = os.getenv('MATHPIX_APP_KEY')
app_id = os.getenv('MATHPIX_APP_ID')
api_key = os.getenv('API_KEY')
project_id = os.getenv('PROJECT_ID')
path_gen_answer = r"D:\Tools\PDFConvert\prompt_aPhuowng.txt"
path_check_duplicate = r"D:\Tools\PDFConvert\check_duplicate.txt"

path_markdown = r""

with open(path_gen_answer, 'r', encoding='utf-8') as f:
    prompt_gen_answer = f.read()

with open(path_check_duplicate, 'r', encoding='utf-8') as f:
    prompt_check_duplicate = f.read()

def get_vertex_ai_credentials():
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
    credentials = service_account.Credentials.from_service_account_info(
        service_account_data,
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    return credentials


def main(pdf_path):
    

   for filename in os.listdir(pdf_path):
        if filename.endswith('.pdf'):
            pdf_path = os.path.join(pdf_path, filename)
            print(f"Đang convert: {pdf_path}")
            pdf_converter = ConvertPDf(pdf_path, app_key, app_id)
            path_md = pdf_converter.convert_pdf_to_mmd()
            filename = os.path.splitext(os.path.basename(path_md))[0]

            with open(path_md, "rb") as f:
                md_data = f.read()
            if path_md:
                print(f"File đã convert: {path_md}")

                gemini_client = VertexClient(project_id=project_id, creds=get_vertex_ai_credentials(), model="gemini-2.0-flash")

                response = gemini_client.send_data_to_AI(
                    data=md_data,
                    mime_type="text/markdown",
                    prompt=prompt_gen_answer
                )

                if response:
                        cleaned = re.sub(r"^```json|```$", "", response, flags=re.MULTILINE).strip()
                        with open(f"{filename}.txt", "w", encoding="utf-8") as f:
                            f.write(cleaned)
                print(f"Đã lưu kết quả vào {filename}.txt")

                if os.path.exists(f"{filename}.txt"):
                    with open(f"{filename}.txt", "rb") as f:
                            json_content = f.read()
                  

                    gemini_client_check = VertexClient(project_id=project_id, creds=get_vertex_ai_credentials(), model="gemini-2.0-flash-lite"
                                                       )
                    print("Đang kiểm tra trùng lặp...")
                    response_check = gemini_client_check.send_data_to_AI( 
                        mime_type="text/plain",
                        data=json_content,
                        prompt=prompt_check_duplicate
                    )

                    if response_check:
                        cleaned = re.sub(r"^```json|```$", "", response, flags=re.MULTILINE).strip()
                        with open(f"{filename}_check.json", "w", encoding="utf-8") as f:
                            f.write(cleaned)
                        print(f"Đã lưu kết quả kiểm tra trùng lặp vào {filename}_check.json")
                    else:
                        print("Không thể kiểm tra trùng lặp")

            else:
                print("Không thể convert file")

if __name__ == "__main__": 
    
    pdf_folder = r"D:\Tools\PDFConvert\unlock"
    
    main(pdf_folder)
