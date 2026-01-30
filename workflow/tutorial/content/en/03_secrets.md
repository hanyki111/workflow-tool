# Security & Secrets

Some workflow actions require user approval. This section explains the security system.

## USER-APPROVE Items

Certain checklist items are marked `[USER-APPROVE]`:

```yaml
checklist:
  - "Review design document"
  - "[USER-APPROVE] Approve for production deployment"
  - "Update documentation"
```

These items require a secret token to check off, ensuring a human has explicitly approved the action.

## Setting Up Secrets

### Generate a Secret

```bash
flow secret-generate
```

Interactive prompt:
```
Enter your secret phrase: ********
Confirm secret phrase: ********

Secret hash saved to .workflow/secret
Use this secret with --token flag for USER-APPROVE items
```

### Security Notes

1. **The secret is hashed**: Only the SHA-256 hash is stored, not the plaintext
2. **Keep it private**: Don't commit `.workflow/secret` to git
3. **Remember your phrase**: There's no recovery mechanism

## Using Tokens

When checking USER-APPROVE items:

```bash
# Will fail without token
flow check 2
# Error: Item 2 requires USER-APPROVE token

# Provide the token
flow check 2 --token "your-secret-phrase"
# Success: Checked items: 2
```

## Audit Trail

All USER-APPROVE actions are logged:

```bash
cat .workflow/audit.log
```

Example log:
```
2024-01-15T10:30:00 USER-APPROVE check item 2 (Production deployment)
2024-01-15T10:30:00 Evidence: Reviewed by security team
```

## Best Practices

1. **Use strong secrets**: Long, random phrases
2. **Don't share**: Each team member should have their own secret
3. **Rotate periodically**: Generate new secrets for long projects
4. **Add evidence**: Document why you're approving

```bash
flow check 2 --token "secret" --evidence "Approved after security review by @alice"
```

## Gitignore Setup

Add to `.gitignore`:
```
.workflow/secret
.workflow/audit.log
```

Next: Learn about advanced features!
