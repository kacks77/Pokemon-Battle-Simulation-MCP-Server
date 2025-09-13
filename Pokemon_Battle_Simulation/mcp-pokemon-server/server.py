from typing import Any
import httpx
import json
import random
import sys
#import asyncio
from fastmcp import FastMCP

#️⃣ Initializing MCP Server...
mcp = FastMCP(name="pokemon-server")

#️⃣ Setting Base URL for PokéAPI...
POKEAPI_BASE = "https://pokeapi.co/api/v2/pokemon/"

#️⃣ Fetching Pokémon Data...
async def get_pokemon_data(name: str):
    """
    Fetching Pokémon data (name, types, stats, abilities, moves, evolution chain)
    from the PokéAPI by name or id.
    """
    url = f"{POKEAPI_BASE}{name.lower()}"
    async with httpx.AsyncClient() as client:

        # 🌐 Getting main Pokémon data...
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

        # 📄 Getting species info (for evolution chain)...
        species_url = data["species"]["url"]
        species_resp = await client.get(species_url)
        species_data = species_resp.json()

        # 🔗 Getting evolution chain data...
        evo_url = species_data["evolution_chain"]["url"]
        evo_resp = await client.get(evo_url)
        evo_data = evo_resp.json()
    
    # 📄 Extracting evolution chain recursively...
    def extract_evolutions(chain):
        evo_list = [chain["species"]["name"]]
        evolves_to = chain.get("evolves_to", [])
        for evo in evolves_to:
            evo_list.extend(extract_evolutions(evo))
        return evo_list

    evolution_chain = extract_evolutions(evo_data["chain"])
    
    # 📦 Packing Pokémon info into dictionary...
    pokemon = {
        "name": data["name"],
        "types": [t["type"]["name"] for t in data["types"]],
        "stats": {s["stat"]["name"]: s["base_stat"] for s in data["stats"]},
        "abilities": [a["ability"]["name"] for a in data["abilities"]],
        "moves": [m["move"]["name"] for m in data["moves"]],
        "evolution_chain": evolution_chain,
    }
    return pokemon

# ✅ Part 1: Resource - Exposing Pokémon Info Resource...
@mcp.resource("pokemon-data/{name}", description="Fetch name, types, stats, abilities, moves and evolution chain for any Pokémon.")
async def pokemon_data(name: str):
    """Exposing Pokémon info as a resource (JSON response)."""
    data = await get_pokemon_data(name)
    print(f"Pokemon Features {name}:", json.dumps(data, indent=2))
    return data

# ✅ Part 2: Tool - Simulating Pokémon Battle with Status Effects...
@mcp.tool("pokemon-battle", description="Simulating a battle with resource description with additional status effects.")
async def battle(pokemon1: str, pokemon2: str):
    """Attractive battle simulator, 💥 Running with Status Effects (Paralysis, Burn, Poison)..."""
    p1 = await get_pokemon_data(pokemon1)
    p2 = await get_pokemon_data(pokemon2)
    
    # 🧬 Setting Initial HP...
    hp1, hp2 = p1["stats"]["hp"], p2["stats"]["hp"]
    log = []

    # 🎲 Assigning Random Status Effects...
    statuses = ["paralysis", "burn", "poison", None]
    p1_status = random.choice(statuses)
    p2_status = random.choice(statuses)

    if p1_status:
        log.append(f"{p1['name']} is affected by {p1_status}!")
    if p2_status:
        log.append(f"{p2['name']} is affected by {p2_status}!")

    

    # 🏁 Deciding Turn Order Based on Speed...
    attacker, defender = (p1, p2) if p1["stats"]["speed"] >= p2["stats"]["speed"] else (p2, p1)
    
    # 💀 Tracking Poison Damage (Stacking)...
    poison_counter = {p1["name"]: 0, p2["name"]: 0}
    
    # 🥊 Running Main Battle Loop...
    while hp1 > 0 and hp2 > 0:

        # ⛔ Checking Paralysis (25% Chance to Skip Turn)...
        if (attacker == p1 and p1_status == "paralysis" and random.random() < 0.25) or \
           (attacker == p2 and p2_status == "paralysis" and random.random() < 0.25):
            log.append(f"{attacker['name']} is paralyzed and cannot move!")
        else:
            atk_stat = attacker["stats"]["attack"]

            # 🔥 Applying Burn Effect (Halving Attack + Chip Damage)...)
            if (attacker == p1 and p1_status == "burn") or (attacker == p2 and p2_status == "burn"):
                atk_stat = atk_stat // 2
                burn_damage = max(1, (hp1 if attacker == p1 else hp2) // 20)
                if attacker == p1:
                    hp1 -= burn_damage
                else:
                    hp2 -= burn_damage
                log.append(f"{attacker['name']} is hurt by burn (-{burn_damage} HP)!")
            
            # 💥 Dealing Damage...
            damage = max(1, attacker["stats"]["attack"] - defender["stats"]["defense"] // 2)
            if defender["name"] == p1["name"]:
                hp1 -= damage
            else:
                hp2 -= damage
            log.append(f"{attacker['name']} hits {defender['name']} for {damage} damage!")
        
        # 💀 Applying Poison Effect (Stacking Damage Each Turn)...
        if (defender == p1 and p1_status == "poison") or (defender == p2 and p2_status == "poison"):
            poison_counter[defender["name"]] += 1
            poison_damage = max(1, ((hp1 if defender == p1 else hp2) * poison_counter[defender["name"]]) // 20)
            if defender == p1:
                hp1 -= poison_damage
            else:
                hp2 -= poison_damage
            log.append(f"{defender['name']} is hurt by poison (-{poison_damage} HP)!")
    
        # 🔄 Switching Turns...
        attacker, defender = defender, attacker  # swap turns
    
    # 🏆 Announcing Winner...
    winner = p1["name"] if hp1 > 0 else p2["name"]
    log.append(f"Winner: {winner}")
    
    # 📦 Returning Full Battle Result...
    return {
        "pokemon1": {
            "name": p1["name"],
            "types": p1["types"],
            "stats": p1["stats"],
            "abilities": p1["abilities"],
            "moves": p1["moves"][:7],  # limit to top 7 moves for UI
            "evolution_chain": p1["evolution_chain"],
        },
        "pokemon2": {
            "name": p2["name"],
            "types": p1["types"],
            "stats": p2["stats"],
            "abilities": p2["abilities"],
            "moves": p2["moves"][:7],
            "evolution_chain": p2["evolution_chain"],
        },
        "battle_log": log,
        "winner": winner
    }


# ===========================
# 🔧 TESTING SECTION (Optional)
# ===========================
# The following function can be used for manual testing of Pokémon data fetching.
# Just uncomment asyncio.run(fight_features()) at the bottom to try it.

# async def fight_features():
#     bulbasaur = await get_pokemon_data("bulbasaur")
#     charmander = await get_pokemon_data("charmander")
  
#     # For Pokemon 1: Bulbasaur
#     print("Bulbasaur Features:", json.dumps(bulbasaur, indent=2))
    
#     # For Pokemon 2: Charmander
#     print("Charmander Features:", json.dumps(charmander, indent=2))

#️⃣ Starting MCP Server...
if __name__ == "__main__":
    print("✅ Poekemon Server Starting...", file=sys.stderr)
    #asyncio.run(fight_features())
    mcp.run()
