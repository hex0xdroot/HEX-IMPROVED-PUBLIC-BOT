import sqlite3
import asyncio
import datetime
# import pm2py
from kutuphane import *
from disnake import Option, OptionType

def create_connection():
    return sqlite3.connect("mydatabase.db")

def create_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users(
        deneme TEXT,
        denemesifre TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS roles(
        name TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channels(
        name TEXT
        )
    """)


def insert_data(cursor):
    cursor.execute("""
        INSERT INTO users VALUES (
            'exampleuser',
            'examplepassword'
        )
    """)

def select_data(cursor):
    cursor.execute("""
        SELECT * FROM users
    """)
    users = cursor.fetchall()
    for user in users:
        print(user)

def main():
    connection = create_connection()
    cursor = connection.cursor()

    create_table(cursor)
    insert_data(cursor)
    select_data(cursor)

    connection.commit()
    connection.close()

main()

@bot.event
async def on_ready():
    print(f'{bot.user} Giriş yaptı')

class ConfirmView(disnake.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @disnake.ui.button(label="Yedeklemek istediğine emin misin?", style=disnake.ButtonStyle.gray)
    async def confirm(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        await interaction.response.send_message("Yedekleme işleminiz başarılı.")
        self.value = True
        self.stop()

@bot.command()
async def sunucuyedekle(ctx):
    # Sunucu sahibi kontrolü
    if ctx.author != ctx.guild.owner:
        await ctx.send("Bu komutu sadece sunucu sahibi kullanabilir.")
        return

    view = ConfirmView()
    await ctx.send("Yedeklemek istediğinize emin misiniz?", view=view)
    await view.wait()

    if view.value is None:
        return

    # Sunucudaki roller ve kanalların yedeğini al
    roles = [role.name for role in ctx.guild.roles]
    channels = [channel.name for channel in ctx.guild.channels]

    # Veritabanına kaydet
    connection = sqlite3.connect("mydatabase.db")
    cursor = connection.cursor()

    for role in roles:
        cursor.execute("INSERT INTO roles VALUES (?)", (role,))
    
    for channel in channels:
        cursor.execute("INSERT INTO channels VALUES (?)", (channel,))

    connection.commit()
    connection.close()

class RestoreView(disnake.ui.View):
  def __init__(self):
      super().__init__()
      self.value = None

  @disnake.ui.button(label="Yedeği yüklemek istediğine emin misin?", style=disnake.ButtonStyle.primary)
  async def confirm(self, button: disnake.ui.Button, interaction: disnake.Interaction):
      await interaction.response.send_message("Yedekleme işlemi başladı.")
      self.value = True
      self.stop()

@bot.command()
async def yedegiyukle(ctx):
  # Sunucu sahibi kontrolü
  if ctx.author != ctx.guild.owner:
      await ctx.send("Bu komutu sadece sunucu sahibi kullanabilir.")
      return

  view = RestoreView()
  await ctx.send("Yedeği yüklemek istediğinize emin misiniz?", view=view)
  await view.wait()

  if view.value is None:
      return

  # Veritabanından roller ve kanalların yedeğini al
  connection = sqlite3.connect("mydatabase.db")
  cursor = connection.cursor()

  cursor.execute("SELECT * FROM roles")
  roles = cursor.fetchall()

  cursor.execute("SELECT * FROM channels")
  channels = cursor.fetchall()

  connection.close()

  # Sunucudaki mevcut roller ve kanalları sil
  for role in ctx.guild.roles:
      if role.permissions <= ctx.me.guild_permissions:
          try:
              await role.delete()
          except disnake.Forbidden:
              continue

  for channel in ctx.guild.channels:
      try:
          await channel.delete()
      except disnake.Forbidden:
          continue

  # Yedekten rolleri ve kanalları geri yükle
  for role in roles:
      await ctx.guild.create_role(name=role[0])

  for channel in channels:
      await ctx.guild.create_text_channel(name=channel[0])


#*---------------------- Slash Komutlu Rol/Ekle Komutu Başlangıç ----------------------#
@bot.slash_command(description='Rol vermek istediğin kisiyi gir')
@commands.has_permissions(manage_roles=True)
async def rolekle(inter, member: disnake.Member = commands.Param(name='kullanici', description='Bir kullanici belirtin'), role_id: str = commands.Param(name='verecegin_rolun_idsi', description='Rolun ID\'sini girin')):
    role = inter.guild.get_role(int(role_id)) # Rolü al
    if role: # Eğer rol varsa
        await member.add_roles(role) # Rolü belirtilen üyeye ekle
        await inter.send('Rol Eklendi.')
    else:
        await inter.send('Geçersiz rol ID\'si.')

@rolekle.error
async def rolekle_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Üzgünüm, yetkin yeterli değil 🥰")
#?---------------------- Rol/Ekle Komutu Bitiş ----------------------#


#*---------------------- Rol/Kaldır Komutu Başlangıç ----------------------#

@bot.slash_command(description='Rol kaldırmak istediğin kisiyi gir')
@commands.has_permissions(manage_roles=True)
async def rolkaldir(inter, member: disnake.Member = commands.Param(name='kullanici', description='Bir kullanici belirtin'), role_id: str = commands.Param(name='kaldirilacak_rolun_idsi', description='Rolun ID\'sini girin')):
    role = inter.guild.get_role(int(role_id)) # Rolü al
    if role in member.roles: # Eğer kullanıcıda bu rol varsa
        await member.remove_roles(role) # Rolü belirtilen üyeden kaldır
        await inter.send('Rol Kaldırıldı.')
    else:
        await inter.send('Geçersiz rol ID\'si veya kullanıcının bu rolü yok.')

@rolkaldir.error
async def rolkaldir_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Üzgünüm, yetkin yeterli değil 🥰")

#?---------------------- Rol/Kaldır Komutu Bitiş ----------------------#



#*---------------------- Toplu-Mesaj-Silme Komutu Başlangıç ----------------------#

@commands.has_permissions(manage_messages=True)
@bot.slash_command(description="Belirli bir kanaldaki son 100 mesajı siler")
async def purge(inter):
    deleted = await inter.channel.purge(limit=100)
    await inter.response.send_message(f"{len(deleted)} mesaj başarıyla silinmiştir lordum. 🥰")

@purge.error
async def purge_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Üzgünüm, yetkin yeterli değil 🥰")
#?---------------------- Toplu-Mesaj-Silme Komutu Bitiş ----------------------#










#*---------------------- Kanal Kilitleme-Lock/Unlock Komutu Başlangıç ----------------------#

@bot.slash_command(description="Belirli bir kanalı kilitle - Kilitledikten sonra kimse mesaj atamaz!")
@commands.has_permissions(manage_guild=True)
async def lock(inter, channel: disnake.TextChannel):
    overwrite = disnake.PermissionOverwrite()
    overwrite.send_messages = False
    await channel.set_permissions(inter.guild.default_role, overwrite=overwrite)
    await inter.response.send_message(f"{channel.name} kanalı kilitlendi.")
@lock.error
async def lock_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Üzgünüm, yetkin yeterli değil 🥰")


@bot.slash_command(description="Belirli bir kanalın kilidini aç - Kilitidi açtıktan sonra herkes mesaj atabilir.")
@commands.has_permissions(manage_guild=True)
async def unlock(inter, channel: disnake.TextChannel):
    overwrite = disnake.PermissionOverwrite()
    overwrite.send_messages = True
    await channel.set_permissions(inter.guild.default_role, overwrite=overwrite)
    await inter.response.send_message(f"{channel.name} kanalının kilidi açıldı.")
@unlock.error
async def unlock_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Üzgünüm, yetkin yeterli değil 🥰")

#?---------------------- Kanal Kilitleme-Lock/Unlock Komutu Bitiş ----------------------#

#*---------------------- Ban/Unban Komutu Başlangıç ----------------------#

@bot.slash_command(
        description="Belirli bir kullanıcının sunucudan banlamaya yarayan komuttur.",
        options=[
        Option("user", "Banlamak istedigin kişiyi bahset/etiketle", OptionType.user, required=True),
        Option("reason", "Neden banlamak istiyorsun? Örn: Allaha Küfür.", OptionType.string, required=True)])
@commands.has_permissions(ban_members=True)
async def ban(inter, user: disnake.User, reason: str = commands.Param(name='sebep', description='Yasa dışı ilan etme sebebini girin')):
    await inter.guild.ban(user, reason=reason)
    await inter.response.send_message(f"{user.mention} kullanıcısı yasa dışı ilan edildi. Sebep: {reason}")
@ban.error
async def ban_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Üzgünüm, yetkin yeterli değil 🥰")

@bot.slash_command(
        description="Belirli bir kullanıcının yasa dışı ilanını kaldırır",
        options=[
        Option("user", "Banını kaldırmak istediğin kişiyi bahset/etiketle", OptionType.user, required=True),
        Option("reason", "Neden banını kaldırmak istiyorsun? Örn: Cezası Bitti.", OptionType.string, required=True)])
@commands.has_permissions(ban_members=True)
async def unban(inter, user: disnake.User):
    await inter.guild.unban(user)
    await inter.response.send_message(f"{user.mention} kullanıcısının yasa dışı ilanı kaldırıldı.")
@unban.error
async def unban_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Üzgünüm, yetkin yeterli değil 🥰")
#?---------------------- Ban/Unban Komutu Bitiş ----------------------#

#*---------------------- Süreli Chat Mute Komutu Başlangıç ----------------------#

@bot.slash_command(
    description="Bir kullanıcıya belirli bir süre için susturma rolü verir",
    options=[
        Option("user", "Susturulacak kullanıcı", OptionType.user, required=True),
        Option("duration", "Susturmanın süresi (dakika)", OptionType.integer, required=True)
    ]
)
@commands.has_permissions(mute_members=True)
async def tempmute(inter, user: disnake.User, duration: int):
    mute_role = disnake.utils.get(inter.guild.roles, name="Muted")  # Susturma rolünü bul
    if mute_role is None:
        mute_role = await inter.guild.create_role(name="Muted")  # Eğer rol yoksa oluştur
        for channel in inter.guild.channels:
            await channel.set_permissions(mute_role, send_messages=False)  # Rolün tüm kanallarda mesaj göndermesini engelle
    await user.add_roles(mute_role)  # Rolü kullanıcıya ekle
    await inter.response.send_message(f"{user.mention} kullanıcısı {duration} dakika boyunca susturuldu.")
    unmute_later.start(user, mute_role, duration)  # Rolü belirtilen süre sonra kaldır

@tasks.loop(count=1)
async def unmute_later(user: disnake.User, role: disnake.Role, duration: int):
    await asyncio.sleep(duration * 60)  # Belirtilen süre kadar bekle
    await user.remove_roles(role)  # Rolü kaldır
    channel = bot.get_channel(1165855564220334221)  # Bilgilendirme mesajının gönderileceği kanalı belirtin
    await channel.send(f"{user.mention} kullanıcısının susturma süresi doldu. Susturma permini kaldırdım.")

unmute_later.before_loop(bot.wait_until_ready)

@tempmute.error
async def tempmute_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Üzgünüm, yetkin yeterli değil 🥰")  # Bot hazır olana kadar bekle
#?---------------------- Süreli Mute Komutu Bitiş ----------------------#

#*---------------------- Say Komutu Başlangıç ----------------------#

emojis = {
    "0": ":zero:",
    "1": ":one:",
    "2": ":two:",
    "3": ":three:",
    "4": ":four:",
    "5": ":five:",
    "6": ":six:",
    "7": ":seven:",
    "8": ":eight:",
    "8": ":nine:",
    "8": ":eight:",
    "8": ":keycap_ten:",
    # Diğer rakamlar için emoji ekleyin
}

def number_to_emojis(number):
    return "".join(emojis.get(digit, "") for digit in str(number))

@bot.command()
async def say(ctx):
    seslideki_kisi_sayisi = sum(1 for m in ctx.guild.members if m.voice)
    uye_sayisi = len(ctx.guild.members)
    aktif_uye_sayisi = sum(1 for m in ctx.guild.members if m.status != disnake.Status.offline)
    tag_sayisi = sum(1 for m in ctx.guild.members if "tagınız" in m.display_name)
    yetkili_sayisi = sum(1 for m in ctx.guild.members if "tagınız" in m.display_name and any(role.permissions.administrator for role in m.roles))
    boost_sayisi = ctx.guild.premium_subscription_count
    bot_sayisi = sum(1 for m in ctx.guild.members if m.bot)

    embed = disnake.Embed(timestamp=datetime.datetime.now())
    embed.set_author(name="Sunucu Adı #YETKİLİALIM", icon_url="https://i.hizliresim.com/5exmtrc.png")
    embed.set_thumbnail(url="https://i.hizliresim.com/j254xl3.png")
    embed.add_field(name="", value=f"❯ Şu anda toplam {number_to_emojis(seslideki_kisi_sayisi)} kişi seslide. (`+`{number_to_emojis(bot_sayisi)}`bot`)", inline=False)
    embed.add_field(name="", value=f"❯ Sunucuda {number_to_emojis(uye_sayisi)} adet üye var (`+`{number_to_emojis(aktif_uye_sayisi)}`aktif`)", inline=False)
    embed.add_field(name="", value=f"❯ Toplamda {number_to_emojis(tag_sayisi)} kişi tagımızı alarak bizi desteklemiş. (`+`{number_to_emojis(yetkili_sayisi)}`taglı`)", inline=False)
    embed.add_field(name="", value=f"❯ Toplamda {number_to_emojis(boost_sayisi)} adet boost basılmış. ({ctx.guild.premium_tier}. seviye)", inline=False)
    embed.set_footer(text='Bu bot `hex0xdroot` tarafından kodlanmıştır.',icon_url="https://i.hizliresim.com/2ksbo58.png")
    await ctx.send(embed=embed)
#?---------------------- Say Komutu Bitiş ----------------------#

#*---------------------- rolemembers Komutu Başlangıç ----------------------#

@bot.slash_command(name="rolemembers", description="Belirli bir roldeki kişilerin listelesini gösteren komut")
async def rolemembers(inter: disnake.ApplicationCommandInteraction, role: disnake.Role):
    members = [member for member in inter.guild.members if role in member.roles]
    member_list ="\n".join(member.mention for member in members)
    
    embed = disnake.Embed(
        title=f"{role.name} Rolündeki Üyeler",
        description=member_list,
        color=0x2F3136,
        timestamp=datetime.datetime.now()
    )
    embed.set_footer(text="Bu bot hex0xdroot tarafından yapılmıştır.")
    
    await inter.response.send_message(embed=embed)

#?---------------------- rolemembers Komutu Bitiş ----------------------#

@bot.command()
async def menu(ctx):
    select = disnake.ui.Select(placeholder='Seçiminizi yapın:', min_values=1, max_values=1)
    select.add_option(label='🎇', description='Bu birinci seçenektir', value='1167206423449587774')
    select.add_option(label='🎆', description='Bu ikinci seçenektir', value='1167206423449587773')
    select.add_option(label='🎊', description='Bu üçüncü seçenektir', value='1167206423449587772')

    view = disnake.ui.View()
    view.add_item(select)

    await ctx.send('Aşağıdan bir seçenek seçin:', view=view)

@bot.event
async def on_select_option(interaction):
    role_id = interaction.data["values"][0]
    role = interaction.guild.get_role(int(role_id))
    if role is not None:
        await interaction.author.add_roles(role)
        await interaction.response.send_message(f"{interaction.author.mention}, {role.name} rolü verildi.")
    else:
        await interaction.response.send_message("Böyle bir rol bulunamadı.")

#*---------------------- Süreli Ban Komutu Başlangıç ----------------------#

@bot.slash_command(
    description="Belirli bir kişiyi süreli bir şekilde sunucudan uzaklaştırmaya yarayan slash komutu!",
    options=[
        Option("user", "Banlanacak kullanıcıyı Etiketle/Bahset", OptionType.user, required=True),
        Option("duration", "Ban süresi (dakika) Sadece sayı gir!", OptionType.integer, required=True),
        Option("reason", "Banlama sebebini girin (İsteğe Bağlı)", OptionType.string)
    ]
)
@commands.has_permissions(ban_members=True)
async def tempban(inter, user: disnake.User, duration: int, reason: str = None):
    await user.ban(reason=reason)
    await inter.response.send_message(f"{user.mention} kullanıcısı {duration} dakika boyunca sunucudan banlandı. Sebep: {reason}")
    unban_later.start(user, duration)  # Banı belirtilen süre sonra kaldır

@tasks.loop(count=1)
async def unban_later(user: disnake.User, duration: int):
    await asyncio.sleep(duration * 60)  # Belirtilen süre kadar bekle
    await user.unban()  # Banı kaldır
    channel = bot.get_channel(1166268276557484032)  # Bilgilendirme mesajının gönderileceği kanalı belirtin
    await channel.send(f"{user.mention} kullanıcısının ban süresi doldu. Banını kaldırdım.")

unban_later.before_loop(bot.wait_until_ready)
@tempban.error
async def tempban_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Üzgünüm, yetkin yeterli değil 🥰")

#?---------------------- Süreli Ban Komutu Bitiş ----------------------#



@bot.slash_command(description="Displays the help embed")
async def help(inter):
    embed = disnake.Embed(
        title="Yardım Menüsü",
        description="Botunuzun kullanılabilir komutlarını ve işlevlerini gösterir.",
        color=disnake.Colour.yellow(),
        url="https://disnake.dev/",
        timestamp=datetime.datetime.now(),
    )

    embed.set_author(
        name="VERONICA BOTS",
        url="https://disnake.dev/",
        icon_url="https://disnake.dev/assets/disnake-logo.png",
    )

    embed.set_thumbnail(url="https://disnake.dev/assets/disnake-logo.png")

    embed.set_image(url="https://i.hizliresim.com/cqqmuxe.jpg")

    embed.add_field(name="/guvenlik", value="Guvenlik Komutlarını Listeler", inline=False)

    embed.add_field(name="/moderasyon", value="Moderasyon Komutlarını Listeler", inline=True)
    embed.add_field(name="/istatistik", value="İstatistik Komutlarını Listeler", inline=True)
    embed.add_field(name="/guvenli", value="Güvenlik Komutlarını Listeler", inline=True)

    embed.set_footer(
        text="Daha fazla yardım için 'yardım' yazın.",
        icon_url="https://disnake.dev/assets/disnake-logo.png",
    )

    await inter.response.send_message(embed=embed)












#*---------------------- Süreli Uyarı - Warn Permi Verdirtme Başlangıç ----------------------#
@bot.slash_command(
    description="Bir kullanıcıya uyarı verir",
    options=[
        Option("user", "Uyarı vereceğin kişiyi bahset/etiketle", OptionType.user, required=True),
        Option("duration", "Uyarının süresi (dakika) - 1 yazarsan 1m olur 10 yazarsan 10m olur.", OptionType.integer, required=True),
        Option("reason", "Uyarının sebebi? Örn: Üst Perde", OptionType.string, required=True)
    ]
)
@commands.has_permissions(administrator=True)
async def uyari(ctx, user: disnake.User, duration: int, reason: str):
    role = disnake.utils.get(ctx.guild.roles, name="Muted")  # Rolü bul
    if role is None:
        await ctx.send("Uyarı rolü bulunamadı.")
        return

    await user.add_roles(role)  # Rolü kullanıcıya ekle
    await ctx.send(f"{user.mention} kullanıcısına uyarı rolü verildi.\nSebep: {reason}")

    remove_role_later.start(user, role, duration)  # Rolü belirtilen süre sonra kaldır

@tasks.loop(count=1)
async def remove_role_later(user: disnake.User, role: disnake.Role, duration: int):
    await asyncio.sleep(duration * 60)  # Belirtilen süre kadar bekle
    await user.remove_roles(role)  # Rolü kaldır
    channel = bot.get_channel(1165855564220334221)  # Bilgilendirme mesajının gönderileceği kanalı belirtin
    await channel.send(f"{user.mention} kullanıcısının uyarı rolünün zamanı doldu. Uyarı permini kaldırdım.")

remove_role_later.before_loop(bot.wait_until_ready)  # Bot hazır olana kadar bekle

@uyari.error
async def uyari_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Üzgünüm, yetkin yeterli değil 🥰")
#?---------------------- Süreli Uyarı - Warn Permi Verdirtme Bitiş ----------------------#

bot.run('TOKENİNİ GİR')
