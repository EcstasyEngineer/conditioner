# Utils Refactor Manifest

## Current Status: Mantras Cog Refactor
- **Original Size:** 1,514 lines
- **Current Size:** 1,264 lines  
- **Reduction:** 250 lines (16.5%)
- **Target:** ~600 lines (60% reduction)

---

## ✅ COMPLETED: Functions in Utils

### utils/encounters.py (140 lines)
- `log_encounter(user_id, encounter)` - ✅ Moved & Used
- `load_encounters(user_id)` - ✅ Moved & Used  
- `load_recent_encounters(user_id, days=7)` - ✅ Moved & Used
- `calculate_user_streak_from_history(user_id)` - ✅ Moved & Used
- `get_user_encounter_stats(user_id)` - ✅ New helper function

### utils/delivery.py (180 lines)
- `DeliveryTracker` class - ✅ Created (ready for gacha)
- `send_dm_with_media(user, content, media_path, embed)` - ✅ Created (ready for gacha)
- `select_random_media_file(directory_path)` - ✅ Created (ready for gacha)
- `schedule_auto_delete(message, delay_seconds)` - ✅ Created (ready for gacha)
- `get_file_count_in_directory(directory_path)` - ✅ Created (ready for gacha)
- `load_file_counts_from_json(json_path)` - ✅ Created (ready for gacha)
- `send_dm_with_auto_delete(...)` - ✅ Created (ready for gacha)

### utils/mantras.py (300 lines)
- `calculate_speed_bonus(response_time_seconds)` - ✅ Moved & Used
- `get_streak_bonus(streak_count)` - ✅ Moved & Used
- `check_mantra_match(user_response, expected_mantra)` - ✅ Moved & Used
- `format_mantra_text(mantra_text, subject, controller)` - ✅ Moved & Used
- `select_mantra_from_themes(themes, available_themes)` - ✅ Moved & Used
- `schedule_next_encounter(config, available_themes, first_enrollment)` - ✅ Moved & Used
- `adjust_user_frequency(config, success, response_time)` - ✅ Moved & Used
- `validate_mantra_config(config)` - ✅ Moved & Used
- `generate_mantra_summary(bot, guild_members)` - ✅ Created (ready to use)
- `generate_mantra_stats_embeds(bot, guild_members)` - ✅ Created (ready to use)

### utils/points.py (80 lines)
- `get_points(bot, user)` - ✅ Moved & Used
- `add_points(bot, user, amount)` - ✅ Moved & Used
- `set_points(bot, user, amount)` - ✅ Moved & Used
- `transfer_points(bot, from_user, to_user, amount)` - ✅ Created

---

## 🎯 TODO: Functions Still in Mantras Cog to Move

### Large Admin Commands (Ready to Move - ~200 lines)
- `mantrasummary(ctx)` - **Ready to move** → Use `generate_mantra_summary()`
- `mantrastats(ctx)` - **Ready to move** → Use `generate_mantra_stats_embeds()`

### Command Implementation Helpers (~280 lines)
- `enroll_user(interaction, themes_str, subject, controller)` - **Can move** → `utils/mantras.py`
- `show_status(interaction)` - **Can move** → `utils/mantras.py`  
- `update_settings(interaction, subject, controller, themes_list, online_only)` - **Can move** → `utils/mantras.py`
- `disable_mantras(interaction)` - **Can move** → `utils/mantras.py`

### Core Cog Functions (Keep in Cog)
- `__init__(bot)` - **Keep** (Discord integration)
- `cog_load()` - **Keep** (Discord lifecycle)
- `cog_unload()` - **Keep** (Discord lifecycle)
- `calculate_streaks_from_history()` - **Keep** (uses cog state)
- `load_themes()` - **Keep** (loads from files into cog)
- `_generate_theme_choices()` - **Keep** (Discord-specific)
- `get_user_mantra_config(user)` - **Keep** (uses bot.config)
- `save_user_mantra_config(user, config)` - **Keep** (uses bot.config)
- `update_streak(user_id, success)` - **Keep** (manages cog state)
- `should_send_mantra(user)` - **Keep** (complex Discord logic)

### Discord Event Handlers (Keep in Cog)
- `mantra_delivery()` - **Keep** (Discord task loop)
- `before_mantra_delivery()` - **Keep** (Discord lifecycle)  
- `on_message(message)` - **Keep** (Discord event handler)

### Slash Commands (Keep in Cog)
- `mantra_enroll()` - **Keep** (Discord command)
- `mantra_status()` - **Keep** (Discord command)
- `mantra_settings()` - **Keep** (Discord command)
- `mantra_disable()` - **Keep** (Discord command)
- `mantra_list_modules()` - **Keep** (Discord command)
- `mantra_modules()` - **Keep** (Discord command)

### UI Components (Keep in Cog)
- `ThemeSelectView` class - **Keep** (Discord UI)

---

## 📋 NEXT EXTRACTION TARGETS (Priority Order)

### Phase 1: Admin Commands (High Impact)
1. **Replace `mantrasummary`** with utils call → Save ~100 lines
2. **Replace `mantrastats`** with utils call → Save ~100 lines

### Phase 2: Command Helpers (Medium Impact)  
3. **Move `enroll_user`** to utils → Save ~120 lines
4. **Move `show_status`** to utils → Save ~90 lines
5. **Move `update_settings`** to utils → Save ~50 lines
6. **Move `disable_mantras`** to utils → Save ~20 lines

**Total Potential Savings:** ~480 lines
**Final Target Size:** ~784 lines (48% reduction from original)

---

## 📊 Progress Tracking

- [x] **Phase 0:** Core helpers moved (250 lines saved) ✅
- [ ] **Phase 1:** Admin commands replaced (200 lines to save)
- [ ] **Phase 2:** Command helpers moved (280 lines to save)

**Current:** 1,264 lines → **Target:** ~784 lines → **Remaining:** 480 lines to extract