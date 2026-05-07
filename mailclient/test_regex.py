import re
import json

content = """
Claro, aquí tienes tu análisis:

```json
{
  "spam_probability": 50,
  "reason": "Test"
}
```

Espero que te sirva.
"""

# Extract the JSON block
match = re.search(r'\{.*\}', content, re.DOTALL)
if match:
    json_str = match.group(0)
    print("Found JSON:")
    print(json_str)
    parsed = json.loads(json_str)
    print("Parsed:", parsed)
else:
    print("No JSON found.")
