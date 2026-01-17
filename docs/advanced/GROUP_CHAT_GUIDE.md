# Group Chat Conversations Guide

[Home](../../README.md) > [Docs](../README.md) > [Advanced](.) > Group Chat Guide

> 🚧 **Coming Soon** - This guide is under development

## Overview

Learn how to use EverMemOS to manage group chat conversations with multiple participants.

---

## Topics Covered (Planned)

This guide will cover:

- **Group conversation structure** - How to organize multi-speaker conversations
- **Participant management** - Managing user details and roles
- **Message threading** - Tracking related messages across participants
- **Memory extraction** - Extracting memories from multi-speaker conversations
- **Best practices** - Tips for optimal group memory organization
- **Scene types** - Using different scene descriptors (work, social, family)
- **Metadata management** - Leveraging group metadata for better context

---

## Current Resources

While this comprehensive guide is being developed, you can refer to these existing resources:

### Documentation
- **[Group Chat Format Specification](../../data_format/group_chat/group_chat_format.md)** - Complete data format reference
- **[Batch Operations Guide](../usage/BATCH_OPERATIONS.md)** - How to process group chat data
- **[API Documentation](../api_docs/memory_api.md)** - Memory API for group conversations

### Examples
- **[Usage Examples](../usage/USAGE_EXAMPLES.md#5-batch-operations)** - Group chat examples
- **[Sample Data](../../data/README.md)** - Example group chat data files
- **`data/group_chat_zh.json`** - Chinese group chat sample
- **`data/group_chat_en.json`** - English group chat sample

### Tools
- **`src/run_memorize.py`** - Batch processing script for group chats
- **`demo/extract_memory.py`** - Memory extraction demo

---

## Quick Start

Until the full guide is available, here's a quick start:

### 1. Prepare Group Chat Data

Create a JSON file following the GroupChatFormat:

```json
{
  "version": "1.0.0",
  "conversation_meta": {
    "group_id": "team_001",
    "name": "Engineering Team",
    "user_details": {
      "alice": {"full_name": "Alice Smith", "role": "Engineer"},
      "bob": {"full_name": "Bob Jones", "role": "Manager"}
    }
  },
  "conversation_list": [
    {
      "message_id": "msg_1",
      "create_time": "2025-02-01T10:00:00+00:00",
      "sender": "alice",
      "content": "I completed the feature"
    }
  ]
}
```

### 2. Process Group Chat

```bash
uv run python src/bootstrap.py src/run_memorize.py \
  --input your_group_chat.json \
  --scene group_chat
```

### 3. Query Group Memories

```bash
curl -X GET http://localhost:8001/api/v1/memories/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What did the team discuss?",
    "group_id": "team_001",
    "data_source": "episode",
    "memory_scope": "group",
    "retrieval_mode": "rrf"
  }'
```

---

## Feedback & Questions

Have specific questions about group chat functionality? We'd love to hear from you!

- **[Open an Issue](https://github.com/EverMind-AI/EverMemOS/issues)** - Report bugs or request features
- **[GitHub Discussions](https://github.com/EverMind-AI/EverMemOS/discussions)** - Ask questions and share ideas

---

## See Also

- [Conversation Metadata Control](METADATA_CONTROL.md) - Fine-grained metadata management
- [Batch Operations](../usage/BATCH_OPERATIONS.md) - Processing multiple messages
- [Memory Retrieval Strategies](RETRIEVAL_STRATEGIES.md) - Optimizing search
- [API Documentation](../api_docs/memory_api.md) - Complete API reference
