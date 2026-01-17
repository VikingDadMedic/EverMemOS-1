# Conversation Metadata Control Guide

[Home](../../README.md) > [Docs](../README.md) > [Advanced](.) > Metadata Control

> 🚧 **Coming Soon** - This guide is under development

## Overview

Fine-grained control over conversation context and metadata in EverMemOS.

---

## Topics Covered (Planned)

This guide will cover:

- **Conversation metadata structure** - Understanding the metadata model
- **User details management** - Managing comprehensive user information
- **Scene types** - Using scene descriptors (assistant vs group_chat)
- **Timezone handling** - Managing timestamps across timezones
- **Custom metadata fields** - Extending metadata for your use case
- **Metadata updates** - Updating metadata after initial creation
- **Metadata queries** - Leveraging metadata in searches
- **Best practices** - Optimal metadata organization strategies

---

## Current Resources

While this comprehensive guide is being developed, you can refer to these existing resources:

### Documentation
- **[API Usage Guide](../dev_docs/api_usage_guide.md)** - API patterns and metadata examples
- **[Group Chat Format](../../data_format/group_chat/group_chat_format.md)** - Metadata schema reference
- **[Memory API](../api_docs/memory_api.md)** - API endpoints and parameters

### Examples
- **[Usage Examples](../usage/USAGE_EXAMPLES.md)** - Practical metadata usage
- **[Batch Operations](../usage/BATCH_OPERATIONS.md)** - Metadata in batch processing

---

## Quick Reference

### Conversation Metadata Fields

**conversation_meta** object:

```json
{
  "group_id": "unique_group_id",
  "name": "Display Name",
  "description": "Optional description",
  "scene": "work|social|family|company|etc",
  "timezone": "Asia/Shanghai",
  "user_details": {
    "user_id": {
      "full_name": "User Full Name",
      "nickname": "Optional Nickname",
      "role": "Optional Role",
      "age": 25
    }
  }
}
```

### Message Metadata Fields

**conversation_list** item:

```json
{
  "message_id": "unique_message_id",
  "create_time": "2025-02-01T10:00:00+00:00",
  "sender": "user_id",
  "sender_name": "Override Display Name",
  "content": "Message content",
  "mentioned_user": ["user_id_1", "user_id_2"]
}
```

### Scene Types

The `scene` field in `conversation_meta` is an internal descriptor:

- **`work`** - Work-related discussions
- **`company`** - Company or organizational context
- **`social`** - Social gatherings and casual chats
- **`family`** - Family conversations
- **Custom values** - Any string describing the context

**Note**: The command-line `--scene` parameter (`assistant` or `group_chat`) is different - it specifies the extraction pipeline, not the context descriptor.

### Timezone Format

Use IANA timezone names:
- `America/New_York`
- `Europe/London`
- `Asia/Shanghai`
- `Asia/Tokyo`
- `UTC`

Message timestamps should include timezone offset:
- `2025-02-01T10:00:00+00:00` (UTC)
- `2025-02-01T10:00:00+08:00` (Asia/Shanghai)
- `2025-02-01T10:00:00-05:00` (America/New_York)

---

## Example: Rich Metadata

```json
{
  "version": "1.0.0",
  "conversation_meta": {
    "group_id": "product_team_2025",
    "name": "Product Team Daily Standup",
    "description": "Daily standup for product development team",
    "scene": "work",
    "timezone": "America/Los_Angeles",
    "user_details": {
      "pm_alice": {
        "full_name": "Alice Johnson",
        "nickname": "AJ",
        "role": "Product Manager",
        "department": "Product"
      },
      "eng_bob": {
        "full_name": "Bob Smith",
        "role": "Senior Engineer",
        "department": "Engineering",
        "specialization": "Backend"
      },
      "design_carol": {
        "full_name": "Carol Williams",
        "role": "UX Designer",
        "department": "Design"
      }
    }
  },
  "conversation_list": [
    {
      "message_id": "standup_001",
      "create_time": "2025-02-01T09:00:00-08:00",
      "sender": "pm_alice",
      "content": "Good morning team! Let's start our standup.",
      "mentioned_user": ["eng_bob", "design_carol"]
    },
    {
      "message_id": "standup_002",
      "create_time": "2025-02-01T09:01:00-08:00",
      "sender": "eng_bob",
      "sender_name": "Bob (Backend)",
      "content": "Yesterday I completed the API integration. Today working on performance optimization."
    }
  ]
}
```

---

## Feedback & Questions

Have questions about metadata management? We'd love to hear from you!

- **[Open an Issue](https://github.com/EverMind-AI/EverMemOS/issues)** - Report bugs or request features
- **[GitHub Discussions](https://github.com/EverMind-AI/EverMemOS/discussions)** - Ask questions and share ideas

---

## See Also

- [Group Chat Guide](GROUP_CHAT_GUIDE.md) - Multi-participant conversations
- [Group Chat Format Specification](../../data_format/group_chat/group_chat_format.md) - Complete schema
- [Batch Operations](../usage/BATCH_OPERATIONS.md) - Processing with metadata
- [API Documentation](../api_docs/memory_api.md) - API reference
