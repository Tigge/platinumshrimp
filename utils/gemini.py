import traceback
import logging
from google import genai
from google.genai import types


def get_response(key, messages, model, max_tokens, temperature):
    client = genai.Client(api_key=key)

    system_instruction = None
    contents = []

    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            system_instruction = content
        elif role == "user":
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=content)]))
        elif role == "assistant" or role == "model":
            contents.append(types.Content(role="model", parts=[types.Part.from_text(text=content)]))

    result = "No result ...."
    try:
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                max_output_tokens=max_tokens,
                temperature=temperature,
            ),
        )

        if response.text:
            result = response.text
    except Exception as e:
        logging.error(traceback.format_exc())

    logging.info("Result: " + result)
    return result
