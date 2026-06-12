from pulse import get_llm, load_reviews, PulseReport
import json

df = load_reviews()
reviews_text = "..." # Just mock it

prompt = """
You are an analyst.
Output valid JSON adhering to this schema:
{"themes": [{"name": "string", "volume": 0, "summary": "string", "quotes": [{"quote": "string", "stars": 5, "date": "string"}], "action_ideas": ["string"]}]}
"""
llm = get_llm().bind(response_format={"type": "json_object"})
response = llm.invoke(prompt)
print(response.content)
