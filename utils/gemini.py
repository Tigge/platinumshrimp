import traceback
import logging
import google.generativeai as genai

def get_response(key, messages, model, max_tokens, temperature):
    genai.configure(api_key=key)

    system_instruction = None
    history = []

    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            system_instruction = content
        elif role == "user":
            history.append({"role": "user", "parts": [content]})
        elif role == "assistant" or role == "model":
            history.append({"role": "model", "parts": [content]})

    # Gemini's start_chat history should not include the final message
    prompt = ""
    if history and history[-1]["role"] == "user":
        prompt = history.pop()["parts"][0]

    result = "No result ...."
    try:
        model_instance = genai.GenerativeModel(
            model_name=model,
            system_instruction=system_instruction
        )

        chat = model_instance.start_chat(history=history)
        response = chat.send_message(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            )
        )

        if response.text:
            result = response.text
    except Exception as e:
        logging.error(traceback.format_exc())

    logging.info("Result: " + result)
    return result
