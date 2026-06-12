from pydantic import BaseModel, Field
from typing import List
import re

class Theme(BaseModel):
    name: str

class PulseReport(BaseModel):
    themes: List[Theme]

error_msg = r"""<function=PulseReport>{"themes": [{"name": "KYC/Onboarding", "quote": "\"Hello\""}]}</function>"""

match = re.search(r'<function=PulseReport>(.*?)</function>', error_msg, re.DOTALL)
if match:
    j = match.group(1).replace('\\"', '"')
    print("MATCHED:", j)
    # print("PARSED:", PulseReport.model_validate_json(j))
else:
    print("NO MATCH")
