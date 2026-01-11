import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from dotenv import load_dotenv
from discord.ui import View, Button
import random
from typing import Optional

# ------------------------ #
# Load Environment & Config
# ------------------------ #
load_dotenv(".env")
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ DISCORD_TOKEN bulunamadı")

if not os.path.exists("config.json"):
    raise RuntimeError("❌ config.json bulunamadı")

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

GUILD_ID = int(config["GUILD_ID"])
YETKILI_ROLE_ID = int(config["YETKILI_ROLE_ID"])
CLEAR_ROLE_ID = int(config["CLEAR_ROLE_ID"])
TICKET_STAFF_ROLE_ID = int(config["TICKET_STAFF_ROLE_ID"])
TICKET_PANEL_CHANNEL_ID = int(config["TICKET_PANEL_CHANNEL_ID"])
TICKET_LOG_KLASOR = config.get("TICKET_LOG_KLASOR", "ticket_logs")

os.makedirs(TICKET_LOG_KLASOR, exist_ok=True)

# ------------------------ #
# Intents ve Bot
# ------------------------ #
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------------ #
# Ticket Embed & View
# ------------------------ #
def ticket_panel_embed():
    return discord.Embed(
        title="🎫 Destek Talebi",
        description=(
            "◆ Ticket Odalarını Gereksiz Kullanmayınız...\n"
            "◆ Destek Ekibini Beklemeyin, Direkt Konuya Değinin..."
        ),
        color=discord.Color.blurple()
    )

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🎫 Ticket Oluştur",
        style=discord.ButtonStyle.success,
        custom_id="ticket_create_button"
    )
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        user = interaction.user

        # Zaten ticket var mı kontrolü
        for ch in guild.text_channels:
            if ch.name == f"ticket-{user.id}":
                return await interaction.response.send_message(
                    "Zaten bir Ticket odan var...", ephemeral=True
                )

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.get_role(TICKET_STAFF_ROLE_ID): discord.PermissionOverwrite(view_channel=True)
        }

        channel = await guild.create_text_channel(
            f"ticket-{user.id}", overwrites=overwrites
        )

        await channel.send(f"Hoşgeldin {user.mention}! Yetkili ekibimiz seninle iletişime geçecektir.")
        await interaction.response.send_message("Ticket oluşturuldu", ephemeral=True)

# ------------------------ #
# Bot Ready Event
# ------------------------ #
@bot.event
async def on_ready():
    guild_obj = discord.Object(id=GUILD_ID)

    # TicketView ekle
    bot.add_view(TicketView())

    # Slash komutları guild'e sync
    await bot.tree.sync(guild=guild_obj)
    print(f"🤖 Bot aktif: {bot.user}")

    # Ticket panel mesajı
    try:
        channel = await bot.fetch_channel(TICKET_PANEL_CHANNEL_ID)
        async for msg in channel.history(limit=5):
            if msg.author == bot.user:
                return
        await channel.send(embed=ticket_panel_embed(), view=TicketView())
    except Exception as e:
        print(f"Ticket panel kanalı gönderilemedi: {e}")

# ------------------------ #
# Slash Commands
# ------------------------ #
@bot.tree.command(name="ykaydet", description="Yetkili kayıt")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def ykaydet(
    interaction: discord.Interaction,
    kullanici: discord.Member,
    rol: discord.Role,
    realisim: str
):
    if YETKILI_ROLE_ID not in [r.id for r in interaction.user.roles]:
        return await interaction.response.send_message("❌ Yetkin yok", ephemeral=True)

    await kullanici.add_roles(rol)
    await kullanici.edit(nick=realisim)
    await interaction.response.send_message("✅ Kayıt tamamlandı", ephemeral=True)

@bot.tree.command(name="say", description="Belirtilen kanala mesaj gönder")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def say(
    interaction: discord.Interaction,
    kanal: discord.TextChannel,
    mesaj: str
):
    if YETKILI_ROLE_ID not in [r.id for r in interaction.user.roles]:
        return await interaction.response.send_message("❌ Yetkin yok", ephemeral=True)

    await kanal.send(mesaj)
    await interaction.response.send_message("✅ Mesaj gönderildi", ephemeral=True)

@bot.tree.command(name="clear", description="Mesaj sil")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def clear(
    interaction: discord.Interaction,
    miktar: int = 5  # default değer: 5 mesaj
):
    """Mesaj silme komutu. Miktar girilmezse 5 mesaj siler."""
    
    # Yetki kontrolü
    if CLEAR_ROLE_ID not in [r.id for r in interaction.user.roles]:
        return await interaction.response.send_message("❌ Yetkin yok", ephemeral=True)

    # Minimum ve maksimum kontrolü
    if miktar < 1:
        return await interaction.response.send_message("❌ Miktar en az 1 olmalı", ephemeral=True)
    if miktar > 100:
        return await interaction.response.send_message("❌ Miktar en fazla 100 olabilir", ephemeral=True)

    await interaction.response.defer(ephemeral=True)
    silinen = await interaction.channel.purge(limit=miktar)
    await interaction.followup.send(f"🧹 {len(silinen)} mesaj silindi", ephemeral=True)


@bot.tree.command(name="ticketkapat", description="Ticket kapat")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def ticketkapat(interaction: discord.Interaction):
    if TICKET_STAFF_ROLE_ID not in [r.id for r in interaction.user.roles]:
        return await interaction.response.send_message("❌ Yetkin yok", ephemeral=True)

    if not interaction.channel.name.startswith("ticket-"):
        return await interaction.response.send_message("❌ Ticket kanalı değil", ephemeral=True)

    await interaction.response.send_message("🗑️ Ticket kapatılıyor", ephemeral=True)
    await interaction.channel.delete()

# ------------------------ #
# On Message Event (Ticket Log)
# ------------------------ #
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if hasattr(message.channel, "name") and message.channel.name.startswith("ticket-"):
        with open(
            os.path.join(TICKET_LOG_KLASOR, f"{message.channel.name}.txt"),
            "a",
            encoding="utf-8"
        ) as f:
            f.write(f"{message.author}: {message.content}\n")

    await bot.process_commands(message)



CEKILIS_KLASOR = "./cekilisler"
os.makedirs(CEKILIS_KLASOR, exist_ok=True)

# ------------------------
# Çekiliş View ve Butonlar
# ------------------------
class CekilisView(View):
    def __init__(self, mesaj_id: int):
        super().__init__(timeout=None)
        self.mesaj_id = mesaj_id  # mesaj ID dosya adı için kullanılacak

    @discord.ui.button(label="🎉 Çekilişe Katıl", style=discord.ButtonStyle.success)
    async def katil(self, interaction: discord.Interaction, button: Button):
        file_path = os.path.join(CEKILIS_KLASOR, f"cekilis_{self.mesaj_id}.txt")
        if not os.path.exists(file_path):
            open(file_path, "w").close()
        with open(file_path, "r", encoding="utf-8") as f:
            katilanlar = [line.strip() for line in f.readlines()]
        if str(interaction.user.id) in katilanlar:
            return await interaction.response.send_message("✅ Zaten çekilişe katıldın!", ephemeral=True)
        katilanlar.append(str(interaction.user.id))
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(katilanlar))
        await interaction.response.send_message("🎉 Çekilişe katıldın!", ephemeral=True)

    @discord.ui.button(label="❌ Çekilişten Ayrıl", style=discord.ButtonStyle.danger)
    async def ayril(self, interaction: discord.Interaction, button: Button):
        file_path = os.path.join(CEKILIS_KLASOR, f"cekilis_{self.mesaj_id}.txt")
        if not os.path.exists(file_path):
            return await interaction.response.send_message("❌ Henüz çekiliş yok!", ephemeral=True)
        with open(file_path, "r", encoding="utf-8") as f:
            katilanlar = [line.strip() for line in f.readlines()]
        if str(interaction.user.id) not in katilanlar:
            return await interaction.response.send_message("❌ Çekilişe katılmamışsın!", ephemeral=True)
        katilanlar.remove(str(interaction.user.id))
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(katilanlar))
        await interaction.response.send_message("❌ Çekilişten ayrıldın!", ephemeral=True)

# ------------------------
# Çekiliş Açma Komutu
# ------------------------
@bot.tree.command(name="cekilis", description="Yeni bir çekiliş aç")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def cekilis(
    interaction: discord.Interaction,
    kanal: discord.TextChannel,
    baslik: str,
    metin: str
):
    # Mesajı gönderdikten sonra ID alınacak
    embed = discord.Embed(title=baslik, description=metin, color=discord.Color.gold())
    embed.set_footer(text="Butonlarla çekilişe katılabilir veya ayrılabilirsiniz.")

    mesaj = await kanal.send(embed=embed)  # mesaj gönder
    mesaj_id = mesaj.id  # mesaj ID al

    view = CekilisView(mesaj_id)
    await mesaj.edit(view=view)  # View ekle

    # Boş dosya oluştur
    open(os.path.join(CEKILIS_KLASOR, f"cekilis_{mesaj_id}.txt"), "w").close()

    await interaction.response.send_message(f"✅ Çekiliş {kanal.mention} kanalında açıldı! Mesaj ID: {mesaj_id}", ephemeral=True)

# ------------------------
# Çekilişten Kazanan Seçme Komutu
# ------------------------
@bot.tree.command(name="cekilisacikla", description="Çekilişi bitir ve kazananı seç (mesaj ID ile)")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def cekilisacikla(
    interaction: discord.Interaction,
    mesaj_id: str  # str olarak alıyoruz
):
    # Int'e çevirmeye çalış
    try:
        mesaj_id_int = int(mesaj_id)
    except ValueError:
        return await interaction.response.send_message("❌ Lütfen geçerli bir mesaj ID girin!", ephemeral=True)

    file_path = os.path.join(CEKILIS_KLASOR, f"cekilis_{mesaj_id_int}.txt")
    if not os.path.exists(file_path):
        return await interaction.response.send_message("❌ Bu çekiliş bulunamadı!", ephemeral=True)

    with open(file_path, "r", encoding="utf-8") as f:
        katilanlar = [line.strip() for line in f.readlines()]

    if not katilanlar:
        return await interaction.response.send_message("❌ Çekilişe kimse katılmamış!", ephemeral=True)

    kazanan_id = int(random.choice(katilanlar))
    kazanan = interaction.guild.get_member(kazanan_id)

    if kazanan:
        await interaction.response.send_message(f"🎉 Kazanan: {kazanan.mention} Tebrikler!", ephemeral=False)
    else:
        await interaction.response.send_message(f"🎉 Kazanan ID: {kazanan_id} Tebrikler!", ephemeral=False)

    os.remove(file_path)




bot.run(TOKEN)
