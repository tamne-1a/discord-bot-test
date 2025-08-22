import discord
import random
from unidecode import unidecode
import google.generativeai as genai
import logging
import os
from dotenv import load_dotenv
load_dotenv()

# ========== CONFIG ==========
MODEL_NAME      = "gemini-2.5-pro"              # hoặc "gemini-1.5-pro"         # <-- THAY (có thể để nhiều ID: {111, 222})
DISCORD_TOKEN   = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")
AI_CHANNEL_IDS = {1408161983466836110,1408522729459814573}
# (Tùy chọn) kênh chào mừng cố định. 0 = dùng system_channel
WELCOME_CHANNEL_ID = 0

# ========== INIT ==========
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(MODEL_NAME)

class Client(discord.Client):
    async def on_ready(self):
        logging.info(f"🤖 Ready as {self.user} (id={self.user.id})")
        for g in self.guilds:
            logging.info(f"• Đang ở server: {g.name} (id={g.id})")

    async def on_message(self, message: discord.Message):
        if message.author == self.user:
            return

        content = unidecode(message.content.lower()).strip()
        logging.info(f"[#{getattr(message.channel, 'name', message.channel.id)}] {message.author}: {message.content}")

        # === AI CHAT trong kênh chỉ định ===
        if message.channel.id in AI_CHANNEL_IDS: 
            prompt = message.content.strip()
            if not prompt:
                return
            try:
                # Gửi tin nhắn chờ trước
                placeholder = await message.channel.send("⏳ Đang soạn câu trả lời...")

                system_hint = "Bạn là trợ lý thân thiện, luôn trả lời bằng TIẾNG VIỆT, ngắn gọn, dễ hiểu."
                resp = model.generate_content([system_hint, prompt])
                reply = (resp.text or "Mình chưa rõ ý, bạn nói lại giúp mình với nha!").strip()

                if len(reply) > 1900:  # tránh vượt 2000 ký tự của Discord
                    reply = reply[:1900] + "…"

                # Edit lại tin nhắn chờ thành kết quả
                await placeholder.edit(content=reply)

            except Exception as e:
                await placeholder.edit(content=f"❌ Lỗi gọi AI: {e}")
            return


        # === Các lệnh “vui” (rule-based) ngoài kênh AI ===
        if "buồn" in message.content.lower():
            await message.channel.send(random.choice([
                "😢 Đừng buồn nữa, rồi mọi chuyện sẽ ổn thôi!",
                "👉 Nếu buồn thì kể cho mình nghe nè!",
                "💪 Mạnh mẽ lên bạn ơi!",
            ]))
            return

        if "cô đơn" in message.content.lower():
            await message.channel.send("🥺 Bạn không cô đơn đâu, mình ở đây nè!")
            return

        if content == "ping":
            await message.channel.send("pong!")
            return

        if content in ("hi", "hi!"):
            await message.channel.send("Tui là bot test 1")
            return

        if content in ("eiu tui la ai?", "eiu tui la ai"):
            await message.channel.send("Eiu bạn tên Bảo Châu")
            return

    # ======= MEMBER EVENTS =======
    async def on_member_join(self, member: discord.Member):
        logging.info(f"👋 Join: {member} (guild={member.guild.name})")
        ch = None
        if WELCOME_CHANNEL_ID:
            ch = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if ch is None:
            ch = member.guild.system_channel

        if ch and ch.permissions_for(member.guild.me).send_messages:
            await ch.send(f"👋 Chào mừng {member.mention} vào server!")
        else:
            logging.warning("Không gửi được tin chào mừng (không có channel hoặc thiếu quyền).")

    async def on_member_remove(self, member: discord.Member):
        logging.info(f"🚪 Leave: {member} (guild={member.guild.name})")
        ch = None
        if WELCOME_CHANNEL_ID:
            ch = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if ch is None:
            ch = member.guild.system_channel

        if ch and ch.permissions_for(member.guild.me).send_messages:
            await ch.send(f"😢 {member.name} đã rời server...")
        else:
            logging.warning("Không gửi được tin tạm biệt.")

    async def on_guild_join(self, guild: discord.Guild):
        logging.info(f"🤖 Bot vừa được thêm vào server: {guild.name} (id={guild.id})")
        if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
            await guild.system_channel.send("👋 Xin chào! Mình là bot, rất vui được phục vụ mọi người!")

    # ======= REACTION EVENTS =======
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        if user == self.user:
            return
        logging.info(f"➕ Reaction add: {user} {reaction.emoji} on msg {reaction.message.id}")
        ch = reaction.message.channel
        if ch and ch.permissions_for(ch.guild.me).send_messages:
            await ch.send(f"👍 {user.name} vừa thả {reaction.emoji}!")

    # Bắt cả khi message KHÔNG có trong cache
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.user.id:
            return
        guild = self.get_guild(payload.guild_id)
        if not guild:
            return
        channel = guild.get_channel(payload.channel_id)
        user = guild.get_member(payload.user_id)
        if channel and user and channel.permissions_for(guild.me).send_messages:
            await channel.send(f"✨ {user.name} vừa thả {payload.emoji} (raw)")

# ========== RUN ==========
intents = discord.Intents.default()
intents.guilds = True
intents.members = True          # bắt buộc cho on_member_join/remove
intents.message_content = True  # để đọc nội dung tin nhắn
intents.reactions = True        # để bắt sự kiện reaction

client = Client(intents=intents)
client.run(DISCORD_TOKEN)

