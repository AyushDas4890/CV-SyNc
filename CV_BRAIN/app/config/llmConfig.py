from langchain_groq import ChatGroq


class LLM:
    
    def __init__(self,modelName,api_key,temperature,maxTokens):

        self.modelName = modelName
        self.api_key = api_key
        self.temperature = temperature
        self.maxTokens = maxTokens

        self.llm = ChatGroq(model=modelName,api_key=api_key,temperature=temperature,max_tokens=maxTokens)

    def get_groq_client(self):
        
        return self.llm
        
        
