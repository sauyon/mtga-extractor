import argparse
import glob
import json
import os.path
import re

import UnityPy

assert __name__ == "__main__"

parser = argparse.ArgumentParser(description='Extracts card art from MTGA.')
parser.add_argument("card_re", help="Regex to match card names")
parser.add_argument("--set", help="Three letter set code to filter for")
parser.add_argument("--output", default="out", help="Output directory")
parser.add_argument("--mtga", default="C:\Program Files\Wizards of the Coast\MTGA", help="Path to MTGA install directory")
parser.add_argument("--lang", default="en-US", help="Localization language to search card names in")

args = parser.parse_args()

card_re = args.card_re
set = args.set
print("Searching for card with regex: " + card_re)

mtga_folder = args.mtga
# UNITY_VERSION = "2020.3.13f1" # doesn't seem to be needed

mtg_data_folder = os.path.join(mtga_folder, "MTGA_Data", "Downloads")
art_folder = os.path.join(mtg_data_folder, "AssetBundle")
data_folder = os.path.join(mtg_data_folder, "Data")

if os.path.exists("card_data.pickle"):
    card_list = json.load(open("card_data.json", "rb"))
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
            "name": loc_dict[card_["titleId"]],
            "artId": card_["artId"],
            "set": card_["set"],
            # can add more info to this dict at some point...
        }

        card_list.append(card)

    json.dump(card_list, open("card_data.json", "w"))

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