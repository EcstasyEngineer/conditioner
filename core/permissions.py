import discord

def is_admin(ctx):
    """Check if user is server admin (bot admin, Discord admin, or server owner)."""
    if is_superadmin(ctx):
        return True

    if ctx.guild is None:
        return False
    
    bot = ctx.bot
    admins = bot.config.get(ctx, "admins", [])
    if ctx.author.id in admins:
        return True
    
    if ctx.author.guild_permissions.administrator or ctx.author == ctx.guild.owner:
        return True
    
    return False

def is_superadmin(ctx):
    """Check if user is global superadmin."""
    bot = ctx.bot
    superadmins = bot.config.get_global("superadmins", [])
    return ctx.author.id in superadmins


def is_admin_interaction(interaction: "discord.Interaction") -> bool:
    """Admin check for slash commands using Interaction."""
    bot = interaction.client
    user = interaction.user
    guild = interaction.guild

    superadmins = bot.config.get_global("superadmins", []) if hasattr(bot, "config") else []
    if user.id in superadmins:
        return True

    if guild is None:
        return False

    admins = bot.config.get(guild, "admins", []) if hasattr(bot, "config") else []
    if user.id in admins:
        return True

    if user.guild_permissions.administrator or user == guild.owner:
        return True

    return False
