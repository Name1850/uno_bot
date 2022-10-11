import discord
from functions import create_image
import traceback


class WildCard(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    async def respond(self, interaction, color):
        await interaction.response.send_message(f"Making color {color}!", ephemeral=True)
        self.value = color
        self.stop()

    @discord.ui.button(label="Red", style=discord.ButtonStyle.blurple)
    async def red(self, interaction: discord.Interaction, _):
        await self.respond(interaction, "red")

    @discord.ui.button(label="Yellow", style=discord.ButtonStyle.blurple)
    async def yellow(self, interaction: discord.Interaction, _):
        await self.respond(interaction, "yellow")

    @discord.ui.button(label="Green", style=discord.ButtonStyle.blurple)
    async def green(self, interaction: discord.Interaction, _):
        await self.respond(interaction, "green")

    @discord.ui.button(label="Blue", style=discord.ButtonStyle.blurple)
    async def blue(self, interaction: discord.Interaction, _):
        await self.respond(interaction, "blue")


class Dropdown(discord.ui.Select):
    def __init__(self, options, game, player):
        super().__init__(
            placeholder="Choose a card to play...",
            min_values=1,
            max_values=1,
            options=options,
        )

        self.game = game
        self.player = player

    async def callback(self, interaction: discord.Interaction):
        embed, attachments = self.view.embed_and_attachments()

        card = [x for x in self.player.deck if str(x) == self.values[0]][0]
        self.player.deck.remove(card)
        x = await self.view.check_special(interaction, card)
        self.game.discard.append(card)

        embed.title = f"Played {card}"
        embed.color = self.view.bot.color_dict.get(card.color)
        if str(card) != str(self.values[0]):
            embed.description = f"Color is now `{card.color}`"

        if x:
            embed.description += x

        attachments.append(create_image(card.color, card.value))
        embed.set_image(url="attachment://card.png")

        self.view.children[0].disabled = True
        await interaction.response.edit_message(view=self.view)

        await self.game.last_message.edit(embed=embed, attachments=attachments)
        self.view.stop()


class MoveView(discord.ui.View):
    def __init__(self, options, game, player, bot):
        super().__init__()
        self.message = None
        self.game = game
        self.player = player
        self.bot = bot

        if len(options) > 0:
            self.add_item(Dropdown(options, game, player))

    def embed_and_attachments(self):
        embed = discord.Embed(description="").add_field(name="Turn Cycle", value=str(self.game.turn))
        embed.set_author(name=f"{self.player.user.name}'s Turn",
                         icon_url=None if not self.player.user else self.player.user.avatar.url)
        attachments = []
        return embed, attachments

    async def check_special(self, interaction, card, wild=True):
        x = self.game.check_card(card.value)
        if x:
            return x

        if card.color is None and wild:
            view = WildCard()
            await interaction.response.defer()
            await interaction.followup.send("Choose the color:", view=view, ephemeral=True)
            await view.wait()
            card.color = view.value

    @discord.ui.button(label="Draw Card", style=discord.ButtonStyle.blurple, row=1)
    async def draw(self, interaction: discord.Interaction, _):
        embed, attachments = self.embed_and_attachments()

        new_draw = self.game.deck[-1]
        await interaction.response.send_message(f"You drew a `{new_draw}`", ephemeral=True,
                                                file=create_image(new_draw.color, new_draw.value))

        if new_draw.color == self.game.last_card.color or new_draw.value == self.game.last_card.value or new_draw.color is None:
            x = await self.check_special(interaction, new_draw, wild=False)
            if new_draw.color is None:
                new_draw.color = self.game.last_card.color

            embed.title = f"Drew Card - {new_draw}"
            if x:
                embed.description += x

            attachments.append(create_image(new_draw.color, new_draw.value))
            embed.set_image(url="attachment://card.png")
            embed.color = self.bot.color_dict[new_draw.color]

        else:
            embed.title = "Drew Card - No Match"
            self.game.move_card(self.game.deck, new_draw, self.player.deck)

        await self.game.last_message.edit(embed=embed, attachments=attachments)
        self.stop()

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

        await self.message.edit(view=self)

    async def on_error(self, interaction, error, item, /) -> None:
        print(''.join(traceback.format_exception(type(error), error, error.__traceback__)))
