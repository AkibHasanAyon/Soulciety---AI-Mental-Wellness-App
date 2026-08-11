import json

with open("postman.json", "r") as f:
    data = json.load(f)

healing_folder = {
    "name": "9. Healing Journey",
    "item": [
        {
            "name": "POST Submit Assessment",
            "request": {
                "method": "POST",
                "header": [
                    { "key": "Content-Type", "value": "application/json" },
                    { "key": "Authorization", "value": "Bearer {{access_token}}" },
                    { "key": "X-User-Timezone", "value": "America/New_York", "type": "text" }
                ],
                "body": {
                    "mode": "raw",
                    "raw": "{\n  \"q1_emotional_baseline\": \"Numb or disconnected\",\n  \"q2_past_influence\": 4,\n  \"q3_life_area_impact\": \"Relationships & connection\",\n  \"q4_core_pain_source\": \"Feeling ignored, unseen, or emotionally neglected\",\n  \"q5_coping_pattern\": \"Withdraw from people\",\n  \"q6_relationship_fear\": \"Being abandoned or left\",\n  \"q7_core_belief\": \"I am not enough\",\n  \"q8_desired_relief\": \"Emotional pain\",\n  \"q9_healing_resistance\": \"Fear of what I might uncover\",\n  \"q10_personal_desire\": \"I want to feel safe in my own skin again.\"\n}"
                },
                "url": {
                    "raw": "{{base_url}}/api/healing/assessment/",
                    "host": ["{{base_url}}"],
                    "path": ["api", "healing", "assessment", ""]
                }
            },
            "response": []
        },
        {
            "name": "GET Assessment Status",
            "request": {
                "method": "GET",
                "header": [
                    { "key": "Authorization", "value": "Bearer {{access_token}}" }
                ],
                "url": {
                    "raw": "{{base_url}}/api/healing/assessment/status/",
                    "host": ["{{base_url}}"],
                    "path": ["api", "healing", "assessment", "status", ""]
                }
            },
            "response": []
        },
        {
            "name": "GET Assessment Profile",
            "request": {
                "method": "GET",
                "header": [
                    { "key": "Authorization", "value": "Bearer {{access_token}}" }
                ],
                "url": {
                    "raw": "{{base_url}}/api/healing/assessment/profile/",
                    "host": ["{{base_url}}"],
                    "path": ["api", "healing", "assessment", "profile", ""]
                }
            },
            "response": []
        },
        {
            "name": "GET Today's Plan",
            "request": {
                "method": "GET",
                "header": [
                    { "key": "Authorization", "value": "Bearer {{access_token}}" }
                ],
                "url": {
                    "raw": "{{base_url}}/api/healing/today/",
                    "host": ["{{base_url}}"],
                    "path": ["api", "healing", "today", ""]
                }
            },
            "response": []
        },
        {
            "name": "GET Day Detail",
            "request": {
                "method": "GET",
                "header": [
                    { "key": "Authorization", "value": "Bearer {{access_token}}" }
                ],
                "url": {
                    "raw": "{{base_url}}/api/healing/days/1/",
                    "host": ["{{base_url}}"],
                    "path": ["api", "healing", "days", "1", ""]
                }
            },
            "response": []
        },
        {
            "name": "POST Complete Day",
            "request": {
                "method": "POST",
                "header": [
                    { "key": "Content-Type", "value": "application/json" },
                    { "key": "Authorization", "value": "Bearer {{access_token}}" }
                ],
                "body": {
                    "mode": "raw",
                    "raw": "{\n  \"mood\": \"happy\"\n}"
                },
                "url": {
                    "raw": "{{base_url}}/api/healing/days/1/complete/",
                    "host": ["{{base_url}}"],
                    "path": ["api", "healing", "days", "1", "complete", ""]
                }
            },
            "response": []
        },
        {
            "name": "GET 30-Day Plan Grid",
            "request": {
                "method": "GET",
                "header": [
                    { "key": "Authorization", "value": "Bearer {{access_token}}" }
                ],
                "url": {
                    "raw": "{{base_url}}/api/healing/plan/",
                    "host": ["{{base_url}}"],
                    "path": ["api", "healing", "plan", ""]
                }
            },
            "response": []
        },
        {
            "name": "GET Progress",
            "request": {
                "method": "GET",
                "header": [
                    { "key": "Authorization", "value": "Bearer {{access_token}}" }
                ],
                "url": {
                    "raw": "{{base_url}}/api/healing/progress/",
                    "host": ["{{base_url}}"],
                    "path": ["api", "healing", "progress", ""]
                }
            },
            "response": []
        },
        {
            "name": "GET Settings",
            "request": {
                "method": "GET",
                "header": [
                    { "key": "Authorization", "value": "Bearer {{access_token}}" }
                ],
                "url": {
                    "raw": "{{base_url}}/api/healing/settings/",
                    "host": ["{{base_url}}"],
                    "path": ["api", "healing", "settings", ""]
                }
            },
            "response": []
        },
        {
            "name": "PATCH Settings",
            "request": {
                "method": "PATCH",
                "header": [
                    { "key": "Content-Type", "value": "application/json" },
                    { "key": "Authorization", "value": "Bearer {{access_token}}" }
                ],
                "body": {
                    "mode": "raw",
                    "raw": "{\n  \"timezone\": \"America/New_York\",\n  \"morning_reminder_enabled\": false\n}"
                },
                "url": {
                    "raw": "{{base_url}}/api/healing/settings/",
                    "host": ["{{base_url}}"],
                    "path": ["api", "healing", "settings", ""]
                }
            },
            "response": []
        },
        {
            "name": "POST Reset Journey",
            "request": {
                "method": "POST",
                "header": [
                    { "key": "Authorization", "value": "Bearer {{access_token}}" }
                ],
                "url": {
                    "raw": "{{base_url}}/api/healing/reset/",
                    "host": ["{{base_url}}"],
                    "path": ["api", "healing", "reset", ""]
                }
            },
            "response": []
        }
    ]
}

# Remove existing Healing folder if it exists
data["item"] = [item for item in data["item"] if item["name"] != "9. Healing Journey"]

data["item"].append(healing_folder)

with open("postman.json", "w") as f:
    json.dump(data, f, indent=2)

print("Updated postman.json successfully.")
