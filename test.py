import adv

item1 = adv.Item("test item 1",
                 "a test item",
                 "tEsT", ["item", "test"],
                 use_funcs={"use": lambda _world: print("used")})

room1 = adv.Room("test room 1", "test description 1", objects=[item1])
room2 = adv.Room("test room 2", "test description 2", exits={"north": room1})
room1.exits["south"] = room2

world = adv.World(room1)
world.run()
