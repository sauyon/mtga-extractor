import argparse
import glob
import pyjson5 as json
import os.path
import re

import UnityPy

assert __name__ == "__main__"

parser = argparse.ArgumentParser(description='Extracts card art from MTGA.')
parser.add_argument("card_re", nargs="?", help="Regex to match card names")
parser.add_argument("--db", "-d", default="card_data.json",
                    help="Path to card database to create or use")
parser.add_argument("--set", help="Three letter set code to filter for")
parser.add_argument("--output", "-o", default="out", help="Output directory")
parser.add_argument("--mtga", default="C:\Program Files\Wizards of the Coast\MTGA",
                    help="Path to MTGA install directory")
parser.add_argument("--lang", "-l", default="en-US",
                    help="Localization language to dump database in")
parser.add_argument("--resize", dest="resize", action="store_true",
                    help="Resize the output image")
parser.add_argument("--no-resize", dest="resize", action="store_false",
                    help="Don't resize the output image")
parser.set_defaults(resize=True)
parser.add_argument("--output-size", nargs=2, type=int, default=(512, 376),
                    help="Output image size, if resize is enabled", metavar=("WIDTH", "HEIGHT"))

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
    card_dict = json.load(open(args.db, "rb"))
else:
    try:
        card_data_filename = glob.glob(
            os.path.join(data_folder, "Data_cards_*.mtga"))[0]
        card_data_file = open(card_data_filename, "rb")

        loc_data_filename = glob.glob(
            os.path.join(data_folder, "Data_loc_*.mtga"))[0]
        loc_data_file = open(loc_data_filename, "rb")

        alt_data_filename = glob.glob(
            os.path.join(data_folder, "Data_altPrintings_*.mtga"))[0]
        alt_data_file = open(alt_data_filename, "rb")
    except Exception as e:
        print(f"Failed to open card data file: ${e}")
        exit(1)

    cards = json.load(card_data_file)
    loc_data = json.load(loc_data_file)
    alt_data = json.load(alt_data_file)

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

    card_dict = {}
    for card_ in cards:
        card = {
            "id": card_["grpid"],
            "altId": 0,  # which alternate printing this is
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
            "isSecondaryCard": card_["isSecondaryCard"] if "isSecondaryCard" in card_ else False,
        }

        for attr in [
            "power", "toughness", "cmc",
            "colors", "castingcost", "subtypes", "rarity",
            "collectorNumber", "collectorMax", "flavorId",
            "knownSupportedStyles",
        ]:
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

        if card["id"] in card_dict:
            print(
                f"Duplicate card id {card['id']} for cards {card['name']} and {card_dict[card['id']]['name']}")

        card_dict[card["id"]] = card

    # load and dump alt data
    for id, alts in alt_data.items():
        for i, (kind, alt) in enumerate(alts.items()):
            if alt in card_dict:
                card_dict[alt]["altId"] = i+1
                card_dict[alt]["altKind"] = kind.strip()
            else:
                if int(id) in card_dict:
                    print(
                        f"Missing alt for {card_dict[int(id)]['name']}: {alt}")
                else:
                    print(
                        f"Missing alt for id {id}, which itself doesn't exist.")

    json.dump(card_dict, open(args.db, "wb"),
              indent=2, ensure_ascii=False)

if card_re is None and set is None:
    exit(0)

# output art from card data
for _, card in card_dict.items():
    if card_re is not None:
        if not re.match(card_re, card["name"], re.IGNORECASE) or (set and card["set"] != set):
            continue
    elif set and card["set"] != set:
        continue

    card_str = f"{card['name']} [{card['set']}] - {card['id']}"
    print(f"Found match: {card_str}")

    art_files = glob.glob(os.path.join(
        art_folder, f"{card['artId']:0>6}_CardArt_*.mtga"))
    if len(art_files) == 0:
        print(f"No art found for card {card['name']}")
    else:
        try:
            art_file = open(art_files[0], "rb")
            assets = UnityPy.load(art_file)

            found = False
            for name, obj in assets.container.items():
                if re.match(f".*/{card['artId']:0>6}_AIF.(tga|jpg)", name):
                    found = True
                    data = obj.read()
                    img = data.image
                    filename = f"{card_str.replace('/', '_')}.png"
                    filepath = os.path.join(args.output, filename)
                    if os.path.exists(filepath):
                        print(f"Skipping output of {filename} because it already exists.")

                    out = open(filepath, "wb")

                    if args.resize:
                        img = img.resize(tuple(args.output_size))

                    img.save(out)

            if not found:
                print(f"No art found for card {card_str}")

        except Exception as e:
            print(f"Failed to open art file for card {card['name']}: {e}")
