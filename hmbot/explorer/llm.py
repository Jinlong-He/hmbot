import os
import time
from dotenv import load_dotenv
from openai import OpenAI
from loguru import logger
from pathlib import Path


def ensure_env_file():
    """
    Check if .env file exists and create it if it doesn't
    """
    env_path = Path('.env')
    if not env_path.exists():
        logger.info(".env file not found, creating a template...")
        with open(env_path, 'w') as f:
            f.write("# General LLM settings\n")
            f.write("GENERAL_BASE_URL=\"\"\n")
            f.write("GENERAL_MODEL=\"\"\n")
            f.write("GENERAL_API_KEY=\"\"\n\n")
            f.write("# Specialized LLM settings\n")
            f.write("SPECIALIZED_BASE_URL=\"\"\n")
            f.write("SPECIALIZED_MODEL=\"\"\n")
            f.write("SPECIALIZED_API_KEY=\"\"\n")
        logger.info(f".env template created at {env_path.absolute()}")


class LLM(object):
    def __init__(self, url="", model="", api_key=""):
        self.client = OpenAI(api_key=api_key, base_url=url)
        self.model = model

    def ask(self, messages, retry=3, temperature=1.0):
        """
        Get response from LLM
        """
        while retry > 0:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    temperature=temperature,
                    messages=messages,
                    stream=False,
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(e)
                time.sleep(1)
                retry -= 1
        return None
    

class GeneralLLM(LLM):
    def __init__(self):
        ensure_env_file()
        load_dotenv()
        url=os.getenv("GENERAL_BASE_URL")
        model=os.getenv("GENERAL_MODEL")
        api_key=os.getenv("GENERAL_API_KEY")
        super().__init__(url, model, api_key)

    def ask(self, messages, retry=3, temperature=1.0):
        return super().ask(messages, retry, temperature)


class SpecializedLLM(LLM):
    def __init__(self):
        ensure_env_file()
        load_dotenv()
        url=os.getenv("SPECIALIZED_BASE_URL")
        model=os.getenv("SPECIALIZED_MODEL")
        api_key=os.getenv("SPECIALIZED_API_KEY")
        super().__init__(url, model, api_key)

    def ask(self, messages, retry=3, temperature=0):
        return super().ask(messages, retry, temperature)

        


