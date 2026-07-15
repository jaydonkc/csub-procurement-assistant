import os
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION")
KNOWLEDGE_BASE_ID = os.getenv("BEDROCK_KNOWLEDGE_BASE_ID")

def query_bedrock(question):
    #model generation - to do
    return f"Bedrock placeholder response for: {question}", []