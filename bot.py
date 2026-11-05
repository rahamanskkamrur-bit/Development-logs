import asyncio, datetime, os, time, aiohttp
from aiohttp import web
import discord
from discord.ext import commands

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
STAFF_ROLE_IDS = [1567026563369664590]
DEVLOG_BANNER_URL = "https://images.unsplash.com/photo-1555066931-4365d14bab8c?auto=format&fit=crop&w=1200&q=80"
START_TIME = time.time()
BOT_STATUS = "Starting..."

async def handle_ping(req):
    up = int((time.time() - START_TIME) // 60)
    return web.Response(text=f"DevLog Bot 24/7 | Uptime: {up}m | Status: {BOT_STATUS}")

async def run_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    await web.TCPSite(runner, "0.0.0.0", port).start()

async def self_ping_loop():
    await asyncio.sleep(20)
    url = os.environ.get("RENDER_EXTERNAL_URL") or f"http://127.0.0.1:{os.environ.get('PORT', 10000)}/"
    async with aiohttp.ClientSession() as s:
        while True:
            try:
                async with s.get(url, timeout=10): pass
            except Exception: pass
            await asyncio.sleep(240)

def is_dev(m: discord.Member) -> bool:
    return m.guild_permissions.administrator or m.guild_permissions.manage_guild or any(r.id in STAFF_ROLE_IDS for r in m.roles)

def format_bullets(text: str) -> str:
    lines = [line.strip().lstrip("-•* ") for line in text.strip().splitlines() if line.strip()]
    return "\n".join(f"• {line}" for line in lines) if lines else "None"

class DevLogModal(discord.ui.Modal, title="🛠️ Post Official Development Log"):
    def __init__(self, target_channel: discord.TextChannel, ping_text: str = ""):
        super().__init__()
        self.target_channel = target_channel
        self.ping_text = ping_text

        self.ver_title = discord.ui.TextInput(
            label="Update Version & Title",
            placeholder="e.g. Update v1.5.0 — New Systems & Bug Fixes",
            required=True,
            max_length=120,
        )
        self.added = discord.ui.TextInput(
            label="✨ Added / New Features (One per line)",
            style=discord.TextStyle.paragraph,
            placeholder="- Added new Ban Appeal system\n- Added 24/7 Uptime monitor",
            required=True,
            max_length=900,
        )
        self.changed_fixed = discord.ui.TextInput(
            label="🔧 Changed / Bug Fixes (One per line)",
            style=discord.TextStyle.paragraph,
            placeholder="- Fixed ticket channel permissions\n- Improved AI response speed",
            required=False,
            max_length=900,
        )
        self.notes = discord.ui.TextInput(
            label="📌 Developer Notes (Optional)",
            style=discord.TextStyle.paragraph,
            placeholder="Report any bugs in a support ticket!",
            required=False,
            max_length=500,
        )
        self.banner = discord.ui.TextInput(
            label="🖼️ Custom Image URL (Optional)",
            placeholder="Leave blank to use default coding banner",
            required=False,
            max_length=300,
        )
        for item in (self.ver_title, self.added, self.changed_fixed, self.notes, self.banner):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%B %d, %Y")

        emb = discord.Embed(
            title=f"🛠️ {self.ver_title.value}",
            description=f"📅 **Release Date:** `{now_str}`\n👨‍💻 **Published By:** {interaction.user.mention}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=discord.Color.from_rgb(43, 182, 115),
        )
        emb.add_field(name="✨ What's New / Added", value=format_bullets(self.added.value), inline=False)

        if self.changed_fixed.value.strip():
            emb.add_field(name="🔧 Changes & Bug Fixes", value=format_bullets(self.changed_fixed.value), inline=False)

        if self.notes.value.strip():
            emb.add_field(name="📌 Developer Notes", value=self.notes.value.strip(), inline=False)

        if interaction.guild and interaction.guild.icon:
            emb.set_thumbnail(url=interaction.guild.icon.url)

        img_url = self.banner.value.strip() or DEVLOG_BANNER_URL
        if img_url.startswith(("http://", "https://")):
            emb.set_image(url=img_url)

        emb.set_footer(
            text=f"{interaction.guild.name if interaction.guild else 'Server'} Development Team",
            icon_url=interaction.user.display_avatar.url,
        )

        msg = await self.target_channel.send(content=self.ping_text or None, embed=emb)
        for emoji in ("🚀", "🔥", "❤️"):
            try:
                await msg.add_reaction(emoji)
            except Exception:
                pass

        await interaction.followup.send(f"✅ Development Log published in {self.target_channel.mention}!", ephemeral=True)

class DevLogLauncherView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Write & Send Development Log", style=discord.ButtonStyle.success, emoji="🛠️", custom_id="devlog:open")
    async def open_modal_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_dev(interaction.user):
            return await interaction.response.send_message("❌ Only Developers / Staff can post development logs.", ephemeral=True)
        await interaction.response.send_modal(DevLogModal(interaction.channel))

class DevLogBot(commands.Bot):
    def __init__(self, msg_intent: bool = True):
        intents = discord.Intents.default()
        intents.message_content = msg_intent
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(DevLogLauncherView())
        await self.tree.sync()

    async def on_ready(self):
        global BOT_STATUS
        BOT_STATUS = f"ONLINE as {self.user}"
        print(f"✅ DevLog Bot ONLINE as {self.user}")

def reg_cmds(b: DevLogBot):
    @b.command(name="devlog")
    async def prefix_devlog(ctx: commands.Context):
        if not is_dev(ctx.author):
            return await ctx.send("❌ Only Developers / Staff can use this command.")
        emb = discord.Embed(
            title="🛠️ Development Log Publisher",
            description="Click the button below to open the **Development Log Form** and publish an update to this channel!",
            color=discord.Color.blurple(),
        )
        await ctx.send(embed=emb, view=DevLogLauncherView())

    @b.tree.command(name="devlog", description="Write and publish an official Development Log embed")
    @discord.app_commands.describe(
        channel="Optional: Channel to send the Dev Log to (defaults to current channel)",
        ping="Optional: Mention @everyone, @here, or a role with the update",
    )
    async def slash_devlog(interaction: discord.Interaction, channel: discord.TextChannel = None, ping: str = ""):
        if not is_dev(interaction.user):
            return await interaction.response.send_message("❌ Only Developers / Staff can post development logs.", ephemeral=True)
        target = channel or interaction.channel
        await interaction.response.send_modal(DevLogModal(target, ping.strip()))

async def main():
    await run_web_server()
    asyncio.create_task(self_ping_loop())
    if not BOT_TOKEN:
        while True: await asyncio.sleep(3600)
    bot = DevLogBot(True)
    reg_cmds(bot)
    try:
        await bot.start(BOT_TOKEN)
    except discord.PrivilegedIntentsRequired:
        await bot.close()
        bot = DevLogBot(False)
        reg_cmds(bot)
        await bot.start(BOT_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
