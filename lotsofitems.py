from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Category, Base, Item, User

engine = create_engine('sqlite:///itemcatalog.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()


# Create dummy user
User1 = User(name="Ron Cromley", email="rcromley@udacity.com",
             picture='')
session.add(User1)
session.commit()

# Items for Snowboarding
category1 = Category(user_id=1, name="Snowboarding")

session.add(category1)
session.commit()

item2 = Item(user_id=1, name="Snowboard", description="Super tough carbon epoxy snowboard",
                     price="700.50", category=category1)

session.add(item2)
session.commit()


item1 = Item(user_id=1, name="Snow Goggles", description="green tinted",
                     price="2.99", category=category1)

session.add(item1)
session.commit()

item2 = Item(user_id=1, name="Funny Hat", description="Boy, will you look great in this!",
                     price="5.50", category=category1)

session.add(item2)
session.commit()

item3 = Item(user_id=1, name="Gloves", description="keep those fingers warm",
                     price="3.99", category=category1)

session.add(item3)
session.commit()

item4 = Item(user_id=1, name="Snowboarding Pants", description="Look good on the slopes",
                     price="7.99", category=category1)

session.add(item4)
session.commit()

item5 = Item(user_id=1, name="Long Underwear", description="It gets cold on the mountain",
                     price="1.99", category=category1)

session.add(item5)
session.commit()

item6 = Item(user_id=1, name="Snowboarding Boots", description="Violet colored",
                     price="0.99", category=category1)

session.add(item6)
session.commit()

item7 = Item(user_id=1, name="Medicinal Flask",
                     description="Use for emergencies", price="3.49", category=category1)

session.add(item7)
session.commit()

item8 = Item(user_id=1, name="Snow Jacket", description="Organic fleece lined",
                     price="5.99", category=category1)

session.add(item8)
session.commit()

# Items for Mixed Martial Arts
category2 = Category(user_id=1, name="Mixed Martial Arts")

session.add(category2)
session.commit()


item1 = Item(user_id=1, name="Bag Gloves", description="Fingers are cut off to improve grip",
                     price="7.99", category=category2)

session.add(item1)
session.commit()

item2 = Item(user_id=1, name="Crosstraining Shoes",
                     description="low heel to prevent twisted ankles", price="25.00", category=category2)

session.add(item2)
session.commit()

item3 = Item(user_id=1, name="Training Knife", description="Unsharpened aluminum, double-edged",
                     price="15.00", category=category2)

session.add(item3)
session.commit()

item4 = Item(user_id=1, name="Kali Sticks", description="Rattan, 24 inches long. Sold in pairs.",
                     price="12.00", category=category2)

session.add(item4)
session.commit()

item5 = Item(user_id=1, name="Heavy Stick", description="Three feet long.  About four pounds.",
                     price="14.00", category=category2)

session.add(item5)
session.commit()

item6 = Item(user_id=1, name="Mouthpiece", description="Custom fit by boiling",
                     price="12.00", category=category2)

session.add(item6)
session.commit()


# Items for Gardening
category1 = Category(user_id=1, name="Gardening")

session.add(category1)
session.commit()


item1 = Item(user_id=1, name="Tazmanian Chocolate Tomato Seed Packet", description="Highly prolific dwarf tomato plant",
                     price="8.99", category=category1)

session.add(item1)
session.commit()

item2 = Item(user_id=1, name="Uluru Ochre Tomato Seed Packet", description="The world's first orange and black tomato",
                     price="6.99", category=category1)

session.add(item2)
session.commit()

item3 = Item(user_id=1, name="Fertilizer", description="Thirteen essential nutrients",
                     price="9.95",  category=category1)

session.add(item3)
session.commit()

item4 = Item(user_id=1, name="Manure", description="Only the best organic manure!",
                     price="6.99", category=category1)

session.add(item4)
session.commit()

item2 = Item(user_id=1, name="Hornworm Killer", description="Organic approved bio-control agent (BT)",
                     price="9.50", category=category1)

session.add(item2)
session.commit()

print "added menu items!"
