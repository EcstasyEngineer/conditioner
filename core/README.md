Core layer (infrastructure)

- config.py: JSON-based config service (guild/user/global) with debounced writes and external reload.
- error_handler.py: Error routing with per-guild and global channels, plus rate limiting.
- permissions.py: Shared permission checks for commands and interactions.
- media_migration.py: Startup migration utilities.
