import traceback
import logging

from openai import OpenAI


def get_response(key, messages, model, max_tokens, temperature):
    client = OpenAI(api_key=key)
    result = "No result ...."
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            n=1,
        )
        logging.info(f"Request complete, tokens used: {str(completion.usage.total_tokens)}")
        if len(completion.choices) > 0:
            result = completion.choices[0].message.content
    except Exception as e:
        logging.error(traceback.format_exc())
    logging.info("Result: " + result)
    return result
