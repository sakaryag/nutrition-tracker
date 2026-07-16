"""
Curated meal seed — real macros per 100g from USDA / nutritionix / verified sources.
Run: python seed_data/meals.py
"""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from models import db
from models.saved_food import SavedFood

MEALS = [
    # ── Turkish ──────────────────────────────────────────────────────────────
    {"name": "Mercimek Corbasi",      "category": "Turkish", "protein": 4.5,  "fat": 1.2,  "carbs": 12.0, "calories": 78,  "default_serving": 250, "serving_unit": "ml"},
    {"name": "Ezogelin Corbasi",      "category": "Turkish", "protein": 4.2,  "fat": 1.5,  "carbs": 13.0, "calories": 83,  "default_serving": 250, "serving_unit": "ml"},
    {"name": "Tarhana Corbasi",       "category": "Turkish", "protein": 3.8,  "fat": 1.8,  "carbs": 11.5, "calories": 76,  "default_serving": 250, "serving_unit": "ml"},
    {"name": "Iskender Kebab",        "category": "Turkish", "protein": 14.5, "fat": 11.2, "carbs": 14.0, "calories": 215, "default_serving": 300, "serving_unit": "g"},
    {"name": "Adana Kebab",           "category": "Turkish", "protein": 17.0, "fat": 14.0, "carbs": 2.5,  "calories": 208, "default_serving": 200, "serving_unit": "g"},
    {"name": "Doner Kebab",           "category": "Turkish", "protein": 16.0, "fat": 10.5, "carbs": 3.0,  "calories": 174, "default_serving": 200, "serving_unit": "g"},
    {"name": "Kofte",                 "category": "Turkish", "protein": 15.5, "fat": 11.0, "carbs": 8.5,  "calories": 196, "default_serving": 150, "serving_unit": "g"},
    {"name": "Manti",                 "category": "Turkish", "protein": 9.5,  "fat": 7.5,  "carbs": 28.0, "calories": 220, "default_serving": 250, "serving_unit": "g"},
    {"name": "Karniyarik",            "category": "Turkish", "protein": 8.5,  "fat": 9.0,  "carbs": 12.0, "calories": 165, "default_serving": 250, "serving_unit": "g"},
    {"name": "Imam Bayildi",          "category": "Turkish", "protein": 2.5,  "fat": 7.5,  "carbs": 10.0, "calories": 120, "default_serving": 200, "serving_unit": "g"},
    {"name": "Dolma (Yaprak)",        "category": "Turkish", "protein": 3.5,  "fat": 4.5,  "carbs": 18.0, "calories": 128, "default_serving": 150, "serving_unit": "g"},
    {"name": "Sarma",                 "category": "Turkish", "protein": 4.0,  "fat": 5.0,  "carbs": 19.0, "calories": 138, "default_serving": 150, "serving_unit": "g"},
    {"name": "Menemen",               "category": "Turkish", "protein": 8.5,  "fat": 9.0,  "carbs": 5.5,  "calories": 138, "default_serving": 200, "serving_unit": "g"},
    {"name": "Borek (Peynirli)",      "category": "Turkish", "protein": 9.0,  "fat": 14.0, "carbs": 26.0, "calories": 268, "default_serving": 150, "serving_unit": "g"},
    {"name": "Su Boregi",             "category": "Turkish", "protein": 10.0, "fat": 13.0, "carbs": 28.0, "calories": 270, "default_serving": 200, "serving_unit": "g"},
    {"name": "Pide (Karisik)",        "category": "Turkish", "protein": 12.0, "fat": 9.5,  "carbs": 35.0, "calories": 275, "default_serving": 250, "serving_unit": "g"},
    {"name": "Lahmacun",              "category": "Turkish", "protein": 10.5, "fat": 7.5,  "carbs": 30.0, "calories": 232, "default_serving": 150, "serving_unit": "g"},
    {"name": "Pilav (Bulgur)",        "category": "Turkish", "protein": 4.5,  "fat": 2.5,  "carbs": 28.0, "calories": 152, "default_serving": 200, "serving_unit": "g"},
    {"name": "Pilav (Pirinc)",        "category": "Turkish", "protein": 2.5,  "fat": 2.0,  "carbs": 28.5, "calories": 142, "default_serving": 200, "serving_unit": "g"},
    {"name": "Kuru Fasulye",          "category": "Turkish", "protein": 6.5,  "fat": 2.5,  "carbs": 18.0, "calories": 122, "default_serving": 250, "serving_unit": "g"},
    {"name": "Nohut Yemegi",          "category": "Turkish", "protein": 5.5,  "fat": 3.5,  "carbs": 20.0, "calories": 135, "default_serving": 250, "serving_unit": "g"},
    {"name": "Etli Sebze Yemegi",     "category": "Turkish", "protein": 9.0,  "fat": 6.5,  "carbs": 10.0, "calories": 136, "default_serving": 250, "serving_unit": "g"},
    {"name": "Corba (Sebze)",         "category": "Turkish", "protein": 2.5,  "fat": 1.5,  "carbs": 9.0,  "calories": 62,  "default_serving": 250, "serving_unit": "ml"},
    {"name": "Cacik",                 "category": "Turkish", "protein": 4.5,  "fat": 3.0,  "carbs": 4.5,  "calories": 63,  "default_serving": 150, "serving_unit": "g"},
    {"name": "Haydari",               "category": "Turkish", "protein": 5.5,  "fat": 6.0,  "carbs": 4.0,  "calories": 94,  "default_serving": 100, "serving_unit": "g"},
    {"name": "Hummus",                "category": "Turkish", "protein": 7.9,  "fat": 9.6,  "carbs": 14.3, "calories": 177, "default_serving": 100, "serving_unit": "g"},
    {"name": "Baklava",               "category": "Turkish", "protein": 5.5,  "fat": 24.0, "carbs": 40.0, "calories": 400, "default_serving": 100, "serving_unit": "g"},
    {"name": "Sutlac",                "category": "Turkish", "protein": 4.0,  "fat": 3.5,  "carbs": 22.0, "calories": 136, "default_serving": 150, "serving_unit": "g"},
    {"name": "Ayran",                 "category": "Turkish", "protein": 3.5,  "fat": 1.5,  "carbs": 4.0,  "calories": 44,  "default_serving": 250, "serving_unit": "ml"},
    {"name": "Tavuk Sote",            "category": "Turkish", "protein": 20.0, "fat": 7.5,  "carbs": 5.0,  "calories": 170, "default_serving": 200, "serving_unit": "g"},
    {"name": "Tavuk Izgara",          "category": "Turkish", "protein": 25.0, "fat": 5.5,  "carbs": 0.0,  "calories": 155, "default_serving": 150, "serving_unit": "g"},

    # ── Italian ───────────────────────────────────────────────────────────────
    {"name": "Pasta Bolognese",       "category": "Italian", "protein": 9.5,  "fat": 6.5,  "carbs": 28.0, "calories": 210, "default_serving": 300, "serving_unit": "g"},
    {"name": "Pasta Carbonara",       "category": "Italian", "protein": 11.0, "fat": 10.5, "carbs": 30.0, "calories": 260, "default_serving": 300, "serving_unit": "g"},
    {"name": "Pasta Pesto",           "category": "Italian", "protein": 8.0,  "fat": 11.0, "carbs": 30.0, "calories": 252, "default_serving": 300, "serving_unit": "g"},
    {"name": "Pasta Arrabiata",       "category": "Italian", "protein": 6.5,  "fat": 4.5,  "carbs": 30.0, "calories": 188, "default_serving": 300, "serving_unit": "g"},
    {"name": "Lasagna",               "category": "Italian", "protein": 10.5, "fat": 9.5,  "carbs": 20.0, "calories": 210, "default_serving": 300, "serving_unit": "g"},
    {"name": "Pizza Margherita",      "category": "Italian", "protein": 10.0, "fat": 8.5,  "carbs": 32.0, "calories": 245, "default_serving": 250, "serving_unit": "g"},
    {"name": "Risotto",               "category": "Italian", "protein": 5.5,  "fat": 6.5,  "carbs": 28.0, "calories": 195, "default_serving": 300, "serving_unit": "g"},
    {"name": "Tiramisu",              "category": "Italian", "protein": 5.5,  "fat": 17.0, "carbs": 28.0, "calories": 290, "default_serving": 150, "serving_unit": "g"},

    # ── International ─────────────────────────────────────────────────────────
    {"name": "Chicken Curry",         "category": "Indian",  "protein": 14.5, "fat": 8.5,  "carbs": 8.0,  "calories": 166, "default_serving": 300, "serving_unit": "g"},
    {"name": "Dal (Lentil Curry)",    "category": "Indian",  "protein": 7.5,  "fat": 3.5,  "carbs": 18.0, "calories": 133, "default_serving": 250, "serving_unit": "g"},
    {"name": "Chicken Fried Rice",    "category": "Asian",   "protein": 11.0, "fat": 5.5,  "carbs": 28.0, "calories": 210, "default_serving": 300, "serving_unit": "g"},
    {"name": "Pad Thai",              "category": "Asian",   "protein": 12.0, "fat": 7.0,  "carbs": 32.0, "calories": 240, "default_serving": 300, "serving_unit": "g"},
    {"name": "Sushi Roll (Mixed)",    "category": "Japanese","protein": 5.5,  "fat": 2.5,  "carbs": 20.0, "calories": 125, "default_serving": 200, "serving_unit": "g"},
    {"name": "Ramen",                 "category": "Japanese","protein": 10.0, "fat": 7.5,  "carbs": 26.0, "calories": 213, "default_serving": 400, "serving_unit": "ml"},
    {"name": "Beef Burger",           "category": "American","protein": 14.5, "fat": 14.0, "carbs": 22.0, "calories": 272, "default_serving": 200, "serving_unit": "g"},
    {"name": "Caesar Salad",          "category": "American","protein": 8.5,  "fat": 11.0, "carbs": 7.5,  "calories": 163, "default_serving": 200, "serving_unit": "g"},
    {"name": "Club Sandwich",         "category": "American","protein": 16.0, "fat": 13.0, "carbs": 28.0, "calories": 295, "default_serving": 250, "serving_unit": "g"},
    {"name": "Tacos (Chicken)",       "category": "Mexican", "protein": 13.0, "fat": 8.0,  "carbs": 20.0, "calories": 204, "default_serving": 200, "serving_unit": "g"},
    {"name": "Burrito (Beef)",        "category": "Mexican", "protein": 12.0, "fat": 9.5,  "carbs": 30.0, "calories": 255, "default_serving": 300, "serving_unit": "g"},
    {"name": "Tom Yum Soup",          "category": "Thai",    "protein": 5.5,  "fat": 2.5,  "carbs": 5.5,  "calories": 67,  "default_serving": 300, "serving_unit": "ml"},
    {"name": "Greek Salad",           "category": "Greek",   "protein": 4.5,  "fat": 9.0,  "carbs": 7.5,  "calories": 130, "default_serving": 200, "serving_unit": "g"},
    {"name": "Shakshuka",             "category": "Middle Eastern", "protein": 8.5, "fat": 9.5, "carbs": 9.0, "calories": 158, "default_serving": 250, "serving_unit": "g"},
    {"name": "Falafel",               "category": "Middle Eastern", "protein": 5.5, "fat": 5.0, "carbs": 17.0,"calories": 333, "default_serving": 100, "serving_unit": "g"},

    # ── Everyday meals ────────────────────────────────────────────────────────
    {"name": "Scrambled Eggs",        "category": "Breakfast","protein": 10.5, "fat": 10.5, "carbs": 1.5,  "calories": 143, "default_serving": 150, "serving_unit": "g"},
    {"name": "Omelette (Plain)",      "category": "Breakfast","protein": 11.0, "fat": 10.0, "carbs": 1.0,  "calories": 139, "default_serving": 150, "serving_unit": "g"},
    {"name": "Pancakes",              "category": "Breakfast","protein": 6.5,  "fat": 5.5,  "carbs": 28.0, "calories": 190, "default_serving": 150, "serving_unit": "g"},
    {"name": "Oatmeal with Milk",     "category": "Breakfast","protein": 5.5,  "fat": 3.5,  "carbs": 22.0, "calories": 143, "default_serving": 250, "serving_unit": "g"},
    {"name": "Avocado Toast",         "category": "Breakfast","protein": 5.5,  "fat": 9.5,  "carbs": 18.0, "calories": 180, "default_serving": 150, "serving_unit": "g"},
    {"name": "Grilled Chicken Breast","category": "Protein",  "protein": 31.0, "fat": 3.6,  "carbs": 0.0,  "calories": 165, "default_serving": 150, "serving_unit": "g"},
    {"name": "Salmon Fillet",         "category": "Protein",  "protein": 25.0, "fat": 13.0, "carbs": 0.0,  "calories": 208, "default_serving": 150, "serving_unit": "g"},
    {"name": "Tuna Salad",            "category": "Salad",    "protein": 18.0, "fat": 5.5,  "carbs": 4.0,  "calories": 136, "default_serving": 200, "serving_unit": "g"},
    {"name": "Lentil Soup",           "category": "Soup",     "protein": 4.5,  "fat": 1.2,  "carbs": 12.0, "calories": 78,  "default_serving": 250, "serving_unit": "ml"},
    {"name": "Tomato Soup",           "category": "Soup",     "protein": 2.0,  "fat": 1.5,  "carbs": 9.5,  "calories": 60,  "default_serving": 250, "serving_unit": "ml"},
    {"name": "Chicken Noodle Soup",   "category": "Soup",     "protein": 6.5,  "fat": 2.5,  "carbs": 9.0,  "calories": 85,  "default_serving": 300, "serving_unit": "ml"},
    {"name": "Vegetable Stir Fry",    "category": "Vegetarian","protein": 3.5, "fat": 4.5,  "carbs": 10.0, "calories": 95,  "default_serving": 250, "serving_unit": "g"},
    {"name": "Cheese Sandwich",       "category": "Sandwich", "protein": 11.5, "fat": 12.0, "carbs": 26.0, "calories": 260, "default_serving": 150, "serving_unit": "g"},
    {"name": "BLT Sandwich",          "category": "Sandwich", "protein": 13.0, "fat": 14.5, "carbs": 28.0, "calories": 295, "default_serving": 200, "serving_unit": "g"},
    {"name": "Yogurt with Granola",   "category": "Snack",    "protein": 8.5,  "fat": 5.0,  "carbs": 30.0, "calories": 198, "default_serving": 200, "serving_unit": "g"},
]

def seed_meals():
    count = 0
    for m in MEALS:
        exists = SavedFood.query.filter_by(name=m["name"], food_type="meal").first()
        if not exists:
            db.session.add(SavedFood(
                name=m["name"],
                brand=None,
                category=m.get("category"),
                protein=m["protein"],
                fat=m["fat"],
                carbs=m["carbs"],
                calories=m["calories"],
                default_serving=m.get("default_serving", 100),
                serving_unit=m.get("serving_unit", "g"),
                source="usda",
                food_type="meal",
                is_archived=False,
            ))
            count += 1
    db.session.commit()
    return count

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        n = seed_meals()
    print(f"Seeded {n} meals.")