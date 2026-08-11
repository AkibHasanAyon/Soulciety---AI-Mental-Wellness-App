import json

with open("postman.json", "r") as f:
    data = json.load(f)

for category in data["item"]:
    if category["name"] == "9. Healing Journey":
        # Add questions endpoint at the top
        category["item"].insert(0, {
            "name": "GET Assessment Questions",
            "request": {
                "method": "GET",
                "header": [
                    { "key": "Authorization", "value": "Bearer {{access_token}}" }
                ],
                "url": {
                    "raw": "{{base_url}}/api/healing/assessment/questions/",
                    "host": ["{{base_url}}"],
                    "path": ["api", "healing", "assessment", "questions", ""]
                }
            },
            "response": []
        })

with open("postman.json", "w") as f:
    json.dump(data, f, indent=2)

print("Updated postman.json with GET Assessment Questions successfully.")
