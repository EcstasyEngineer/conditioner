def is_admin(ctx):
    """Check if user is server admin (bot admin, Discord admin, or server owner)."""
    if ctx.guild is None:
        return False
    
    # Check if user is in bot's admin list for this guild
    bot = ctx.bot
    admins = bot.config.get(ctx, "admins", [])
    if ctx.author.id in admins:
        return True
    
    # Check Discord server permissions
    if ctx.author.guild_permissions.administrator or ctx.author == ctx.guild.owner:
        return True
    
    return False

def is_superadmin(ctx):
    """Check if user is global superadmin."""
    bot = ctx.bot
    superadmins = bot.config.get_global("superadmins", [])
    return ctx.author.id in superadmins