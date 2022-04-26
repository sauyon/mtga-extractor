import argparse
import glob
import json
import os.path
import re

import UnityPy

assert __name__ == "__main__"

parser = argparse.ArgumentParser(description='Extracts card art from MTGA.')
parser.add_argument("card_re", nargs="?", help="Regex to match card names")
parser.add_argument("--db", default="card_data.json", help="Path to card database to create or use")
parser.add_argument("--set", help="Three letter set code to filter for")
parser.add_argument("--output", default="out", help="Output directory")
parser.add_argument("--mtga", default="C:\Program Files\Wizards of the Coast\MTGA", help="Path to MTGA install directory")
parser.add_argument("--lang", default="en-US", help="Localization language to search card names in")

args = parser.parse_args()

card_re = args.card_re
set = args.set
if card_re is None:
    print("Refreshing card database...")
    if os.path.exists(args.db):
        os.remove(args.db)
else:    
    print(f"Searching for card with regex: '{card_re}'")

mtga_folder = args.mtga
# UNITY_VERSION = "2020.3.13f1" # doesn't seem to be needed

mtg_data_folder = os.path.join(mtga_folder, "MTGA_Data", "Downloads")
art_folder = os.path.join(mtg_data_folder, "AssetBundle")
data_folder = os.path.join(mtg_data_folder, "Data")

if os.path.exists(args.db):
    card_list = json.load(open(args.db, "r", encoding="utf-8"))
else:
    try:
        card_data_filename = glob.glob(os.path.join(data_folder, "Data_cards_*.mtga"))[0]
        card_data_file = open(card_data_filename, "r", encoding="utf-8")

        loc_data_filename = glob.glob(os.path.join(data_folder, "Data_loc_*.mtga"))[0]
        loc_data_file = open(loc_data_filename, "r", encoding="utf-8")
    except Exception as e:
        print(f"Failed to open card data file: ${e}")
        exit(1)

    cards = json.load(card_data_file)
    loc_data = json.load(loc_data_file)

    loc_dict = {}
    for loc in loc_data:
        if loc["isoCode"] == args.lang:
            for loc_item in loc["keys"]:
                try:
                    if "raw" in loc_item:
                        loc_dict[loc_item["id"]] = loc_item["raw"]
                    else:
                        loc_dict[loc_item["id"]] = loc_item["text"]
                except Exception as e:
                    print(f"Bad loc item {loc_item}: {e}")

    os.makedirs(args.output, exist_ok=True)

    card_list = []
    for card_ in cards:
        card = {
            "grpid": card_["grpid"],
            "name": loc_dict[card_["titleId"]],
            "artId": card_["artId"],
            "set": card_["set"],
            "flavor_text": loc_dict[card_["flavorId"]],
            "set": card_["set"],
            "types": card_["types"] if "types" in card_ else [],
            "subtypes": card_["subtypes"] if "subtypes" in card_ else [],
            "typeText": loc_dict[card_["cardTypeTextId"]],
            "subtypeText": loc_dict[card_["subtypeTextId"]] if "subtypeTextId" in card_ else None,
            "frameColors": card_["frameColors"] if "frameColors" in card_ else [],
            "colorIdentity": card_["colorIdentity"] if "colorIdentity" in card_ else [],
        }

        for attr in ["power", "toughness", "cmc", "colors", "castingcost", "subtypes", "rarity", "collectorNumber", "collectorMax"]:
            if attr in card_:
                card[attr] = card_[attr]

        if "artistCredit" in card_:
            card["artist"] = card_["artistCredit"]

        if "abilities" in card_:
            card["abilities"] = [
                {"id": ability["Id"], "text": loc_dict[ability["TextId"]]} for ability in card_["abilities"]
            ]

        if "castingcost" in card_:
            cost = card_["castingcost"]
            card["castingcost"] = cost.replace("o", "")

        card_list.append(card)

    json.dump(card_list, open(args.db, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

if card_re is None:
    exit(0)

# output art from card data
for card in card_list:
    if not re.match(card_re, card["name"]) or (set and card["set"] != set):
        continue

    print(f"Found match: {card['name']} ({card['set']})")

    art_files = glob.glob(os.path.join(art_folder, f"{card['artId']:0>6}_CardArt_*.mtga"))
    if len(art_files) == 0:
        print(f"No art found for card {card['name']}")
    else:
        try:
            art_file = open(art_files[0], "rb")
            assets = UnityPy.load(art_file)
            
            for name, obj in assets.container.items():
                if os.path.splitext(name)[1] == ".tga":
                    data = obj.read()
                    img = data.image
                    out = open(os.path.join("out", f"{card['name']} ({card['set']}).png"), "wb")
                    img.resize((512, 376)).save(out)
        except Exception as e:
            print(f"Failed to open art file for card {card['name']}: {e}")