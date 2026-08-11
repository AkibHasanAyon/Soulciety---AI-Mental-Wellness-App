# Chat System API Documentation

This document outlines the API endpoints available for the Soulciety Chat System. All endpoints require authentication (`IsAuthenticated` permission class).

**Base Path:** `/api/`

---

## 1. Conversations

### 1.1 List / Create Conversations
**Endpoint:** `/api/chat/conversations/`  
**Methods:** `GET`, `POST` 

#### `GET` - List Active Conversations
Retrieves a list of all active conversations for the currently authenticated user.

**Payload:** None
**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "title": "New Conversation",
    "created_at": "2026-03-30T10:00:00Z",
    "updated_at": "2026-03-30T10:00:00Z",
    "last_message": {
      "id": 42,
      "role": "ai",
      "content": "Hello, how can I assist you today?",
      "created_at": "2026-03-30T10:05:00Z"
    },
    "message_count": 5
  }
]
```

#### `POST` - Create a New Conversation
Creates a new conversation instance for the user.

**Payload:** None
**Response:** `201 Created`
```json
{
  "id": 2,
  "title": "New Conversation",
  "created_at": "2026-03-30T10:00:00Z",
  "updated_at": "2026-03-30T10:00:00Z",
  "last_message": null,
  "message_count": 0
}
```

---

### 1.2 Conversation Detail
**Endpoint:** `/api/chat/conversations/<int:pk>/`  
**Methods:** `GET`, `DELETE` 

#### `GET` - Retrieve a Conversation
Retrieves details of a specific conversation.

**Payload:** None
**Response:** `200 OK`
```json
{
  "id": 1,
  "title": "New Conversation",
  "created_at": "2026-03-30T10:00:00Z",
  "updated_at": "2026-03-30T10:00:00Z",
  "last_message": {
    "id": 42,
    "role": "ai",
    "content": "Hello, how can I assist you today?",
    "created_at": "2026-03-30T10:05:00Z"
  },
  "message_count": 5
}
```

#### `DELETE` - Delete a Conversation
Deletes a specific conversation permanently.

**Payload:** None
**Response:** `204 No Content`

---

## 2. Messages

### 2.1 List / Send Messages
**Endpoint:** `/api/chat/conversations/<int:conversation_id>/messages/`  
**Methods:** `GET`, `POST` 

#### `GET` - List Messages
Retrieves all messages for a specific conversation in ascending chronological order. Uses PageNumberPagination (20 items per page).

**Payload:** None
**Response:** `200 OK`
```json
{
  "count": 45,
  "next": "http://domain.com/api/chat/conversations/1/messages/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "role": "user",
      "content": "I am feeling stressed.",
      "created_at": "2026-03-30T09:00:00Z"
    },
    {
      "id": 2,
      "role": "ai",
      "content": "I understand. Let's take a deep breath...",
      "created_at": "2026-03-30T09:01:00Z"
    }
  ]
}
```

#### `POST` - Send Message & Trigger AI
Sends a user message to the conversation and triggers an asynchronous AI task (Celery) to generate a reply. 

*Note: This endpoint is explicitly rate-limited to 30 requests per day per user block-free (the code checks was_limited to return a 429 response).*

**Payload:**
```json
{
  "content": "I need some advice on anxiety."
}
```

**Success Response:** `202 Accepted`
```json
{
  "message": "Message sent. Soulciety AI is reflecting on your words...",
  "user_message": {
    "id": 10,
    "role": "user",
    "content": "I need some advice on anxiety.",
    "created_at": "2026-03-30T09:15:00Z"
  },
  "ai_thinking": true
}
```

**Rate Limited Response:** `429 Too Many Requests`
```json
{
  "error": "Daily message limit reached",
  "detail": "You can send up to 10 AI messages per day. Please try again tomorrow.",
  "limit": "10/day"
}
```

---

### 2.2 Retrieve Latest Message
**Endpoint:** `/api/chat/conversations/<int:conversation_id>/messages/latest/`  
**Methods:** `GET` 

#### `GET` - Latest Message
Retrieves the single most recent message in the specified conversation. Helpful for real-time polling or UI updates without fetching the whole history.

**Payload:** None
**Response (if message exists):** `200 OK`
```json
{
  "id": 42,
  "role": "ai",
  "content": "Here is a spiritual insight for your day...",
  "created_at": "2026-03-30T09:20:00Z"
}
```
**Response (if no messages yet):** `200 OK`
```json
{
  "message": "No messages yet"
}
```
