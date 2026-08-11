import json

with open("postman.json", "r") as f:
    data = json.load(f)

# Helper to add if missing
def add_missing(folder_name, endpoints):
    for folder in data["item"]:
        if folder["name"] == folder_name or folder_name in folder["name"]:
            existing_urls = [item["request"]["url"]["raw"] for item in folder.get("item", [])]
            for ep in endpoints:
                if ep["request"]["url"]["raw"] not in existing_urls:
                    folder.setdefault("item", []).append(ep)

# Auth missing
add_missing("1. Auth", [
    {
        "name": "POST Token Refresh",
        "request": {
            "method": "POST",
            "header": [{"key": "Content-Type", "value": "application/json"}],
            "body": {"mode": "raw", "raw": "{\n  \"refresh\": \"...\"\n}"},
            "url": {"raw": "{{base_url}}/api/auth/token/refresh/", "host": ["{{base_url}}"], "path": ["api", "auth", "token", "refresh", ""]}
        },
        "response": []
    },
    {
        "name": "POST Resend OTP",
        "request": {
            "method": "POST",
            "header": [{"key": "Content-Type", "value": "application/json"}],
            "body": {"mode": "raw", "raw": "{\n  \"email\": \"john@example.com\"\n}"},
            "url": {"raw": "{{base_url}}/api/auth/resend-otp/", "host": ["{{base_url}}"], "path": ["api", "auth", "resend-otp", ""]}
        },
        "response": []
    },
    {
        "name": "POST Google Auth",
        "request": {
            "method": "POST",
            "header": [{"key": "Content-Type", "value": "application/json"}],
            "body": {"mode": "raw", "raw": "{\n  \"access_token\": \"...\"\n}"},
            "url": {"raw": "{{base_url}}/api/auth/social/google/", "host": ["{{base_url}}"], "path": ["api", "auth", "social", "google", ""]}
        },
        "response": []
    },
    {
        "name": "POST Apple Auth",
        "request": {
            "method": "POST",
            "header": [{"key": "Content-Type", "value": "application/json"}],
            "body": {"mode": "raw", "raw": "{\n  \"id_token\": \"...\"\n}"},
            "url": {"raw": "{{base_url}}/api/auth/social/apple/", "host": ["{{base_url}}"], "path": ["api", "auth", "social", "apple", ""]}
        },
        "response": []
    }
])

# Spiritual missing
add_missing("3. Spiritual", [
    {
        "name": "GET Popular Videos",
        "request": {
            "method": "GET",
            "url": {"raw": "{{base_url}}/api/spiritual/videos/popular/", "host": ["{{base_url}}"], "path": ["api", "spiritual", "videos", "popular", ""]}
        },
        "response": []
    },
    {
        "name": "POST Toggle Video Bookmark",
        "request": {
            "method": "POST",
            "header": [{"key": "Authorization", "value": "Bearer {{access_token}}"}],
            "url": {"raw": "{{base_url}}/api/spiritual/videos/1/bookmark/", "host": ["{{base_url}}"], "path": ["api", "spiritual", "videos", "1", "bookmark", ""]}
        },
        "response": []
    },
    {
        "name": "GET Bookmarked Videos",
        "request": {
            "method": "GET",
            "header": [{"key": "Authorization", "value": "Bearer {{access_token}}"}],
            "url": {"raw": "{{base_url}}/api/spiritual/videos/bookmarks/", "host": ["{{base_url}}"], "path": ["api", "spiritual", "videos", "bookmarks", ""]}
        },
        "response": []
    }
])

# Journal missing
add_missing("4. Journal", [
    {
        "name": "POST Toggle Journal Archive",
        "request": {
            "method": "POST",
            "header": [{"key": "Authorization", "value": "Bearer {{access_token}}"}],
            "url": {"raw": "{{base_url}}/api/journal/entries/1/archive/", "host": ["{{base_url}}"], "path": ["api", "journal", "entries", "1", "archive", ""]}
        },
        "response": []
    },
    {
        "name": "GET Archived Journal Entries",
        "request": {
            "method": "GET",
            "header": [{"key": "Authorization", "value": "Bearer {{access_token}}"}],
            "url": {"raw": "{{base_url}}/api/journal/archived/", "host": ["{{base_url}}"], "path": ["api", "journal", "archived", ""]}
        },
        "response": []
    }
])

# Community missing
add_missing("6. Community", [
    {
        "name": "DELETE Comment",
        "request": {
            "method": "DELETE",
            "header": [{"key": "Authorization", "value": "Bearer {{access_token}}"}],
            "url": {"raw": "{{base_url}}/api/community/posts/1/comments/", "host": ["{{base_url}}"], "path": ["api", "community", "posts", "1", "comments", ""]}
        },
        "response": []
    },
    {
        "name": "GET User Posts",
        "request": {
            "method": "GET",
            "header": [{"key": "Authorization", "value": "Bearer {{access_token}}"}],
            "url": {"raw": "{{base_url}}/api/community/user/2/posts/", "host": ["{{base_url}}"], "path": ["api", "community", "user", "2", "posts", ""]}
        },
        "response": []
    },
    {
        "name": "GET Following Users",
        "request": {
            "method": "GET",
            "header": [{"key": "Authorization", "value": "Bearer {{access_token}}"}],
            "url": {"raw": "{{base_url}}/api/community/following-users/", "host": ["{{base_url}}"], "path": ["api", "community", "following-users", ""]}
        },
        "response": []
    },
    {
        "name": "POST Report Post",
        "request": {
            "method": "POST",
            "header": [
                {"key": "Content-Type", "value": "application/json"},
                {"key": "Authorization", "value": "Bearer {{access_token}}"}
            ],
            "body": {"mode": "raw", "raw": "{\n  \"post\": 1,\n  \"reason\": \"spam\"\n}"},
            "url": {"raw": "{{base_url}}/api/community/posts/report/", "host": ["{{base_url}}"], "path": ["api", "community", "posts", "report", ""]}
        },
        "response": []
    },
    {
        "name": "GET Today's Community Prompt",
        "request": {
            "method": "GET",
            "header": [{"key": "Authorization", "value": "Bearer {{access_token}}"}],
            "url": {"raw": "{{base_url}}/api/community/prompts/today/", "host": ["{{base_url}}"], "path": ["api", "community", "prompts", "today", ""]}
        },
        "response": []
    }
])

# Notifications missing
add_missing("8. Notifications", [
    {
        "name": "POST Notification Action",
        "request": {
            "method": "POST",
            "header": [{"key": "Authorization", "value": "Bearer {{access_token}}"}],
            "url": {"raw": "{{base_url}}/api/notifications/notifications/1/action/", "host": ["{{base_url}}"], "path": ["api", "notifications", "notifications", "1", "action", ""]}
        },
        "response": []
    },
    {
        "name": "GET/PATCH Notification Settings",
        "request": {
            "method": "GET",
            "header": [{"key": "Authorization", "value": "Bearer {{access_token}}"}],
            "url": {"raw": "{{base_url}}/api/notifications/settings/", "host": ["{{base_url}}"], "path": ["api", "notifications", "settings", ""]}
        },
        "response": []
    }
])

with open("postman.json", "w") as f:
    json.dump(data, f, indent=2)

print("Updated missing endpoints in postman.json successfully.")
