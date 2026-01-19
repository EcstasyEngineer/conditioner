"""
Temporary cog to analyze voice session telemetry from log channel history.
"""
from discord.ext import commands
import discord
from datetime import datetime, timedelta
import re
from collections import defaultdict


class VoiceTelemetry(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="voice_telemetry")
    @commands.is_owner()
    async def voice_telemetry(self, ctx, channel_id: int = 1346989091518021692, since_days: int = 36):
        """
        Analyze voice session durations from log channel history.

        Usage: !voice_telemetry [channel_id] [days_back]
        Default: channel 1346989091518021692, last 36 days (since Nov 24)
        """
        await ctx.send(f"Fetching messages from <#{channel_id}> for the last {since_days} days...")

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return await ctx.send(f"Channel {channel_id} not found")

        since = datetime.utcnow() - timedelta(days=since_days)

        # Patterns for voice events
        join_pattern = re.compile(r"^(.+?) joined \*\*(.+?)\*\*$")
        leave_pattern = re.compile(r"^(.+?) left \*\*(.+?)\*\*$")
        move_pattern = re.compile(r"^(.+?) moved from \*\*(.+?)\*\* to \*\*(.+?)\*\*$")

        # Track sessions: {user: {channel: join_time}}
        active_sessions = defaultdict(dict)
        completed_sessions = []  # [(user, channel, start, end, duration_minutes)]

        messages = []
        async for msg in channel.history(after=since, limit=None, oldest_first=True):
            messages.append(msg)

        await ctx.send(f"Processing {len(messages)} messages...")

        for msg in messages:
            content = msg.content
            timestamp = msg.created_at

            # Check for join
            match = join_pattern.match(content)
            if match:
                user, voice_channel = match.groups()
                active_sessions[user][voice_channel] = timestamp
                continue

            # Check for leave
            match = leave_pattern.match(content)
            if match:
                user, voice_channel = match.groups()
                if user in active_sessions and voice_channel in active_sessions[user]:
                    start = active_sessions[user].pop(voice_channel)
                    duration = (timestamp - start).total_seconds() / 60
                    completed_sessions.append((user, voice_channel, start, timestamp, duration))
                continue

            # Check for move (leave old, join new)
            match = move_pattern.match(content)
            if match:
                user, from_channel, to_channel = match.groups()
                # End session in old channel
                if user in active_sessions and from_channel in active_sessions[user]:
                    start = active_sessions[user].pop(from_channel)
                    duration = (timestamp - start).total_seconds() / 60
                    completed_sessions.append((user, from_channel, start, timestamp, duration))
                # Start session in new channel
                active_sessions[user][to_channel] = timestamp
                continue

        # Analyze results
        if not completed_sessions:
            return await ctx.send("No completed voice sessions found in the time range.")

        # Group by channel
        by_channel = defaultdict(list)
        for user, channel_name, start, end, duration in completed_sessions:
            by_channel[channel_name].append((user, duration))

        # Build report
        report = ["**Voice Session Analysis**\n"]

        for channel_name, sessions in sorted(by_channel.items(), key=lambda x: -len(x[1])):
            durations = [d for _, d in sessions]
            total = sum(durations)
            avg = total / len(durations) if durations else 0
            max_d = max(durations) if durations else 0
            min_d = min(durations) if durations else 0

            # Sessions over 5 min (meaningful)
            over_5 = [d for d in durations if d >= 5]
            over_30 = [d for d in durations if d >= 30]

            report.append(f"**{channel_name}** ({len(sessions)} sessions)")
            report.append(f"  Total time: {total:.0f} min ({total/60:.1f} hrs)")
            report.append(f"  Avg: {avg:.1f} min | Min: {min_d:.1f} min | Max: {max_d:.1f} min")
            report.append(f"  Sessions ≥5min: {len(over_5)} | ≥30min: {len(over_30)}")

            # Top users by time
            user_totals = defaultdict(float)
            for user, duration in sessions:
                user_totals[user] += duration
            top_users = sorted(user_totals.items(), key=lambda x: -x[1])[:5]
            if top_users:
                report.append(f"  Top users: {', '.join(f'{u} ({t:.0f}m)' for u, t in top_users)}")
            report.append("")

        # Duration distribution
        all_durations = [d for _, _, _, _, d in completed_sessions]
        buckets = [0, 5, 15, 30, 60, 120, float('inf')]
        bucket_labels = ["<5m", "5-15m", "15-30m", "30-60m", "1-2hr", ">2hr"]
        distribution = []
        for i in range(len(buckets) - 1):
            count = len([d for d in all_durations if buckets[i] <= d < buckets[i+1]])
            distribution.append(f"{bucket_labels[i]}: {count}")

        report.append("**Duration Distribution**")
        report.append("  " + " | ".join(distribution))

        # Sub-5-minute breakdown (in seconds)
        sub_5m = [d * 60 for d in all_durations if d < 5]  # convert to seconds
        sub_buckets = [0, 15, 30, 60, 120, 180, 300]
        sub_labels = ["<15s", "15-30s", "30s-1m", "1-2m", "2-3m", "3-5m"]
        sub_distribution = []
        for i in range(len(sub_buckets) - 1):
            count = len([s for s in sub_5m if sub_buckets[i] <= s < sub_buckets[i+1]])
            sub_distribution.append(f"{sub_labels[i]}: {count}")

        report.append("")
        report.append("**Sub-5-minute breakdown**")
        report.append("  " + " | ".join(sub_distribution))

        # Send report
        full_report = "\n".join(report)
        if len(full_report) > 2000:
            # Split into chunks
            for i in range(0, len(full_report), 1900):
                await ctx.send(full_report[i:i+1900])
        else:
            await ctx.send(full_report)


async def setup(bot):
    await bot.add_cog(VoiceTelemetry(bot))
