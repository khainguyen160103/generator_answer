from google import genai
from google.genai import types
from dotenv import load_dotenv
import os
import re
import json 
load_dotenv()
key = os.getenv("GEMINI_API_KEY")

client = genai.Client()
client = genai.Client(api_key=key)


path_gen_answer = r"D:\Tools\PDFConvert\prompt_aPhuowng.txt"
path_check_duplicate = r"D:\Tools\PDFConvert\check_duplicate.txt"

with open(path_gen_answer, "r", encoding="utf-8") as f:
    prompt_gen_answer = f.read()

with open(path_check_duplicate, "r", encoding="utf-8") as f:
    prompt_check_duplicate = f.read()
path_file = r"D:\Tools\PDFConvert\output\Công nghệ 10_bài 8_converted.mmd"
filename = os.path.splitext(os.path.basename(path_file))[0]

with open(path_file, "rb") as f:
    md_data = f.read()

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents = 
    [types.Part.from_bytes(
        data=md_data,
        mime_type='text/markdown',
      ),
      prompt_gen_answer]
)

if response.text :
    cleaned = re.sub(r"^```json|```$", "", response.text, flags=re.MULTILINE).strip()
    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)
    json_path = f"{filename}.json" 
    with open(json_path , "w") as file : 
        file.write(cleaned)
        print("tao file thanh cong")

    with open(json_path , "r" , encoding="utf-8") as file : 
        json_data = json.load(file)
    
    json_bytes = json.dumps(json_data, ensure_ascii=False, indent=2).encode('utf-8')
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(
                data=json_bytes,
                mime_type='application/json',
            ),
            prompt_check_duplicate
           ]
        )

    if (response.text): 
        with open(json_path , "w") as file : 
            file.write(cleaned)
            print("tao file check duplicate thanh cong")

# print(response.text)