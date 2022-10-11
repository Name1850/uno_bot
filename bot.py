import asyncio
import traceback
import discord
from discord.ext import commands
from functions import create_deck
from models import Player, Game
from views import MoveView

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
bot.active_games = []
bot.color_dict = {"green": discord.Color.green(), "blue": discord.Color.blue(),
                  "yellow": discord.Color.yellow(), "red": discord.Color.red()}


@bot.event
async def on_ready():
    print("aa")


@bot.command()
@commands.guild_only()
@commands.is_owner()
async def sync(ctx) -> None:
    await ctx.bot.tree.sync(guild=ctx.guild)
    await ctx.send("ok")


@bot.tree.command(name="game")
async def _game(interaction: discord.Interaction, players: str):
    players = players.replace("1025565912461496370", "0")
    players = [interaction.guild.get_member(int(x[2:-1])) for x in players.split()]
    for i in range(players.count(None)):
        players[players.index(None)] = i + 1

    game = Game(
        [Player(interaction.user.id, bot),
         *[Player(player if type(player) == int else player.id, bot) for player in players]],
        interaction.guild_id, interaction.channel_id, bot)
    await game.initialize_game()
    await game.alert()
    bot.active_games.append(game)
    await interaction.response.send_message(
        f"{', '.join([interaction.user.mention, *[x.mention for x in players if isinstance(x, discord.Member)], *['AI' for x in players if type(x) == int]])}")


@bot.tree.command()
async def deck(interaction: discord.Interaction):
    game = bot.active_games[[x.guild for x in bot.active_games].index(interaction.guild_id)]
    player = game.players[[x.user_id for x in game.players].index(interaction.user.id)]

    embed, file = create_deck(interaction, player)
    await interaction.response.send_message(embed=embed, file=file, ephemeral=True)


@bot.tree.command()
async def move(interaction: discord.Interaction):
    game = bot.active_games[[x.guild for x in bot.active_games].index(interaction.guild_id)]
    player = game.players[[x.user_id for x in game.players].index(interaction.user.id)]

    possible_cards = []
    if game.turn.current == player:
        for card in player.deck:
            if card.color == game.last_card.color or card.value == game.last_card.value or card.color is None:
                possible_cards.append(discord.SelectOption(label=str(card)))

        embed, file = create_deck(interaction, player)
        view = MoveView(possible_cards, game, player, bot)
        msg = await interaction.response.send_message(embed=embed, file=file, view=view, ephemeral=True)

        view.message = msg
        await view.wait()
        phrases = {0: f"{interaction.user.mention} wins!",
                   1: f"{interaction.user.mention} has UNO!"}

        if len(player.deck) in phrases:
            await interaction.followup.send(phrases[len(player.deck)])
            if not player.deck:
                bot.active_games.remove(game)
                return

        await game.alert()

    else:
        await interaction.response.send_message("It's not your turn!", ephemeral=True)


@bot.tree.error
async def on_app_command_error(_, error):
    print(''.join(traceback.format_exception(type(error), error, error.__traceback__)))


async def main():
    async with bot:
        bot.tree.copy_global_to(
            guild=discord.Object(
                id=969460759073525770))
        await bot.start("token or")


asyncio.run(main())
