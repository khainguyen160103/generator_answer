from google import genai
from google.genai import types


class GeminiClient : 

    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)

    def send_data_to_AI(self, model, prompt ,data = None , mime_type = None ):
        response =  self.client.models.generate_content(
            model=model,
            contents=[
                types.Part.from_bytes(
                    data=data,
                    mime_type=mime_type,
                ),
                prompt
            ]
        )
        return response.text