from langchain_ollama import OllamaLLM

# Connect to the local Ollama instance running llama3
llm = OllamaLLM(model="llama3.2:1b")

# Run a simple prompt
response = llm.invoke("Who is the starting quarterback for the Seattle Seahawks")

print(response)
