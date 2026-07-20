#!/usr/bin/env python3
"""
generate_serving_fixes.py
Generates correct serving info for all 751 foods using rule-based logic.
"""
import csv, json, os

CSV_PATH = r"C:\Users\z004mvzt\nutrition-tracker\seed_data\foods.csv"
JSON_OUT = r"C:\Users\z004mvzt\nutrition-tracker\seed_data\serving_fixes.json"

def get_serving_info(fdc_id, name, category, current_unit, current_serving):
    """Return (serving_unit, default_serving, g_per_unit) for a food item."""
    n = name.lower()
    cat = (category or '').lower()
    fid = int(fdc_id) if fdc_id else 0

    # ========= PROTEIN SOURCES =========
    if cat == 'protein sources':
        # Eggs - whole
        if 'egg, whole' in n:
            return 'piece', 1, 50
        if 'egg, scrambled' in n:
            return 'g', 100, None
        if 'egg white' in n:
            return 'g', 33, None
        if 'egg yolk' in n:
            return 'g', 17, None
        # Hot dogs
        if 'hot dog' in n and 'hebrew' in n:
            return 'piece', 1, 55
        if 'turkey hot dog' == n:
            return 'piece', 1, 45
        # Deli meats (sliced)
        if 'deli' in n and 'sliced' in n:
            return 'g', 30, None
        # Sausage patty
        if 'sausage patty' in n:
            return 'piece', 1, 45
        # Breakfast sausage links
        if 'breakfast sausage links' in n:
            return 'g', 45, None
        # Pepperoni/Salami/Bologna sliced
        if 'sliced' in n:
            return 'g', 30, None
        # Chicken patty
        if 'chicken patty' in n:
            return 'piece', 1, 100
        # Protein powder
        if 'protein powder' in n:
            return 'g', 30, None
        # Jerky
        if 'jerky' in n:
            return 'g', 28, None
        # Spam
        if 'spam' == n:
            return 'g', 56, None
        # Italian sausage / kielbasa / bratwurst
        if 'italian sausage' in n or 'kielbasa' in n or 'bratwurst' in n:
            return 'g', 85, None
        # Anchovies (small cans)
        if 'anchovies' in n:
            return 'g', 28, None
        # Default for protein: 100-150g
        if any(x in n for x in ['breast', 'thigh', 'drumstick', 'wing', 'fillet', 'steak', 'loin', 'chop', 'tenderloin', 'roast']):
            return 'g', 150, None
        if 'ground' in n or 'liver' in n or 'tofu' in n or 'tempeh' in n or 'seitan' in n:
            return 'g', 100, None
        if 'bacon' in n:
            return 'g', 30, None
        if any(x in n for x in ['salmon', 'tuna', 'cod', 'tilapia', 'shrimp', 'halibut', 'mahi', 'sardine', 'mackerel', 'herring', 'trout', 'catfish', 'flounder', 'snapper', 'swordfish', 'striped bass', 'fish']):
            return 'g', 150, None
        if any(x in n for x in ['oyster', 'clam', 'scallop', 'mussel', 'crab', 'lobster']):
            return 'g', 100, None
        if any(x in n for x in ['salad', 'tuna salad', 'chicken salad', 'egg salad']):
            return 'g', 150, None
        if 'liverwurst' in n:
            return 'g', 57, None
        if 'corned beef' in n:
            return 'g', 100, None
        return 'g', 100, None

    # ========= DAIRY =========
    if cat == 'dairy':
        # Milks
        if any(x in n for x in ['milk, whole', 'milk, 2%', 'milk, 1%', 'milk, skim', 'milk, raw', 'buttermilk']):
            return 'ml', 240, None
        if any(x in n for x in ['almond milk', 'oat milk', 'soy milk', 'cashew milk', 'coconut milk', 'rice milk', 'chocolate milk']):
            return 'ml', 240, None
        # Kefir
        if 'kefir' in n:
            return 'ml', 240, None
        # String cheese
        if 'string cheese' in n:
            return 'piece', 1, 28
        # Cottage cheese
        if 'cottage cheese' in n:
            return 'g', 113, None
        # Ricotta
        if 'ricotta' in n:
            return 'g', 60, None
        # Parmesan grated
        if 'parmesan' in n and 'grated' in n:
            return 'tbsp', 1, None
        # Cream cheese
        if 'cream cheese' in n:
            return 'g', 28, None
        # Cheese (blocks/slices) - 28g serving
        if 'cheese' in n:
            return 'g', 28, None
        # Butter / Ghee
        if 'butter' in n or 'ghee' in n:
            return 'tbsp', 1, None
        # Heavy cream / whipping cream
        if 'heavy cream' in n or 'whipping' in n:
            return 'tbsp', 1, None
        # Sour cream
        if 'sour cream' in n:
            return 'tbsp', 2, None
        # Whipped cream
        if 'whipped cream' in n:
            return 'tbsp', 2, None
        # Creme fraiche
        if 'cr' in n and 'fraiche' in n:
            return 'tbsp', 1, None
        # Greek yogurt
        if 'greek yogurt' in n or 'yogurt' in n or 'frozen yogurt' in n:
            return 'g', 150, None
        # Ice cream
        if 'ice cream' in n:
            return 'g', 100, None
        return 'g', 100, None

    # ========= GRAINS & BREAD =========
    if cat == 'grains & bread':
        # Rice varieties (cooked)
        if 'rice' in n and 'cooked' in n and 'cake' not in n:
            return 'g', 150, None
        if 'rice cakes' in n:
            return 'piece', 1, 9
        # Grains cooked
        if any(x in n for x in ['quinoa', 'buckwheat', 'couscous', 'bulgar', 'millet', 'amaranth', 'teff', 'farro', 'barley', 'wild rice', 'black rice']) and 'cooked' in n:
            return 'g', 150, None
        # Oats dry
        if ('oats' in n or 'oatmeal' in n) and any(x in n for x in ['dry', 'rolled', 'old fashioned']):
            return 'g', 40, None
        # Oats prepared
        if ('oats' in n or 'oatmeal' in n) and any(x in n for x in ['prepared', 'instant', 'water']):
            return 'g', 250, None
        # Pasta
        if 'pasta' in n and 'cooked' in n:
            return 'g', 200, None
        # Bread loaves - slice
        if n.startswith('bread,') or n.startswith('bread '):
            return 'slice', 1, 30
        if 'bread' in n and any(x in n for x in ['ciabatta', 'focaccia']):
            return 'slice', 1, 50
        # Bagels
        if 'bagel' in n:
            return 'piece', 1, 105
        # English muffin
        if 'english muffin' in n:
            return 'piece', 1, 57
        # Croissant
        if 'croissant' in n:
            return 'piece', 1, 57
        # Tortilla
        if 'tortilla' in n:
            return 'piece', 1, 50
        # Pita
        if 'pita' in n:
            return 'piece', 1, 57
        # Crackers
        if 'crackers' in n:
            return 'serving', 4, None
        # Granola
        if 'granola' in n and 'bar' not in n:
            return 'g', 30, None
        # Cereal
        if 'cereal' in n or 'muesli' in n:
            return 'g', 40, None
        # Popcorn
        if 'popcorn' in n:
            return 'g', 30, None
        # Pancake
        if 'pancake' in n:
            return 'piece', 1, 70
        # Waffle
        if 'waffle' in n:
            return 'piece', 1, 75
        # Pretzel soft
        if 'pretzel, soft' in n:
            return 'piece', 1, 113
        # Pretzel hard
        if 'pretzel, hard' in n:
            return 'g', 30, None
        # Muffin (baked good, not fast food)
        if 'muffin' in n and 'english' not in n:
            return 'piece', 1, 70
        # Cornmeal
        if 'cornmeal' in n:
            return 'g', 30, None
        return 'g', 100, None

    # ========= FRUITS =========
    if cat == 'fruits':
        # Juices in Fruits section
        if 'juice' in n:
            return 'ml', 240, None
        # Whole fruits
        if n.startswith('banana'):
            return 'piece', 1, 120
        if n.startswith('apple'):
            return 'piece', 1, 180
        if n.startswith('orange'):
            return 'piece', 1, 180
        if n.startswith('mango'):
            return 'piece', 1, 200
        if n.startswith('peach'):
            return 'piece', 1, 150
        if n.startswith('pear'):
            return 'piece', 1, 170
        if n.startswith('plum'):
            return 'piece', 1, 85
        if n.startswith('kiwi'):
            return 'piece', 1, 75
        if n.startswith('avocado'):
            return 'piece', 1, 150
        if n.startswith('lemon'):
            return 'piece', 1, 70
        if n.startswith('lime'):
            return 'piece', 1, 60
        if n.startswith('grapefruit'):
            return 'piece', 1, 250
        if n.startswith('tangerine'):
            return 'piece', 1, 85
        if n.startswith('pomegranate') and 'juice' not in n:
            return 'piece', 1, 250
        if n.startswith('fig'):
            return 'piece', 1, 50
        if n.startswith('date'):
            return 'piece', 1, 25
        # Small berries / dried fruits / chopped - use g
        if any(x in n for x in ['strawberry', 'blueberry', 'raspberry', 'blackberry', 'cherry', 'grape,', 'watermelon', 'cantaloupe', 'honeydew', 'pineapple', 'papaya', 'coconut', 'raisin', 'cranberry, dried', 'apricot, dried', 'prune', 'currant', 'gooseberry', 'passionfruit', 'persimmon', 'lychee', 'dragon fruit', 'guava', 'jackfruit', 'mulberry', 'loganberry', 'boysenberry']):
            return 'g', 100, None
        return 'g', 100, None

    # ========= VEGETABLES =========
    if cat == 'vegetables':
        # Herbs - small amounts
        if any(x in n for x in ['chive', 'mint', 'basil', 'cilantro', 'parsley']):
            return 'g', 5, None
        # Garlic - small amount
        if 'garlic, raw' in n:
            return 'g', 10, None
        # Small amounts for strong flavors
        if any(x in n for x in ['jalapeno', 'serrano', 'habanero']):
            return 'g', 30, None
        # Most vegetables
        return 'g', 100, None

    # ========= LEGUMES & NUTS =========
    if cat == 'legumes & nuts':
        # Whole nuts
        if any(x in n for x in ['peanuts', 'almonds', 'cashews', 'walnuts', 'pecans', 'pistachios', 'macadamia', 'hazelnuts', 'brazil nuts', 'pine nuts']):
            return 'g', 28, None
        # Seeds
        if any(x in n for x in ['sunflower seeds', 'pumpkin seeds']):
            return 'g', 28, None
        if any(x in n for x in ['chia seeds', 'flax seeds', 'hemp seeds', 'sesame seeds']):
            return 'g', 15, None
        # Nut butters
        if any(x in n for x in ['peanut butter', 'almond butter', 'cashew butter', 'sunflower seed butter']):
            if 'powdered' in n:
                return 'tbsp', 2, None
            return 'tbsp', 2, None
        # Tahini / sesame paste
        if 'tahini' in n or 'sesame paste' in n:
            return 'tbsp', 1, None
        # Beans / lentils / peas (cooked)
        if any(x in n for x in ['beans', 'lentils', 'peas', 'chickpeas', 'edamame']):
            return 'g', 150, None
        return 'g', 100, None

    # ========= OILS & FATS =========
    if cat == 'oils & fats':
        if 'cooking spray' in n:
            return 'serving', 1, None
        if any(x in n for x in ['mayonnaise', 'mayo']):
            return 'tbsp', 1, None
        if 'margarine' in n:
            return 'tbsp', 1, None
        if 'shortening' in n:
            return 'tbsp', 1, None
        if 'lard' in n:
            return 'tbsp', 1, None
        # All oils
        return 'tbsp', 1, None

    # ========= SNACKS & SWEETS =========
    if cat == 'snacks & sweets':
        # Chocolate bars
        if 'dark chocolate,' in n or 'milk chocolate' in n or 'white chocolate' in n:
            return 'g', 40, None
        if 'chocolate chips' in n:
            return 'tbsp', 1, None
        if 'chocolate candy bar' in n:
            return 'piece', 1, 45
        if 'chocolate covered nuts' in n:
            return 'g', 40, None
        # Sweeteners
        if 'honey' == n:
            return 'tbsp', 1, None
        if 'maple syrup' in n:
            return 'tbsp', 1, None
        if 'agave' in n:
            return 'tbsp', 1, None
        if 'corn syrup' in n:
            return 'tbsp', 1, None
        if 'sugar' in n:
            return 'tsp', 1, None
        # Jelly/jam
        if 'jelly' in n or 'jam' in n:
            return 'tbsp', 1, None
        # Peanut butter cups
        if 'peanut butter cups' in n:
            return 'piece', 2, 21
        # Granola bars
        if 'granola bar' in n:
            return 'piece', 1, 40
        # Protein bars
        if 'protein bar' in n:
            return 'piece', 1, 65
        # Energy bar
        if 'energy bar' in n:
            return 'piece', 1, 60
        # Chips
        if 'chips' in n:
            return 'g', 28, None
        # Pretzels
        if 'pretzels' in n:
            return 'g', 28, None
        # Candy
        if 'candy, gummy' in n:
            return 'g', 28, None
        if 'candy, hard' in n:
            return 'piece', 1, 5
        if 'candy, licorice' in n:
            return 'g', 28, None
        if 'candy, taffy' in n:
            return 'piece', 1, 14
        if 'candy, lollipop' in n:
            return 'piece', 1, 17
        if 'candy, caramel' in n:
            return 'piece', 1, 14
        if 'candy, fudge' in n:
            return 'piece', 1, 28
        # Cookies
        if 'cookie' in n:
            return 'piece', 1, 15
        # Brownie
        if 'brownie' in n:
            return 'piece', 1, 60
        # Donuts
        if 'donut' in n:
            return 'piece', 1, 60
        # Muffin (store bought)
        if 'muffin' in n:
            return 'piece', 1, 100
        # Cakes
        if 'cake, cheesecake' in n:
            return 'slice', 1, 100
        if 'cake' in n:
            return 'slice', 1, 100
        # Pie
        if 'pie' in n:
            return 'slice', 1, 150
        # Trail mix
        if 'trail mix' in n:
            return 'g', 50, None
        # Popcorn candy coated
        if 'popcorn' in n:
            return 'g', 50, None
        # Peppermint candy
        if 'peppermint' in n:
            return 'piece', 1, 5
        # Dates stuffed
        if 'dates, stuffed' in n:
            return 'piece', 1, 25
        return 'g', 30, None

    # ========= BEVERAGES =========
    if cat == 'beverages':
        # Espresso
        if 'espresso' in n:
            return 'ml', 30, None
        # Macchiato
        if 'macchiato' in n:
            return 'ml', 60, None
        # Cortado
        if 'cortado' in n:
            return 'ml', 100, None
        # Shot spirits
        if any(x in n for x in ['vodka', 'whiskey', 'rum', 'gin', 'tequila', 'brandy', 'liqueur']):
            return 'ml', 44, None
        # Wine / champagne
        if 'wine' in n or 'champagne' in n:
            return 'ml', 150, None
        # Beer
        if 'beer' in n:
            return 'ml', 355, None
        # Small juices
        if 'ginger juice' in n or 'wheatgrass juice' in n:
            return 'ml', 30, None
        # All other beverages: 240ml standard
        return 'ml', 240, None

    # ========= CONDIMENTS & SAUCES =========
    if cat == 'condiments & sauces':
        # Hot sauces / small condiments
        if 'hot sauce' in n or 'worcestershire' in n or 'fish sauce' in n or 'coconut aminos' in n or 'buffalo sauce' in n:
            return 'tsp', 1, None
        if 'liquid smoke' in n:
            return 'tsp', 1, None
        # Mustard
        if 'mustard' in n:
            return 'tsp', 1, None
        # Ketchup
        if 'ketchup' in n:
            return 'tbsp', 1, None
        # Soy sauce / tamari / teriyaki
        if 'soy sauce' in n or 'tamari' in n or 'teriyaki' in n:
            return 'tbsp', 1, None
        # BBQ / marinara / alfredo
        if 'barbecue' in n or 'bbq' in n or 'marinara' in n or 'alfredo' in n:
            return 'tbsp', 2, None
        # Pesto
        if 'pesto' in n:
            return 'tbsp', 2, None
        # Ranch/Italian/Caesar/Balsamic dressing
        if 'dressing' in n or 'vinaigrette' in n:
            return 'tbsp', 2, None
        # Salsa / guacamole / hummus
        if 'salsa' in n or 'guacamole' in n or 'hummus' in n:
            return 'tbsp', 2, None
        # Relish / pickle juice / capers
        if 'relish' in n or 'pickle juice' in n or 'capers' in n:
            return 'tbsp', 1, None
        # Olives / pickles
        if 'olives' in n or 'pickles' in n:
            return 'g', 30, None
        # Tahini / sesame paste / miso / soy butter
        if 'tahini' in n or 'sesame paste' in n or 'miso' in n or 'soy butter' in n:
            return 'tbsp', 1, None
        return 'tbsp', 1, None

    # ========= PREPARED FOODS =========
    if cat == 'prepared foods':
        # Pizza
        if 'pizza' in n:
            return 'slice', 1, 150
        # Burgers
        if 'hamburger patty' in n:
            return 'piece', 1, 113
        if 'cheeseburger' in n:
            return 'piece', 1, 150
        if 'hamburger, double' in n:
            return 'piece', 1, 215
        # Hot dogs
        if 'hot dog' in n:
            return 'piece', 1, 85
        # French fries / sweet potato fries
        if 'fries' in n:
            return 'g', 150, None
        # Nuggets / wings / fried chicken
        if 'nuggets' in n or 'wings' in n or 'fried chicken' in n:
            return 'g', 150, None
        # Tacos
        if 'taco' in n:
            return 'piece', 1, 120
        # Burritos
        if 'burrito' in n and 'bowl' not in n:
            return 'piece', 1, 300
        if 'burrito bowl' in n:
            return 'g', 280, None
        # Quesadilla
        if 'quesadilla' in n:
            return 'piece', 1, 200
        # Enchilada
        if 'enchilada' in n:
            return 'piece', 1, 200
        # Sushi rolls
        if 'sushi roll' in n:
            return 'piece', 1, 200
        # Nigiri
        if 'nigiri' in n:
            return 'piece', 2, 20
        # Ramen / pho (soups)
        if 'ramen' in n:
            return 'ml', 450, None
        if 'pho' in n:
            return 'ml', 500, None
        # Mac and cheese
        if 'mac and cheese' in n:
            return 'g', 250, None
        # Lasagna
        if 'lasagna' in n:
            return 'g', 250, None
        # Lo mein / fried rice
        if 'lo mein' in n or 'fried rice' in n:
            return 'g', 300, None
        # Garden salad
        if 'salad' in n:
            return 'g', 300, None
        # Oatmeal
        if 'oatmeal' in n:
            return 'g', 250, None
        # Eggs (2 eggs)
        if 'eggs,' in n and '2 eggs' in n:
            return 'serving', 1, None
        # Omelets
        if 'omelet' in n:
            return 'serving', 1, None
        # Pancakes with syrup
        if 'pancakes,' in n:
            return 'serving', 1, None
        # Waffles with syrup
        if 'waffles,' in n:
            return 'serving', 1, None
        # French toast
        if 'french toast' in n:
            return 'slice', 1, 75
        # Crepes
        if 'crepe' in n:
            return 'piece', 1, 50
        # Hash browns
        if 'hash browns' in n:
            return 'g', 100, None
        # Breakfast sandwich
        if 'breakfast sandwich' in n:
            return 'piece', 1, 150
        # Granola with yogurt / yogurt parfait
        if 'granola with yogurt' in n or 'yogurt parfait' in n:
            return 'g', 200, None
        # Protein pancakes
        if 'protein pancakes' in n:
            return 'g', 150, None
        return 'g', 200, None

    # Fallback
    return current_unit, float(current_serving) if current_serving else 100.0, None


def main():
    # Read CSV
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"Read {len(rows)} foods from CSV")
    
    results = {}
    
    for row in rows:
        name = row['name']
        fdc_id = row['usda_fdc_id']
        category = row.get('category', '')
        current_unit = row.get('serving_unit', 'g')
        current_serving = row.get('default_serving', '100')
        
        unit, serving, g_per = get_serving_info(fdc_id, name, category, current_unit, current_serving)
        results[name] = {
            "serving_unit": unit,
            "default_serving": serving,
            "g_per_unit": g_per
        }
    
    # Save JSON backup
    with open(JSON_OUT, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"Generated serving data for {len(results)} foods")
    print(f"JSON saved to {JSON_OUT}")
    
    # Show some stats
    unit_counts = {}
    for v in results.values():
        u = v['serving_unit']
        unit_counts[u] = unit_counts.get(u, 0) + 1
    print("\nUnit distribution:")
    for u, c in sorted(unit_counts.items(), key=lambda x: -x[1]):
        print(f"  {u}: {c}")
    
    count_unit_with_g = sum(1 for v in results.values() if v['g_per_unit'] is not None)
    print(f"\nFoods with g_per_unit set: {count_unit_with_g}")


if __name__ == '__main__':
    main()