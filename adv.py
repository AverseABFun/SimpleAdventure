from __future__ import annotations

import ast
import random
from collections.abc import Callable
from dataclasses import dataclass, field

DIRECTIONS = [
    "north", "northeast", "east", "southeast", "south", "southwest", "west",
    "northwest", "up", "down"
]
DIRECTION_ABBRS = {
    "north": "n",
    "northeast": "ne",
    "east": "e",
    "southeast": "se",
    "south": "s",
    "southwest": "sw",
    "west": "w",
    "northwest": "nw",
    "up": "u",
    "down": "d"
}
REVERSED_DIRECTION_ABBRS = {v: k for k, v in DIRECTION_ABBRS.items()}

USE_VERBS = []

BOLD = "\u001b[1m"
BLACK = "\u001b[30m"
GREY = "\u001b[30m"
GRAY = "\u001b[30m"
RED = "\u001b[31m"
GREEN = "\u001b[32m"
YELLOW = "\u001b[33m"
BLUE = "\u001b[34m"
MAGENTA = "\u001b[35m"
CYAN = "\u001b[36m"
WHITE = "\u001b[37m"
RESET = "\033[0m"


def colored(text, color):
    """Colored text"""
    if color.startswith('\u001b') or color.startswith('\033'):
        return color + text + RESET
    raise ValueError(
        f"unexpected color value \"{color}\", expected a color variable")


class AdvObject:
    """The base class for all text adventure objects"""
    pass


@dataclass
class Room(AdvObject):
    """A room that has a name, description, objects in it, and exits to other rooms"""
    name: str
    desc: str
    invalid_direction_msg: str = "You can't go that way!"
    objects: list[AdvObject] = field(default_factory=list)
    exits: dict[str, Room] = field(default_factory=dict)

    @property
    def description(self):
        return self.desc

    @description.setter
    def description(self, value):
        self.desc = value

    def __post_init__(self):
        for dir, exit in self.exits.items():
            if dir not in DIRECTIONS:
                raise ValueError(f'unknown direction {dir}')
            if not isinstance(exit, Room):
                raise TypeError(
                    f'{exit}: invalid type ({type(exit)}) for exit')
        for object in self.objects:
            if not isinstance(object, AdvObject):
                raise TypeError(
                    f'{object}: invalid type ({type(object)}) for object')


@dataclass
class Item(AdvObject):
    """A class to that can be picked up by the player"""
    name: str
    sdesc: str
    ldesc: str
    synonyms: list[str] = field(default_factory=list)
    use_funcs: dict[str, Callable] = field(default_factory=dict)
    fixed: str = ""

    @property
    def short_description(self):
        return self.sdesc

    @short_description.setter
    def short_description(self, value):
        self.sdesc = value

    @property
    def long_description(self):
        return self.ldesc

    @long_description.setter
    def long_description(self, value):
        self.ldesc = value

    def __post_init__(self):
        for verb in self.use_funcs:
            if verb not in USE_VERBS:
                USE_VERBS.append(verb)


@dataclass
class EnterableItem(Item):
    """A item that can be entered by the player and leads to a room"""
    name: str
    sdesc: str
    ldesc: str
    synonyms: list[str] = field(default_factory=list)
    use_funcs: dict[str, Callable] = field(default_factory=dict)
    enter_room: Room = Room("", "")

    @property
    def short_description(self):
        return self.sdesc

    @short_description.setter
    def short_description(self, value):
        self.sdesc = value

    @property
    def long_description(self):
        return self.ldesc

    @long_description.setter
    def long_description(self, value):
        self.ldesc = value

    def __post_init__(self):
        super().__init__(self.name, self.sdesc, self.ldesc, self.synonyms,
                         self.use_funcs)


def look(_inp, world):
    """Show information about the room that the player is in"""
    print(colored(world.current_room.name, BOLD))
    print(world.current_room.desc)
    for object in world.current_room.objects:
        print(f"{object.name}: {object.sdesc}")


def examine(inp, world):
    if inp.startswith("look at"):
        inp = inp.replace("look at", "", 1)
    else:
        inp = ' '.join(inp.split(" ")[1:])
    
    for object in world.current_room.objects:
        if object.name == inp or inp in object.synonyms:
            print(f"{object.ldesc}")
            return
    for object in world.inventory:
        if object.name == inp or inp in object.synonyms:
            print(f"{object.ldesc}")
            return
    print("You don't see that object here.")


def go(inp, world):
    inp = ''.join(inp.split(" ")[1:])
    try:
        world.current_room = world.current_room.exits[inp]
    except KeyError:
        try:
            world.current_room = world.current_room.exits[
                REVERSED_DIRECTION_ABBRS[inp]]
        except KeyError:
            print(world.current_room.invalid_direction_msg)
            return
    look("", world)


def moveCommand(dir):

    def func(_inp, world):
        go(f"go {dir}", world)

    return {str([dir, DIRECTION_ABBRS[dir]]): func}


def moveCommands():
    return {
        list(moveCommand(dir).keys())[0]: list(moveCommand(dir).values())[0]
        for dir in DIRECTIONS
    }

def get(inp, world):
    inp = ' '.join(inp.split(" ")[1:])
    if inp == "all":
        for object in world.current_room.objects:
            if object.fixed:
                print(object.fixed)
                return
            world.inventory.append(object)
            world.current_room.objects.remove(object)
        return
    for object in world.current_room.objects:
        if object.name == inp or inp in object.synonyms:
            if object.fixed:
                print(object.fixed)
                return
            world.inventory.append(object)
            world.current_room.objects.remove(object)
            return
    print("That item isn't in this room!")

def drop(inp, world):
    inp = ' '.join(inp.split(" ")[1:])
    for object in world.inventory:
        if object.name == inp or inp in object.synonyms:
            world.inventory.remove(object)
            world.current_room.objects.append(object)
            return
    print("That item isn't in your inventory!")

def inventory(_inp, world):
    for object in world.inventory:
        print(f"{object.name}: {object.sdesc}")

def again(_inp, world):
    try:
        inp = world.prev_commands[-2]
    except IndexError:
        print("You don't have any previous commands!")
        return
    found = False
    for key, val in world.commands.items():
        key = ast.literal_eval(key)
        for cmd in key:
            if inp.startswith(cmd):
                val(inp, world)
                found = True
                break
        if found: break
    if not found:
        print(random.choice(world.unknown_command_text))

def wait(_inp, _world):
    print("Time passes.")

def goin(inp, world):
    inp = ' '.join(inp.split(" ")[1:])
    for object in world.current_room.objects:
        if object.name == inp or inp in object.synonyms:
            if not isinstance(object, EnterableItem):
                print("You can't enter that!")
                return
            world.out_room = world.current_room
            world.current_room = object.enter_room
            look("", world)
            return

def goout(_inp, world):
    world.current_room = world.out_room
    look("", world)
    return

def useSomething(inp, world):
    if len(inp.split(" "))<2:
        print(random.choice(world.unknown_command_text))
        return False
    verb = inp.split(" ")[0]
    inp = ' '.join(inp.split(" ")[1:])
    for object in world.inventory:
        if object.name == inp or inp in object.synonyms:
            try:
                object.use_funcs[verb](world)
            except KeyError:
                print("That doesn't make sense!")
            return True
    print("You don't have that object!")

DEFAULT_COMMANDS = {
    str(["enter", "in"]): goin,
    str(["exit", "out"]): goin,
    str(["wait", "z"]): wait,
    str(["get", "take"]): get,
    str(["again", "g"]): again,
    str(["drop"]): drop,
    str(["inventory", "i"]): inventory,
    str(["exit", "quit"]): lambda _inp, _world : exit(0),
    **moveCommands(),
    str(["go", "move"]): go,
    str(["examine", "x", "look at"]): examine,
    str(["look", "l"]): look
}

class World:
    def __init__(self, starting_room: Room, commands = DEFAULT_COMMANDS):
        self.current_room = starting_room
        self.out_room = self.current_room
        self.commands = commands
        self.inventory = []
        self.unknown_command_text = ["Pardon?", "A fantastical idea!"]
        self.prev_commands = []

    def run(self, prompt = "> "):
        prompt = prompt.format(**globals())
        look("", self)
        while True:
            self.out_room = self.current_room
            inp = input(prompt)
            self.prev_commands.append(inp)
            found = False
            for verb in USE_VERBS:
                if inp.startswith(verb):
                    useSomething(inp, self)
                    found = True
            if not found:
                for key, val in self.commands.items():
                    key = ast.literal_eval(key)
                    for cmd in key:
                        if inp.startswith(cmd):
                            val(inp, self)
                            self.out_room = self.current_room
                            found = True
                            break
                    if found:
                        break
            if not found:
                print(random.choice(self.unknown_command_text))
