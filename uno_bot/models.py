import random
import discord
import asyncio
from functions import create_image

class PlayerList:
    def __init__(self, players: list):
        self.players = players
        self.index = -1
        self.direction = 1

    def __next__(self):
        self.index = (self.index + self.direction) % len(self.players)

    @property
    def current(self):
        return self.players[self.index]

    def __str__(self):
        player_list = [repr(player) for player in self.players]
        player_list[max(self.index, 0)] = f"**{player_list[max(self.index, 0)]}**"
        return ["<-", "", "->"][self.direction + 1].join(player_list)


class Card:
    def __init__(self, color, value):
        self.color = color
        self.value = value

    def __str__(self):
        if self.color is None:
            return f"Wild {'Card' if self.value == 'wild' else '+4'}"
        return f"{self.color.title()} {str(self.value).title()}"


class Player:
    def __init__(self, user_id, bot):
        self.deck = []
        self.user_id = user_id
        self.user = bot.get_user(user_id)

    def __str__(self):
        return self.user.mention if self.user else f"AI {self.user_id}"

    def __repr__(self):
        return f"AI {self.user_id}" if not self.user else self.user.name


class Game:
    def __init__(self, players: list[Player], guild_id, channel_id, bot):
        self.deck = []  # index 0 is bottom of stack, index -1 is top of stack
        self.discard = []
        self.players = players
        self.turn = PlayerList(players)
        self.guild = guild_id
        self.channel = bot.get_channel(channel_id)
        self.last_message = None
        self.bot = bot

    @property
    def last_card(self):
        return self.discard[-1]

    @staticmethod
    def move_card(deck_from, card, deck_to):
        deck_to.append(card)
        deck_from.remove(card)

    async def initialize_game(self):
        cards = [1, 2, 3, 4, 5, 6, 7, 8, 9, 0, "skip", "reverse", "+2"]
        for color in ["red", "green", "yellow", "blue"]:
            for card in cards:
                self.deck.append(Card(color=color, value=card))

        for i in range(2):
            self.deck.append(Card(color=None, value="wild"))
            self.deck.append(Card(color=None, value="+4"))

        await self.deal()

    async def deal(self):
        random.shuffle(self.deck)

        Game.move_card(self.deck, self.deck[-1], self.discard)

        card = create_image(self.last_card.color, self.last_card.value)
        embed = discord.Embed(title=f"First Card Up: `{self.last_card}`",
                              color=self.bot.color_dict.get(self.last_card.color))
        embed.add_field(name="Turn Cycle", value=str(self.turn))
        embed.set_image(url="attachment://card.png")

        self.last_message = await self.channel.send(embed=embed, file=card)

        for i in range(7):
            for player in self.players:
                Game.move_card(self.deck, self.deck[-1], player.deck)

    def re_deal(self):
        cards = [card for card in self.discard if card.value in ["+4", "wild"]]
        for card in cards:
            card.color = None

        self.deck = self.discard
        random.shuffle(self.deck)

        self.discard.clear()

        Game.move_card(self.deck, self.deck[-1], self.discard)

    async def alert(self):
        if len(self.deck) == 0:
            self.re_deal()
            await self.last_message.edit(content="Draw pile empty, re-shuffling deck...")
            await asyncio.sleep(1)

            card = create_image(self.last_card.color, self.last_card.value)
            embed = discord.Embed(title=f"First Card Up: `{self.last_card}`",
                                  color=self.bot.color_dict.get(self.last_card.color))
            embed.add_field(name="Turn Cycle", value=str(self.turn))
            embed.set_image(url="attachment://card.png")

            await self.last_message.edit(content=None, embed=embed, attachments=[card])

        next(self.turn)

        player = self.turn.current
        if not player.user:
            embed = self.last_message.embeds[0]
            embed.insert_field_at(0, name="Turn Cycle", value=str(self.turn))
            await self.last_message.edit(content=f"{player} turn!")

            await asyncio.sleep(1.5)

            possible_cards = [card for card in player.deck if
                              card.color == self.last_card.color or card.value == self.last_card.value or card.color is None]

            attachments = []
            embed = discord.Embed(description="").add_field(name="Turn Cycle", value=str(self.turn))
            embed.set_author(name=f"{player} Turn")
            if len(possible_cards) == 0:
                new_draw = self.deck[-1]

                if new_draw.color == self.last_card.color or new_draw.value == self.last_card.value or new_draw.color is None:
                    Game.move_card(self.deck, new_draw, self.discard)
                    x = self.check_card(new_draw.value)
                    if new_draw.color is None:
                        new_draw.color = self.last_card.color

                    embed.title = f"Drew Card - {new_draw}"
                    embed.color = self.bot.color_dict[new_draw.color]
                    if x:
                        embed.description = x
                    attachments.append(create_image(new_draw.color, new_draw.value))
                    embed.set_image(url="attachment://card.png")

                else:
                    Game.move_card(self.deck, new_draw, player.deck)
                    embed.title = "Drew Card - No Match"

            else:
                choice = random.choice(possible_cards)

                if choice.color is None:
                    choice.color = random.choice(["red", "blue", "green", "yellow"])
                    embed.description = f"Color is now `{choice.color}`"

                Game.move_card(player.deck, choice, self.discard)
                x = self.check_card(choice.value)

                embed.title = f"{player} played {choice}"
                if x:
                    embed.description += x
                embed.color = self.bot.color_dict[choice.color]

                attachments.append(create_image(choice.color, choice.value))
                embed.set_image(url="attachment://card.png")

            await self.last_message.edit(embed=embed, attachments=attachments)

            phrase = {0: f"{player} wins!",
                      1: f"{player} has UNO!"}
            if phrase.get(len(player.deck)):
                await self.channel.send(phrase[len(player.deck)])

                if not player.deck:
                    self.bot.active_games.remove(self)
                    return

            await self.alert()

        else:
            embed = self.last_message.embeds[0]
            embed.insert_field_at(0, name="Turn Cycle", value=str(self.turn))
            await self.last_message.edit(content=f"{player} turn!")

    def check_card(self, special):
        if special == "skip":
            next(self.turn)
            return f"\nSkipped {self.turn.current}'s turn!"
        elif special == "reverse":
            self.turn.direction *= -1
            return "\nOrder reversed!"
        elif special == "+2":
            next(self.turn)
            for i in range(2):
                Game.move_card(self.deck, self.deck[-1], self.turn.current.deck)
            return f"\nSkipped {self.turn.current}'s turn and added 2 cards to their deck!"
        elif special == "+4":
            next(self.turn)
            for i in range(4):
                Game.move_card(self.deck, self.deck[-1], self.turn.current.deck)
            return f"\nSkipped {self.turn.current}'s turn and added 4 cards to their deck!"
        return None
