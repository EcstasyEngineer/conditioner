import discord
from discord.ext import commands
from typing import Any, Dict, List
from datetime import datetime

from features.encounters import load_encounters, load_recent_encounters


class MantraStats(commands.Cog):
    """Presenter cog for mantra statistics (embeds and commands)."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = getattr(bot, "logger", None)

    @commands.command(hidden=True, aliases=["mstats"])  # keep parity with existing alias
    async def mantrastats(self, ctx: commands.Context):
        """Show detailed mantra statistics for enrolled users."""
        embeds = self._build_mantra_stats_embeds()
        for embed in embeds:
            await ctx.send(embed=embed)

    def _build_mantra_stats_embeds(self) -> List[discord.Embed]:
        embeds: List[discord.Embed] = []
        # Use central config to enumerate known users instead of scanning files
        config = getattr(self.bot, 'config', None)
        if not config or not hasattr(config, 'list_user_ids'):
            embeds.append(discord.Embed(
                title="📊 Neural Programming Statistics",
                description="Configuration not available.",
                color=discord.Color.purple()
            ))
            return embeds

        def user_total_points(user_id: int) -> int:
            total = 0
            for e in load_encounters(user_id):
                if e.get("completed", False):
                    total += int(e.get("base_points", 0))
                    total += int(e.get("speed_bonus", 0))
                    total += int(e.get("public_bonus", 0))
            return total

        users_with_mantras: List[tuple[Any, Dict[str, Any]]] = []
        try:
            user_ids = list(config.list_user_ids())
        except Exception:
            user_ids = []

        for user_id in user_ids:
            try:
                cfg = config.get_user(user_id, 'mantra_system', {}) or {}
                has_enc = len(load_encounters(user_id)) > 0
                if not (cfg.get("enrolled") or has_enc):
                    continue
                user = self.bot.get_user(user_id) or type("FakeUser", (), {"id": user_id, "name": f"User_{user_id}", "bot": False})()
                if getattr(user, "bot", False):
                    continue
                users_with_mantras.append((user, cfg))
            except Exception:
                continue

        if not users_with_mantras:
            embeds.append(discord.Embed(
                title="📊 Neural Programming Statistics",
                description="No users have tried the mantra system yet.",
                color=discord.Color.purple()
            ))
            return embeds

        users_with_mantras = [x for x in users_with_mantras if x[1].get("enrolled")]
        users_with_mantras.sort(key=lambda t: user_total_points(t[0].id), reverse=True)

        def recent_list(user_id: int) -> List[Dict[str, Any]]:
            return load_recent_encounters(user_id, limit=5) or []

        current = discord.Embed(
            title="📊 Neural Programming Statistics",
            description=f"Found {len(users_with_mantras)} users with conditioning data",
            color=discord.Color.purple()
        )
        field_count = 0
        for idx, (user, cfg) in enumerate(users_with_mantras):
            last_5 = list(recent_list(user.id))
            info: List[str] = []
            if cfg.get("enrolled"):
                status = "🟢" if cfg.get("online_only") else "⚪"
                time_info = ""
                nxt = cfg.get("next_encounter")
                if nxt and isinstance(nxt, dict) and nxt.get("timestamp"):
                    try:
                        next_time = datetime.fromisoformat(nxt["timestamp"])  # type: ignore[arg-type]
                        now = datetime.now()
                        diff = next_time - now
                        if diff.total_seconds() < 0:
                            if cfg.get("online_only"):
                                status = "🟡"
                            overdue = abs(int(diff.total_seconds()))
                            time_info = f"overdue {overdue//3600}h {(overdue%3600)//60}m"
                        else:
                            upcoming = int(diff.total_seconds())
                            time_info = f"next in {upcoming//3600}h {(upcoming%3600)//60}m"
                    except Exception:
                        time_info = "scheduling error"
                else:
                    time_info = "no encounter scheduled"
                info.append(f"**Status:** {status} {time_info}")
            else:
                info.append("**Status:** 🔴 Inactive")

            all_encs = load_encounters(user.id)
            total = len(all_encs)
            if total > 0:
                completed = sum(1 for e in all_encs if e.get("completed", False))
                info.append(f"**All Time:** {completed}/{total} ({(completed/total*100):.1f}%)")

            if cfg.get("enrolled"):
                info.append(f"**Settings:** {cfg.get('subject', 'puppet')}/{cfg.get('controller', 'Master')}")
                if cfg.get("themes"):
                    info.append(f"**Programming Modules:** {', '.join(cfg['themes'])}")
                info.append(f"**Transmission Rate:** {float(cfg.get('frequency', 1.0)):.2f}/day")

            if last_5:
                info.append("\n**Recent Programming:**")
                for i, enc in enumerate(reversed(last_5), 1):
                    try:
                        enc_time = datetime.fromisoformat(enc["timestamp"])  # type: ignore[arg-type]
                        time_str = enc_time.strftime("%b %d %H:%M")
                        if enc.get("completed"):
                            total_pts = int(enc.get("base_points", 0)) + int(enc.get("speed_bonus", 0)) + int(enc.get("public_bonus", 0))
                            status = f"✅ {enc.get('theme', 'unknown')} - {total_pts}pts ({enc.get('response_time', '?')}s)"
                            if enc.get("was_public"):
                                status = "🌍 " + status
                        else:
                            status = f"❌ {enc.get('theme', 'unknown')} - MISSED"
                        info.append(f"{i}. {time_str}: {status}")
                    except Exception:
                        continue
            else:
                info.append("\n*No recent programming sequences*")

            if field_count >= 24:
                embeds.append(current)
                current = discord.Embed(title="📊 Neural Programming Statistics (Continued)", color=discord.Color.purple())
                field_count = 0

            current.add_field(name=getattr(user, "name", str(user.id)), value="\n".join(info)[:1024], inline=False)
            field_count += 1

            if idx < len(users_with_mantras) - 1 and field_count < 24:
                current.add_field(name="\u200b", value="─────────────────────────────", inline=False)
                field_count += 1

        if field_count > 0:
            embeds.append(current)

        return embeds


async def setup(bot):
    await bot.add_cog(MantraStats(bot))
