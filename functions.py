from PIL import Image
import discord
from io import BytesIO


def create_deck(interaction, player):
    w = len(player.deck[:7])
    h = -(-len(player.deck) // 7)
    width = 72 * w + 3 * (w - 1)
    height = 108 * h + 3 * (h - 1)

    bg = Image.new('RGBA', (width, height))
    print(player.deck, "im")
    for i, card in enumerate(player.deck):
        im = Image.open(f"images/{card.color if card.color else 'wild'}_{card.value}.png")
        bg.paste(im, ((72 * (i % 7) + 3 * (i % 7)), (108 * (i // 7) + 3 * (i // 7))))

    buffer = create_buffer(bg)

    file = discord.File(buffer, filename="deck.png")
    embed = discord.Embed(color=discord.Color.blue())
    embed.set_author(name=f"{interaction.user.name}'s Deck", icon_url=interaction.user.avatar.url)
    embed.set_image(url="attachment://deck.png")
    return embed, file


def create_buffer(im):
    buffer = BytesIO()
    im.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def create_image(color, value):
    if value in ["+4", "wild"]:
        color = "wild"
    im = Image.open(f"images/{color}_{value}.png")
    buffer = create_buffer(im)
    return discord.File(buffer, filename="card.png")
