# GitHub Labels Guide

This document describes the label system used in the ai-conditioner-discord repository.

## Label Categories

### Priority Labels
Indicate the urgency and importance of issues:
- `priority: critical` - Urgent issue requiring immediate attention (e.g., bot is down, security vulnerability)
- `priority: high` - High priority issue that should be addressed soon
- `priority: medium` - Medium priority issue for normal development flow
- `priority: low` - Low priority issue that can wait
- `priority: backlog` - Low priority, may be addressed in the future

### Effort Sizing Labels
Estimate the amount of work required:
- `effort: trivial` - Less than 1 hour of work
- `effort: small` - 1-4 hours of work
- `effort: medium` - 4-8 hours of work
- `effort: large` - 1-3 days of work
- `effort: x-large` - More than 3 days of work

### Complexity Labels
Indicate the technical difficulty and knowledge required:
- `complexity: beginner` - Good first issue, minimal Discord.py knowledge needed
- `complexity: intermediate` - Requires Discord.py experience
- `complexity: advanced` - Requires deep Discord.py and async programming knowledge
- `complexity: expert` - Requires architectural changes or complex system design

### Component Labels
Identify which part of the bot is affected:
- `component: mantras` - Mantra system (hypnotic content delivery)
- `component: points` - Points and rewards system
- `component: gacha` - Gacha game mechanics
- `component: logging` - Logging and monitoring functionality
- `component: admin` - Admin commands and permissions
- `component: dev` - Developer tools and debugging features
- `component: counter` - Counter system
- `component: player` - Media player functionality
- `component: setrole` - Role management system
- `component: config` - Configuration and settings management
- `component: api` - External API integrations
- `component: database` - Database and data persistence
- `component: commands` - Command handling and slash commands
- `component: cogs` - Cog system and dynamic loading

### Discord-Specific Labels
For Discord API related issues:
- `discord: permissions` - Discord permission issues
- `discord: rate-limits` - Discord API rate limiting problems
- `discord: intents` - Discord gateway intents configuration
- `discord: interactions` - Slash commands and interaction handling

### Technical Labels
For code quality and maintenance:
- `refactor` - Code refactoring needed
- `security` - Security-related issue
- `performance` - Performance optimization needed
- `tech-debt` - Technical debt to be addressed
- `maintenance` - Regular maintenance tasks
- `migration` - Migration-related tasks

### Project-Specific Labels
- `hypnosis` - Hypnosis content and mechanics
- `moderation` - Server moderation features
- `automation` - Automation and scheduled tasks
- `testing` - Testing related issues
- `feature request` - New feature or enhancement request

### Standard GitHub Labels
- `bug` - Something isn't working
- `documentation` - Improvements or additions to documentation
- `duplicate` - This issue or pull request already exists
- `enhancement` - New feature or request
- `good first issue` - Good for newcomers
- `help wanted` - Extra attention is needed
- `invalid` - This doesn't seem right
- `question` - Further information is requested
- `wontfix` - This will not be worked on

## Using Labels Effectively

### For Issues
1. **Always add a priority label** to help with triage
2. **Add both effort and complexity labels** to help contributors find suitable tasks
3. **Add relevant component labels** to identify which systems are affected
4. **Use multiple labels** when appropriate (e.g., `component: mantras` + `performance` + `priority: high`)

### For Pull Requests
1. **Copy relevant labels from the linked issue**
2. **Add technical labels** if the PR involves refactoring, performance, etc.
3. **Update labels** as the PR scope changes

### Examples

**Example 1: Bug Report**
- `bug`
- `priority: high`
- `component: mantras`
- `effort: small`
- `complexity: intermediate`

**Example 2: Feature Request**
- `feature request`
- `priority: medium`
- `component: gacha`
- `effort: large`
- `complexity: advanced`

**Example 3: Performance Issue**
- `performance`
- `priority: critical`
- `component: database`
- `effort: medium`
- `complexity: expert`

## Label Maintenance

To recreate or update labels, run:
```bash
bash scripts/create_github_labels.sh
```

This script is idempotent and can be run multiple times safely.