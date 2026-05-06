# witcher_streamlit_creator.py

import streamlit as st
import random
import numpy as np
import pandas as pd
#gear_df = pd.read_csv("https://docs.google.com/spreadsheets/d/.../export?format=csv&gid=297970149")
#st.set_page_config(page_title="Witcher RPG Character Creator", layout="centered")

st.title("🧙 Witcher RPG Character Creator")

# --- Basic Info ---
st.header("Step 1: Basic Info")
# --- Race and Profession Logic ---
races = ["Human", "Elf", "Dwarf", "Witcher", "Mage"]
profession_map = {
    "Bard": "Busking",
    "Craftsman": "Patch Job",
    "Criminal": "Practised Paranoia",
    "Doctor": "Healing Hands",
    "Mage": "Magic Training",
    "Man-at-Arms": "Tough as Nails",
    "Merchant": "Well Travelled",
    "Priest": "Initiate of the Gods",
    "Witcher": "Witcher Training"
}

# --- Race Selection ---
name = st.text_input("Character Name")
race = st.selectbox("Race", races)
st.session_state["race"] = race

# --- Racial Bonuses ---
racial_bonuses = {
    "Witcher": {
        "Awareness": 1,
        "Reflex": 1,
        "Dexterity": 1,
        "Empathy_penalty": -4,
        "Empathy_cap": 6,
        "notes": [
            "Immune to disease",
            "Can use mutagens",
            "No dim light penalty",
            "Can track by scent"
        ]
    },
    "Elf": {
        "Fine Arts": 1,
        "Archery": 2,
        "notes": [
            "Can draw/string bow without action",
            "Animals are friendly unless provoked",
            "Auto-find common plant substances in natural terrain"
        ]
    },
    "Dwarf": {
        "Physique": 1,
        "Business": 1,
        "Encumbrance_bonus": 25,
        "notes": [
            "Natural SP 2 (not reduced by ablation)"
        ]
    }
}

# --- Display Bonuses ---
if race in racial_bonuses:
    st.subheader(f"🧬 {race} Racial Perks")
    bonuses = racial_bonuses[race]
    for stat, value in bonuses.items():
        if stat == "notes":
            for note in value:
                st.markdown(f"- {note}")
        else:
            st.markdown(f"- **{stat}**: {value}")
gender = st.text_input("Gender")
age = st.number_input("Age", min_value=10, max_value=100)
home_region = st.selectbox("Choose your homeland:", ["Northern Kingdom", "Nilfgaard", "Dol Blathanna", "Skellige", "Mahakam"])
if home_region == "North":
    home_language = "Common Speech"
elif home_region in ["Nilfgaard", "Dol Blathanna", "Skellige"]:
    home_language = "Elder Speech"
else:
    home_language = "Dwarven"

language_skills = {
    "Common Speech": 0,
    "Elder Speech": 0,
    "Dwarven": 0
}
language_skills[home_language] = 8



# --- Filter Professions Based on Race ---
if race == "Witcher":
    allowed_professions = ["Witcher"]
elif race == "Mage":
    allowed_professions = ["Mage"]
else:
    allowed_professions = [p for p in profession_map if p != "Witcher"]

profession = st.selectbox("Profession", allowed_professions)
defining_skill = profession_map[profession]
st.text_input("Defining Skill", value=defining_skill, disabled=True)

# --- Magic Access Note ---
if race == "Dwarf":
    st.warning("🛑 Dwarves cannot use magic.")
elif race in ["Human", "Elf", "Mage"]:
    st.info("✨ This race can access magic if profession allows it.")

if race == "Witcher" or profession == "Witcher":
    st.subheader("🛡️ Choose Your Witcher School")
    school = st.selectbox("Select a Witcher School:", ["Wolf", "Gryphon", "Cat", "Viper", "Bear"])
    st.session_state["witcher_school"] = school

school_perks = {
    "Wolf": "No penalty for Strong Strikes",
    "Gryphon": "+2 Vigor Threshold",
    "Cat": "Immune to Charm Attempts",
    "Viper": "No penalties for Dual Wielding",
    "Bear": "-2 to Overall Armor Penalty"
}

if "witcher_school" in st.session_state:
    selected_school = st.session_state["witcher_school"]
    st.markdown(f"🎓 **{selected_school} School Perk**: {school_perks[selected_school]}")


# --- Stats ---
st.header("Step 2: Assign Stats (1–10)")
stat_names = ["INT", "REF", "DEX", "BODY", "SPD", "EMP", "CRA", "WILL", "LUCK"]

# --- Choose Method ---
method = st.radio("Choose stat assignment method:", ["Roll for stats", "Point-buy system"])

stats = {}

if method == "Roll for stats":
    if st.button("Roll Stats"):
        for stat in stat_names:
            stats[stat] = random.randint(3, 10)
        st.success("🎲 Stats rolled!")
        for stat, val in stats.items():
            st.write(f"{stat}: {val}")

elif method == "Point-buy system":
    total_points = st.number_input("Enter total points to distribute (e.g. 60)", min_value=9, max_value=90, value=60)
    cols = st.columns(3)
    for i, stat in enumerate(stat_names):
        with cols[i % 3]:
            stats[stat] = st.number_input(f"{stat}", min_value=1, max_value=10, value=5, key=f"stat_{stat}")

    current_total = sum(stats.values())
    st.write(f"🧮 Total assigned: {current_total} / {total_points}")

    if current_total > total_points:
        st.error("You've assigned more points than allowed!")
    elif current_total < total_points:
        st.warning("You still have points left to assign.")
    else:
        st.success("✅ Stat distribution complete.")

# --- Profession Abilities ---
st.header("Step 3: Profession Abilities")
profession_skills = {
    "Bard": {
        "Defining Skill": "Busking",
        "Core Skills": ["Charisma", "Deceit", "Performance", "Language (Choose 1)", "Human Perception",
                        "Persuasion", "Streetwise", "Fine Arts", "Seduction", "Social Etiquette"]
    },
    "Craftsman": {
        "Defining Skill": "Patch Job",
        "Core Skills": ["Crafting", "Business", "Athletics", "Endurance", "Physique",
                        "Streetwise", "Fine Arts", "Alchemy", "Education", "Persuasion"]
    },
    "Criminal": {
        "Defining Skill": "Practised Paranoia",
        "Core Skills": ["Sleight of Hand", "Pick Locks", "Streetwise", "Forgery", "Deceit",
                        "Stealth", "Intimidate", "Small Blades", "Athletics", "Awareness"]
    },
    "Doctor": {
        "Defining Skill": "Healing Hands",
        "Core Skills": ["Resist Coercion", "Charisma", "Social Etiquette", "Courage", "Human Perception",
                        "Wilderness Survival", "Business", "Deduction", "Small Blades", "Alchemy"]
    },
    "Mage": {
        "Defining Skill": "Magic Training",
        "Core Skills": ["Human Perception", "Spell Casting", "Hex Weaving", "Resist Magic", "Staff/Spear",
                        "Education", "Ritual Crafting", "Social Etiquette", "Seduction", "Grooming & Style"]
    },
    "Man-at-Arms": {
        "Defining Skill": "Tough as Nails",
        "Core Skills": ["Combat Skill 1", "Combat Skill 2", "Combat Skill 3", "Combat Skill 4", "Combat Skill 5",
                        "Wilderness Survival", "Courage", "Physique", "Intimidation", "Dodge/Escape"]
    },
    "Merchant": {
        "Defining Skill": "Well Travelled",
        "Core Skills": ["Charisma", "Small Blades", "Education", "Language (Choose 2)", "Streetwise",
                        "Business", "Persuasion", "Human Perception", "Gambling", "Resist Coercion"]
    },
    "Priest": {
        "Defining Skill": "Initiate of the Gods",
        "Core Skills": ["Ritual Crafting", "Leadership", "Courage", "Human Perception", "Hex Weaving",
                        "First Aid", "Charisma", "Wilderness Survival", "Teaching", "Spell Casting"]
    },
    "Witcher": {
        "Defining Skill": "Witcher Training",
        "Core Skills": ["Awareness", "Deduction", "Spell Casting", "Alchemy", "Dodge/Escape",
                        "Wilderness Survival", "Swordsmanship", "Athletics", "Stealth", "Ride"]
    }
}

# --- Get Profession from Step 1 ---
st.session_state["profession"] = profession 
combat_skills = [
    "Brawling", "Dodge/Escape", "Melee", "Riding", "Sailing",
    "Small Blades", "Staff/Spear", "Swordsmanship", "Archery",
    "Athletics", "Crossbow"
]

if profession == "Man-at-Arms":
    st.subheader("⚔️ Choose 5 Combat Skills")
    selected_combat_skills = st.multiselect("Select your combat skills:", combat_skills, max_selections=5)

    if len(selected_combat_skills) != 5:
        st.warning(f"You’ve selected {len(selected_combat_skills)} of 5 combat skills.")
        st.stop()
    else:
        st.success("✅ Combat skills selected.")

    # Add fixed core skills
    fixed_skills = ["Wilderness Survival", "Courage", "Physique", "Intimidation", "Dodge/Escape"]
    core_skills = selected_combat_skills + fixed_skills
else:
    core_skills = profession_skills[profession]["Core Skills"]

# Final skill list
all_skills = [defining_skill] + core_skills
defining_skill = profession_skills[profession]["Defining Skill"]
core_skills = profession_skills[profession]["Core Skills"]
all_skills = [defining_skill] + core_skills

# --- Skill Allocation UI ---
st.markdown(f"🧠 Allocate **44 points** across the following 11 skills for your **{profession}**.")
st.markdown("Each skill must have **at least 1 point**, and no more than **6 points**.")

skill_points = {}
cols = st.columns(3)
for i, skill in enumerate(all_skills):
    with cols[i % 3]:
        skill_points[skill] = st.number_input(f"{skill}", min_value=1, max_value=6, value=1, key=f"skill_{skill}")

# --- Validation ---
total_allocated = sum(skill_points.values())
st.write(f"🎯 Total allocated: {total_allocated} / 44")

if total_allocated > 44:
    st.error("You've assigned more points than allowed!")
elif total_allocated < 44:
    st.warning("You still have points left to assign.")
else:
    st.success("✅ Skill allocation complete.")

language_count = 0
for skill in core_skills:
    if "Language" in skill:
        if "Choose 2" in skill or "(2)" in skill:
            language_count = 2
        elif "Choose 1" in skill or "(1)" in skill:
            language_count = 1

if language_count > 0:
    st.subheader(f"🌍 Choose {language_count} Language(s)")
    available_languages = ["Common Speech", "Elder Speech", "Dwarven"]
    selected_languages = st.multiselect("Select your languages:", available_languages, max_selections=language_count)

    if len(selected_languages) > language_count:
        st.error(f"You can only choose {language_count} language(s).")
    elif len(selected_languages) < language_count:
        st.warning(f"You’ve selected {len(selected_languages)} of {language_count} language(s).")
    else:
        st.success("✅ Language selection complete.")
        st.session_state["languages"] = selected_languages

# --- Gear ---
st.header("Step 4: Starting Gear")
gear_options = {
    "Bard": {
        "limit": 5,
        "items": [
            "Dice poker board", "Gwent deck", "Hand mirror", "An instrument", "Flask of spirits",
            "Dagger", "Perfume/cologne", "Belt pouch", "Garter sheath", "A journal with a lock"
        ]
    },
    "Craftsman": {
        "limit": 5,
        "items": [
            "Tinker’s forge", "Merchant’s tools", "Iron long sword", "Forging tools", "Alchemy set",
            "Hourglass", "Small chest", "Mace", "50 crowns of components", "Lock"
        ]
    },
    "Criminal": {
        "limit": 5,
        "items": [
            "Loaded dice", "Bullseye lantern", "Secret pocket", "Thieves’ tools", "Sleeve sheath",
            "Stiletto", "Brass knuckles", "Throwing knives x5", "Chloroform", "Satchel"
        ]
    },
    "Doctor": {
        "limit": 5,
        "items": [
            "Clotting powder x10", "Sterilizing fluid x10", "Numbing herbs x10", "Surgeon’s kit", "Writing kit",
            "Hourglass", "Candles x10", "Blanket", "Large tent", "Dagger"
        ]
    },
    "Mage": {
        "limit": 5,
        "items": [
            "Hourglass", "Makeup kit", "Belt pouch", "Writing kit", "Hand mirror",
            "Dagger", "Staff", "Garter sheath", "Journal", "100 crowns of components"
        ]
    },
    "Man-at-Arms": {
        "limit": 5,
        "items": [
            "Kord", "Spear", "Battle axe", "Throwing knives x5", "Satchel",
            "Chain coif", "Brigandine", "Armored trousers", "Crossbow & bolts x20", "Steel buckler"
        ]
    },
    "Merchant": {
        "limit": 3,
        "items": [
            "Writing kit", "Merchant’s tools", "Large tent", "Journal", "Crossbow & bolts x20", "Dagger"
        ]
    },
    "Priest": {
        "limit": 5,
        "items": [
            "Holy symbol", "Sterilizing fluid x5", "Alchemy set", "Surgeon’s kit", "Hourglass",
            "Dagger", "Staff", "Clotting powder x5", "Numbing herbs x5", "100 crowns of components"
        ]
    },
    "Witcher": {
        "limit": 2,
        "items": [
            "Alchemy set", "A horse", "Throwing knives x5", "A hand crossbow", "Double woven gambeson"
        ]
    }
}

profession = st.session_state.get("profession")
gear_pool = gear_options.get(profession, {})
gear_limit = gear_pool.get("limit", 5)
gear_items = gear_pool.get("items", [])

# --- Gear Selection UI ---
st.markdown(f"🎒 Choose up to **{gear_limit} items** for your **{profession}**:")
selected_gear = st.multiselect("Select your gear:", gear_items, max_selections=gear_limit)

# --- Auto-assign Witcher gear (does NOT count toward limit) ---
auto_gear = []
if profession == "Witcher":
    auto_gear = [
        "Witcher Medallion",
        "Steel Sword",
        "Silver Sword"  # fixed typo
    ]

# --- Validation only on selected gear ---
if len(selected_gear) > gear_limit:
    st.error(f"You can only select {gear_limit} items.")
elif len(selected_gear) == gear_limit:
    st.success("✅ Gear selection complete.")
    full_gear = selected_gear + auto_gear
    st.session_state["starting_gear"] = full_gear
    st.subheader("🧰 Final Gear List")
    for item in full_gear:
        st.write(f"- {item}")
else:
    st.warning(f"You’ve selected {len(selected_gear)} of {gear_limit} items.")



# --- Coin ---
import random
starting_coin = random.randint(100, 500)
st.header("Step 5: Starting Coin")
import streamlit as st
import random

st.header("Step 5: Starting Coin")

# --- Coin Base by Profession ---
coin_base = {
    "Bard": 120,
    "Craftsman": 120,
    "Criminal": 100,
    "Doctor": 150,
    "Mage": 200,
    "Man-at-Arms": 150,
    "Merchant": 180,
    "Priest": 75,
    "Witcher": 50
}

# --- Get Profession from session state ---
profession = st.session_state.get("profession", "Witcher")
base = coin_base.get(profession, 100)

# --- Coin Method ---
method = st.radio("Choose how to determine starting coin:", ["Roll 2d6", "Take average"])

if method == "Roll 2d6":
    if st.button("Roll for Coin"):
        roll = random.randint(1, 6) + random.randint(1, 6)
        coin = base * roll
        st.success(f"🎲 You rolled {roll} → Starting coin: {coin} crowns")
        st.session_state["starting_coin"] = coin
elif method == "Take average":
    coin = base * 7
    st.success(f"📊 Average taken → Starting coin: {coin} crowns")
    st.session_state["starting_coin"] = coin

# --- Display Summary ---
if st.button("Generate Character Summary"):
    st.subheader("🧾 Character Summary")
    st.markdown(f"**Name:** {name}")
    st.markdown(f"**Race:** {race}")
    st.markdown(f"**Gender:** {gender}")
    st.markdown(f"**Age:** {age}")
    st.markdown(f"**Profession:** {profession}")
    st.markdown(f"**Defining Skill:** {defining_skill}")
    st.markdown("**Stats:**")
    for stat, val in stats.items():
        st.write(f"{stat}: {val}")
    st.markdown("**Profession Abilities:** " + ", ".join(abilities))
    st.markdown("**Gear:** " + ", ".join(gear))
    st.markdown(f"**Starting Coin:** {starting_coin} crowns")

st.header("Step 6: Magic Setup")

profession = st.session_state.get("profession")
# --- Spell Lists ---
novice_spells = [ "Afan’s Mirror", "Blinding Dust", "Dispel", "Glamour", "Magic Compass", "Mind Manipulation", "Summon Staff", "Telepathy", "Cenlly Graig", "Codi Bywyd", "Diagnostic Spell", "Earthen Spike", "Korath’s Breath", "Luthien’s Quill", "Magic Healing", "Talfryn’s Prison", "Adenydd", "Air Pocket", "Bronwyn’s Gust", "Freshen Air", "Urien’s Shelter", "Static Storm", "Telekinesis", "Zephyr", "Aenye", "Aine Verseos", "Brand of Fire", "Cadfan’s Grasp", "Magic Flare", "Raise Flame", "Tanio Ilchar", "Wave of Fire", "Carys’ Hail", "Control Water", "Curse of Sedna", "Dormyn’s Fog", "Downpour", "Ice Slick", "Puro Dwr", "Rhewi" ]

invocations = [ "Boiling Blood", "Cursed Illness", "Friend to Wild Kind", "Nature’s Gift", "Nature’s Sight", "Sigil of the Hidden", "Blessing of Good Fortune", "Blessing of Love", "Holy Light", "Waters of Clearance", "Web of Lies", "Vaults of Knowledge" ]

rituals = [ "Cleansing Ritual", "Hydromancy", "Magical Message", "Pyromancy", "Ritual of Life", "Ritual of Magic", "Spell Jar", "Spirit Seance", "Telecommunication" ]

hexes = [ "Threads of Life", "Primal Reservoir", "Blessing of Healing", "Shape Nature", "Song of the Sky", "Cleansing Fire", "Holy Fortification", "Light of Truth", "Divine Portal", "Divine Wisdom", "Blessing of Death", "Eternal Judgement", "Freya’s Bravery", "Healing Rest", "Luck of the Father", "White Flame" ]

witcher_signs = [ "Aard", "Igni", "Quen", "Yrden", "Axii", "Magic Trap", "Active Shield", "Aard Sweep", "Fire Stream", "Puppet" ]


magic_profiles = {
    "Mage": {
        "novice_spells": 5,
        "rituals": 1,
        "hexes": 1,
        "vigor": 5
    },
    "Priest": {
        "invocations": 2,
        "rituals": 2,
        "hexes": 2,
        "vigor": 2
    },
    "Witcher": {
        "signs": "All Basic Signs",
        "vigor": 2
    }
}


if profession in magic_profiles:
    profile = magic_profiles[profession]
    st.markdown(f"🔮 **{profession} Magic Profile**")
    st.write(f"- Vigor Pool: {profile['vigor']}")

    if "novice_spells" in profile:
        selected_spells = st.multiselect(
           f"Choose {profile['novice_spells']} Novce Spell(s):",
            novice_spells,
            max_selections=profile["novice_spells"]
        )
        st.session_state["novice_spells"] = selected_spells

    if "invocations" in profile:
        selected_invocations = st.multiselect(
            f"Choose {profile['invocations']} Invocation(s):",
            invocations,
            max_selections=profile["invocations"]
        )
        st.session_state["invocations"] = selected_invocations

    if "rituals" in profile:
        selected_rituals = st.multiselect(
            f"Choose {profile['rituals']} Ritual(s):",
            rituals,
            max_selections=profile["rituals"]
        )
        st.session_state["rituals"] = selected_rituals

    if "hexes" in profile:
        selected_hexes = st.multiselect(
            f"Choose {profile['hexes']} Hex(es):",
            hexes,
            max_selections=profile["hexes"]
        )
        st.session_state["hexes"] = selected_hexes

    if "signs" in profile:
        st.success("✅ Witchers start with all Basic Signs.")
        st.session_state["signs"] = witcher_signs
else:
    st.info("🧘 This profession does not use magic.")


