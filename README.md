# Ian's Claude Skills

Personal collection of Claude Code skills distributed as a plugin marketplace.

## Skills

### learning-mode

Teaching-first approach: Claude explains concepts deeply and helps you write the
solution yourself instead of handing over finished code.

### research

Answers technical questions by reading current official documentation instead
of relying on memory, then hands back a summary, a worked example, and precise
citations.

## Installation

```bash
# Add the marketplace
claude plugin marketplace add YOUR_GITHUB_USERNAME/claude-skills

# Install a skill
claude plugin install learning-mode@claude-skills
claude plugin install research@claude-skills
```

## Development

```bash
# Test plugin structure locally
claude plugin list --plugin-dir plugins/learning-mode

# Create a version tag (after pushing to GitHub)
cd plugins/learning-mode
claude plugin tag --push
```