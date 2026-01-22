# config.py

# Format: "Official Name": ["List", "of", "keywords", "to", "match"]
# We use lowercase for keywords to make matching easier.

RETAILERS = {
    "Lenovo US": ["lenovo us", "lenovo usa"],
    "Lenovo Intel": ["lenovo intel"],
    "Lenovo LAS": ["lenovo las"],
    "Lenovo Global": ["lenovo global"],
    "Lenovo Qualcomm": ["lenovo qualcomm", "snapdragon"],
    "J Crew": ["j crew", "jcrew"],
    "Madewell": ["madewell"],
    "Dillards": ["dillards"],
    "Staples": ["staples"],
    "Unique Vintage": ["unique vintage"],
    "Ann Taylor": ["ann taylor"],
    "LOFT": ["loft"],
    "GAP US": ["gap us", "gap usa"],
    "Old Navy": ["old navy"],
    "Banana Republic": ["banana republic", "br factory"],
    "Athleta": ["athleta us"],
    "Athleta Canada": ["athleta canada"],
    "Gap Factory": ["gap factory"],
    "Gap Canada": ["gap can", "gap canada"],
    "Joe Fresh": ["joe fresh"],
    "Simply Be": ["simplybe", "simply be"],
    "JD Williams": ["jd williams"],
    "Jacamo": ["jacamo"],
    "Lululemon": ["lululemon", "lulu"],
    "Foot Locker": ["foot locker"],
    "Sole Supplier": ["sole supplier"],
    "Janie and Jack": ["janie and jack"],
    "NAPA Online": ["napa", "genuine parts"],
    "Pet Supermarket": ["pet supermarket"],
    "EVO": ["evo"],
    "Brooks Brothers": ["brooks brothers"],
    "Revzilla": ["revzilla"],
    "Croma": ["croma"],
    "Halloween Costumes": ["halloween costumes"],
    "Ambrose Wilson": ["ambrose wilson"],
    "Fashion World": ["fashion world"],
    "Pacsun": ["pacsun"],
    "Quiksilver": ["quick silver", "quiksilver"],
    "Billabong": ["billabong"],
    "Reebok": ["reebok"],
    "Vince Camuto": ["vince camuto"],
    "David Jones": ["david jones"],
    "SnapAV": ["snapav"],
    "DSG": ["dsg", "dick's sporting goods"],
    "Rainbow Shops": ["rainbow", "rainbowshops"],
    "Alex & Ani": ["alex & ani", "alex and ani"],
    "Roots": ["roots"]
}

# Metadata for the Dashboard (Frequency/Notes)
RETAILER_INFO = {
    "Madewell": "Weekly/Biweekly",
    "Dillards": "Weekly/Biweekly",
    "Pacsun": "Biweekly/Monthly",
    "Lululemon": "Biweekly/Monthly",
    "Gap Canada": "Monthly (Includes ON, GAP, BR, Athleta)",
    "Lenovo Global": "21 Regions",
    # Add others as needed, defaults to "Monthly" in dashboard if missing
}