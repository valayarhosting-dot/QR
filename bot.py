import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta
import qrcode
from io import BytesIO

TOKEN = "YOUR_BOT_TOKEN"
PAYMENT_QR_LINK = "https://example.com/your-qr.png"  # replace with your static QR if needed

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="/", intents=intents)
        self.invites = {}

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Slash commands synced")

bot = MyBot()

# -------- EVENTS -------- #
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    for guild in bot.guilds:
        bot.invites[guild.id] = await guild.invites()

@bot.event
async def on_member_join(member):
    invites_before = bot.invites.get(member.guild.id, [])
    invites_after = await member.guild.invites()

    used_invite = None
    for invite in invites_before:
        for new_invite in invites_after:
            if invite.code == new_invite.code and invite.uses < new_invite.uses:
                used_invite = invite
                break

    bot.invites[member.guild.id] = invites_after

    channel = discord.utils.get(member.guild.text_channels, name="welcome")
    if channel:
        if used_invite:
            await channel.send(
                f"🎉 Welcome {member.mention}! Invited by **{used_invite.inviter}** using invite `{used_invite.code}`"
            )
        else:
            await channel.send(f"🎉 Welcome {member.mention}!")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # Link blocker
    if "http://" in message.content or "https://" in message.content:
        await message.delete()
        await message.channel.send(
            f"🚫 {message.author.mention}, links are not allowed here!",
            delete_after=5
        )
    
    await bot.process_commands(message)

# -------- SLASH COMMANDS -------- #
# Static Payment QR
@bot.tree.command(name="pay", description="Show payment QR code")
async def pay(interaction: discord.Interaction):
    embed = discord.Embed(
        title="💳 Payment",
        description="Scan this QR code to pay.",
        color=discord.Color.green()
    )
    embed.set_image(url=PAYMENT_QR_LINK)
    await interaction.response.send_message(embed=embed)

# Dynamic QR /qr [amount]
@bot.tree.command(name="qr", description="Generate payment QR for a specific amount")
@app_commands.describe(amount="Amount to generate QR code for")
async def qr(interaction: discord.Interaction, amount: float):
    payment_link = f"https://example-payment.com/pay?amount={amount}"  # replace with your payment system URL

    qr_img = qrcode.make(payment_link)
    buffer = BytesIO()
    qr_img.save(buffer, format="PNG")
    buffer.seek(0)

    file = discord.File(fp=buffer, filename="payment.png")
    embed = discord.Embed(
        title="💳 Payment QR",
        description=f"Scan this QR to pay **{amount}** units.",
        color=discord.Color.green()
    )
    embed.set_image(url="attachment://payment.png")
    await interaction.response.send_message(embed=embed, file=file)

# Announce
@bot.tree.command(name="announce", description="Send announcement to #announcements")
@app_commands.checks.has_permissions(administrator=True)
async def announce(interaction: discord.Interaction, message: str):
    channel = discord.utils.get(interaction.guild.text_channels, name="announcements")
    if channel:
        embed = discord.Embed(
            title="📢 Announcement",
            description=message,
            color=discord.Color.blue()
        )
        await channel.send(embed=embed)
        await interaction.response.send_message("✅ Announcement sent!", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ #announcements channel not found.", ephemeral=True)

# Purge
@bot.tree.command(name="purge", description="Delete up to 200 messages")
@app_commands.checks.has_permissions(manage_messages=True)
async def purge(interaction: discord.Interaction, amount: int):
    if amount > 200:
        await interaction.response.send_message("⚠️ You can only purge up to 200 messages.", ephemeral=True)
        return
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.response.send_message(f"🧹 Deleted {len(deleted)} messages.", ephemeral=True)

# Kick
@bot.tree.command(name="kick", description="Kick a member from the server")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"👢 {member.mention} has been kicked. Reason: {reason}")

# Ban
@bot.tree.command(name="ban", description="Ban a member from the server")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await member.ban(reason=reason)
    await interaction.response.send_message(f"🔨 {member.mention} has been banned. Reason: {reason}")

# Unban
@bot.tree.command(name="unban", description="Unban a member by username#discriminator")
@app_commands.checks.has_permissions(ban_members=True)
async def unban(interaction: discord.Interaction, user: str):
    banned_users = await interaction.guild.bans()
    name, discriminator = user.split("#")
    for ban_entry in banned_users:
        if (ban_entry.user.name, ban_entry.user.discriminator) == (name, discriminator):
            await interaction.guild.unban(ban_entry.user)
            await interaction.response.send_message(f"✅ Unbanned {user}")
            return
    await interaction.response.send_message(f"⚠️ User {user} not found in bans.", ephemeral=True)

# Mute (timeout)
@bot.tree.command(name="mute", description="Mute a member (timeout in minutes)")
@app_commands.checks.has_permissions(moderate_members=True)
async def mute(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason provided"):
    duration = timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    await interaction.response.send_message(f"🔇 {member.mention} has been muted for {minutes} minutes. Reason: {reason}")

# Unmute
@bot.tree.command(name="unmute", description="Remove timeout from a member")
@app_commands.checks.has_permissions(moderate_members=True)
async def unmute(interaction: discord.Interaction, member: discord.Member):
    await member.timeout(None)
    await interaction.response.send_message(f"✅ {member.mention} has been unmuted.")

# Help command
@bot.tree.command(name="help", description="Show all bot commands")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📜 Bot Commands",
        description="Here are all the available commands:",
        color=discord.Color.purple()
    )
    embed.add_field(name="/pay", value="Show static payment QR code", inline=False)
    embed.add_field(name="/qr [amount]", value="Generate dynamic payment QR for specified amount", inline=False)
    embed.add_field(name="/announce [message]", value="Send announcement to #announcements (Admin only)", inline=False)
    embed.add_field(name="/purge [amount]", value="Delete up to 200 messages (Manage Messages permission required)", inline=False)
    embed.add_field(name="/kick [member] [reason]", value="Kick a member (Kick Members permission required)", inline=False)
    embed.add_field(name="/ban [member] [reason]", value="Ban a member (Ban Members permission required)", inline=False)
    embed.add_field(name="/unban [username#0000]", value="Unban a member by tag (Ban Members permission required)", inline=False)
    embed.add_field(name="/mute [member] [minutes] [reason]", value="Mute a member (Moderate Members permission required)", inline=False)
    embed.add_field(name="/unmute [member]", value="Unmute a member (Moderate Members permission required)", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# -------- RUN -------- #
bot.run(TOKEN)