"""
Curated meal seed -- real macros per 100g from USDA / nutritionix / verified sources.
Run: python seed_data/meals.py
"""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from models import db
from models.saved_food import SavedFood

MEALS = [
    # -- Turkish ------------------------------------------------------------------
    {"name": "Mercimek Corbasi",      "category": "Turkish", "protein": 4.5,  "fat": 1.2,  "carbs": 12.0, "calories": 78,  "default_serving": 250, "serving_unit": "ml", "valid_units": '["ml","cup","glass"]'},
    {"name": "Ezogelin Corbasi",      "category": "Turkish", "protein": 4.2,  "fat": 1.5,  "carbs": 13.0, "calories": 83,  "default_serving": 250, "serving_unit": "ml", "valid_units": '["ml","cup","glass"]'},
    {"name": "Tarhana Corbasi",       "category": "Turkish", "protein": 3.8,  "fat": 1.8,  "carbs": 11.5, "calories": 76,  "default_serving": 250, "serving_unit": "ml", "valid_units": '["ml","cup","glass"]'},
    {"name": "Iskender Kebab",        "category": "Turkish", "protein": 14.5, "fat": 11.2, "carbs": 14.0, "calories": 215, "default_serving": 300, "serving_unit": "g",  "valid_units": '["g","oz","serving"]'},
    {"name": "Adana Kebab",           "category": "Turkish", "protein": 17.0, "fat": 14.0, "carbs": 2.5,  "calories": 208, "default_serving": 200, "serving_unit": "g",  "valid_units": '["g","oz","serving"]'},
    {"name": "Doner Kebab",           "category": "Turkish", "protein": 16.0, "fat": 10.5, "carbs": 3.0,  "calories": 174, "default_serving": 200, "serving_unit": "g",  "valid_units": '["g","oz","serving"]'},
    {"name": "Kofte",                 "category": "Turkish", "protein": 15.5, "fat": 11.0, "carbs": 8.5,  "calories": 196, "default_serving": 150, "serving_unit": "g",  "valid_units": '["g","oz","piece","serving"]'},
    {"name": "Manti",                 "category": "Turkish", "protein": 9.5,  "fat": 7.5,  "carbs": 28.0, "calories": 220, "default_serving": 250, "serving_unit": "g",  "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Karniyarik",            "category": "Turkish", "protein": 8.5,  "fat": 9.0,  "carbs": 12.0, "calories": 165, "default_serving": 250, "serving_unit": "g",  "valid_units": '["g","oz","piece","serving"]'},
    {"name": "Imam Bayildi",          "category": "Turkish", "protein": 2.5,  "fat": 7.5,  "carbs": 10.0, "calories": 120, "default_serving": 200, "serving_unit": "g",  "valid_units": '["g","oz","piece","serving"]'},
    {"name": "Dolma (Yaprak)",        "category": "Turkish", "protein": 3.5,  "fat": 4.5,  "carbs": 18.0, "calories": 128, "default_serving": 150, "serving_unit": "g",  "valid_units": '["g","oz","piece","serving"]'},
    {"name": "Sarma",                 "category": "Turkish", "protein": 4.0,  "fat": 5.0,  "carbs": 19.0, "calories": 138, "default_serving": 150, "serving_unit": "g",  "valid_units": '["g","oz","piece","serving"]'},
    {"name": "Menemen",               "category": "Turkish", "protein": 8.5,  "fat": 9.0,  "carbs": 5.5,  "calories": 138, "default_serving": 200, "serving_unit": "g",  "valid_units": '["g","oz","serving"]'},
    {"name": "Borek (Peynirli)",      "category": "Turkish", "protein": 9.0,  "fat": 14.0, "carbs": 26.0, "calories": 268, "default_serving": 150, "serving_unit": "g",  "valid_units": '["g","oz","slice","piece","serving"]'},
    {"name": "Su Boregi",             "category": "Turkish", "protein": 10.0, "fat": 13.0, "carbs": 28.0, "calories": 270, "default_serving": 200, "serving_unit": "g",  "valid_units": '["g","oz","slice","piece","serving"]'},
    {"name": "Pide (Karisik)",        "category": "Turkish", "protein": 12.0, "fat": 9.5,  "carbs": 35.0, "calories": 275, "default_serving": 250, "serving_unit": "g",  "valid_units": '["g","oz","slice","piece","serving"]'},
    {"name": "Lahmacun",              "category": "Turkish", "protein": 10.5, "fat": 7.5,  "carbs": 30.0, "calories": 232, "default_serving": 150, "serving_unit": "g",  "valid_units": '["g","oz","slice","piece","serving"]'},
    {"name": "Pilav (Bulgur)",        "category": "Turkish", "protein": 4.5,  "fat": 2.5,  "carbs": 28.0, "calories": 152, "default_serving": 200, "serving_unit": "g",  "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Pilav (Pirinc)",        "category": "Turkish", "protein": 2.5,  "fat": 2.0,  "carbs": 28.5, "calories": 142, "default_serving": 200, "serving_unit": "g",  "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Kuru Fasulye",          "category": "Turkish", "protein": 6.5,  "fat": 2.5,  "carbs": 18.0, "calories": 122, "default_serving": 250, "serving_unit": "g",  "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Nohut Yemegi",          "category": "Turkish", "protein": 5.5,  "fat": 3.5,  "carbs": 20.0, "calories": 135, "default_serving": 250, "serving_unit": "g",  "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Etli Sebze Yemegi",     "category": "Turkish", "protein": 9.0,  "fat": 6.5,  "carbs": 10.0, "calories": 136, "default_serving": 250, "serving_unit": "g",  "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Corba (Sebze)",         "category": "Turkish", "protein": 2.5,  "fat": 1.5,  "carbs": 9.0,  "calories": 62,  "default_serving": 250, "serving_unit": "ml", "valid_units": '["ml","cup","glass"]'},
    {"name": "Cacik",                 "category": "Turkish", "protein": 4.5,  "fat": 3.0,  "carbs": 4.5,  "calories": 63,  "default_serving": 150, "serving_unit": "g",  "valid_units": '["g","oz","tbsp","tsp","cup","serving"]'},
    {"name": "Haydari",               "category": "Turkish", "protein": 5.5,  "fat": 6.0,  "carbs": 4.0,  "calories": 94,  "default_serving": 100, "serving_unit": "g",  "valid_units": '["g","oz","tbsp","tsp","cup","serving"]'},
    {"name": "Hummus",                "category": "Turkish", "protein": 7.9,  "fat": 9.6,  "carbs": 14.3, "calories": 177, "default_serving": 100, "serving_unit": "g",  "valid_units": '["g","oz","tbsp","tsp","cup","serving"]'},
    {"name": "Baklava",               "category": "Turkish", "protein": 5.5,  "fat": 24.0, "carbs": 40.0, "calories": 400, "default_serving": 100, "serving_unit": "g",  "valid_units": '["g","oz","piece","serving"]'},
    {"name": "Sutlac",                "category": "Turkish", "protein": 4.0,  "fat": 3.5,  "carbs": 22.0, "calories": 136, "default_serving": 150, "serving_unit": "g",  "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Ayran",                 "category": "Turkish", "protein": 3.5,  "fat": 1.5,  "carbs": 4.0,  "calories": 44,  "default_serving": 250, "serving_unit": "ml", "valid_units": '["ml","cup","glass"]'},
    {"name": "Tavuk Sote",            "category": "Turkish", "protein": 20.0, "fat": 7.5,  "carbs": 5.0,  "calories": 170, "default_serving": 200, "serving_unit": "g",  "valid_units": '["g","oz","serving"]'},
    {"name": "Tavuk Izgara",          "category": "Turkish", "protein": 25.0, "fat": 5.5,  "carbs": 0.0,  "calories": 155, "default_serving": 150, "serving_unit": "g",  "valid_units": '["g","oz","serving"]'},

    # -- Italian ------------------------------------------------------------------
    {"name": "Pasta Bolognese",       "category": "Italian", "protein": 9.5,  "fat": 6.5,  "carbs": 28.0, "calories": 210, "default_serving": 300, "serving_unit": "g", "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Pasta Carbonara",       "category": "Italian", "protein": 11.0, "fat": 10.5, "carbs": 30.0, "calories": 260, "default_serving": 300, "serving_unit": "g", "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Pasta Pesto",           "category": "Italian", "protein": 8.0,  "fat": 11.0, "carbs": 30.0, "calories": 252, "default_serving": 300, "serving_unit": "g", "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Pasta Arrabiata",       "category": "Italian", "protein": 6.5,  "fat": 4.5,  "carbs": 30.0, "calories": 188, "default_serving": 300, "serving_unit": "g", "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Lasagna",               "category": "Italian", "protein": 10.5, "fat": 9.5,  "carbs": 20.0, "calories": 210, "default_serving": 300, "serving_unit": "g", "valid_units": '["g","oz","slice","serving"]'},
    {"name": "Pizza Margherita",      "category": "Italian", "protein": 10.0, "fat": 8.5,  "carbs": 32.0, "calories": 245, "default_serving": 250, "serving_unit": "g", "valid_units": '["g","oz","slice","piece","serving"]'},
    {"name": "Risotto",               "category": "Italian", "protein": 5.5,  "fat": 6.5,  "carbs": 28.0, "calories": 195, "default_serving": 300, "serving_unit": "g", "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Tiramisu",              "category": "Italian", "protein": 5.5,  "fat": 17.0, "carbs": 28.0, "calories": 290, "default_serving": 150, "serving_unit": "g", "valid_units": '["g","oz","serving"]'},

    # -- International ------------------------------------------------------------
    {"name": "Chicken Curry",         "category": "Indian",  "protein": 14.5, "fat": 8.5,  "carbs": 8.0,  "calories": 166, "default_serving": 300, "serving_unit": "g", "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Dal (Lentil Curry)",    "category": "Indian",  "protein": 7.5,  "fat": 3.5,  "carbs": 18.0, "calories": 133, "default_serving": 250, "serving_unit": "g", "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Chicken Fried Rice",    "category": "Asian",   "protein": 11.0, "fat": 5.5,  "carbs": 28.0, "calories": 210, "default_serving": 300, "serving_unit": "g", "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Pad Thai",              "category": "Asian",   "protein": 12.0, "fat": 7.0,  "carbs": 32.0, "calories": 240, "default_serving": 300, "serving_unit": "g", "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Sushi Roll (Mixed)",    "category": "Japanese","protein": 5.5,  "fat": 2.5,  "carbs": 20.0, "calories": 125, "default_serving": 200, "serving_unit": "g", "valid_units": '["g","oz","piece","serving"]'},
    {"name": "Ramen",                 "category": "Japanese","protein": 10.0, "fat": 7.5,  "carbs": 26.0, "calories": 213, "default_serving": 400, "serving_unit": "ml","valid_units": '["ml","cup","glass"]'},
    {"name": "Beef Burger",           "category": "American","protein": 14.5, "fat": 14.0, "carbs": 22.0, "calories": 272, "default_serving": 200, "serving_unit": "g", "valid_units": '["g","oz","piece","serving"]'},
    {"name": "Caesar Salad",          "category": "American","protein": 8.5,  "fat": 11.0, "carbs": 7.5,  "calories": 163, "default_serving": 200, "serving_unit": "g", "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Club Sandwich",         "category": "American","protein": 16.0, "fat": 13.0, "carbs": 28.0, "calories": 295, "default_serving": 250, "serving_unit": "g", "valid_units": '["g","oz","piece","serving"]'},
    {"name": "Tacos (Chicken)",       "category": "Mexican", "protein": 13.0, "fat": 8.0,  "carbs": 20.0, "calories": 204, "default_serving": 200, "serving_unit": "g", "valid_units": '["g","oz","piece","serving"]'},
    {"name": "Burrito (Beef)",        "category": "Mexican", "protein": 12.0, "fat": 9.5,  "carbs": 30.0, "calories": 255, "default_serving": 300, "serving_unit": "g", "valid_units": '["g","oz","piece","serving"]'},
    {"name": "Tom Yum Soup",          "category": "Thai",    "protein": 5.5,  "fat": 2.5,  "carbs": 5.5,  "calories": 67,  "default_serving": 300, "serving_unit": "ml","valid_units": '["ml","cup","glass"]'},
    {"name": "Greek Salad",           "category": "Greek",   "protein": 4.5,  "fat": 9.0,  "carbs": 7.5,  "calories": 130, "default_serving": 200, "serving_unit": "g", "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Shakshuka",             "category": "Middle Eastern", "protein": 8.5, "fat": 9.5, "carbs": 9.0, "calories": 158, "default_serving": 250, "serving_unit": "g", "valid_units": '["g","oz","serving"]'},
    {"name": "Falafel",               "category": "Middle Eastern", "protein": 5.5, "fat": 5.0, "carbs": 17.0,"calories": 333, "default_serving": 100, "serving_unit": "g", "valid_units": '["g","oz","piece","serving"]'},

    # -- Everyday meals -----------------------------------------------------------
    {"name": "Scrambled Eggs",        "category": "Breakfast","protein": 10.5, "fat": 10.5, "carbs": 1.5,  "calories": 143, "default_serving": 150, "serving_unit": "g", "valid_units": '["g","oz","serving"]'},
    {"name": "Omelette (Plain)",      "category": "Breakfast","protein": 11.0, "fat": 10.0, "carbs": 1.0,  "calories": 139, "default_serving": 150, "serving_unit": "g", "valid_units": '["g","oz","piece","serving"]'},
    {"name": "Pancakes",              "category": "Breakfast","protein": 6.5,  "fat": 5.5,  "carbs": 28.0, "calories": 190, "default_serving": 150, "serving_unit": "g", "valid_units": '["g","oz","piece","serving"]'},
    {"name": "Oatmeal with Milk",     "category": "Breakfast","protein": 5.5,  "fat": 3.5,  "carbs": 22.0, "calories": 143, "default_serving": 250, "serving_unit": "g", "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Avocado Toast",         "category": "Breakfast","protein": 5.5,  "fat": 9.5,  "carbs": 18.0, "calories": 180, "default_serving": 150, "serving_unit": "g", "valid_units": '["g","oz","slice","serving"]'},
    {"name": "Grilled Chicken Breast","category": "Protein",  "protein": 31.0, "fat": 3.6,  "carbs": 0.0,  "calories": 165, "default_serving": 150, "serving_unit": "g", "valid_units": '["g","oz","serving"]'},
    {"name": "Salmon Fillet",         "category": "Protein",  "protein": 25.0, "fat": 13.0, "carbs": 0.0,  "calories": 208, "default_serving": 150, "serving_unit": "g", "valid_units": '["g","oz","serving"]'},
    {"name": "Tuna Salad",            "category": "Salad",    "protein": 18.0, "fat": 5.5,  "carbs": 4.0,  "calories": 136, "default_serving": 200, "serving_unit": "g", "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Lentil Soup",           "category": "Soup",     "protein": 4.5,  "fat": 1.2,  "carbs": 12.0, "calories": 78,  "default_serving": 250, "serving_unit": "ml","valid_units": '["ml","cup","glass"]'},
    {"name": "Tomato Soup",           "category": "Soup",     "protein": 2.0,  "fat": 1.5,  "carbs": 9.5,  "calories": 60,  "default_serving": 250, "serving_unit": "ml","valid_units": '["ml","cup","glass"]'},
    {"name": "Chicken Noodle Soup",   "category": "Soup",     "protein": 6.5,  "fat": 2.5,  "carbs": 9.0,  "calories": 85,  "default_serving": 300, "serving_unit": "ml","valid_units": '["ml","cup","glass"]'},
    {"name": "Vegetable Stir Fry",    "category": "Vegetarian","protein": 3.5, "fat": 4.5,  "carbs": 10.0, "calories": 95,  "default_serving": 250, "serving_unit": "g", "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Cheese Sandwich",       "category": "Sandwich", "protein": 11.5, "fat": 12.0, "carbs": 26.0, "calories": 260, "default_serving": 150, "serving_unit": "g", "valid_units": '["g","oz","piece","serving"]'},
    {"name": "BLT Sandwich",          "category": "Sandwich", "protein": 13.0, "fat": 14.5, "carbs": 28.0, "calories": 295, "default_serving": 200, "serving_unit": "g", "valid_units": '["g","oz","piece","serving"]'},
    {"name": "Yogurt with Granola",   "category": "Snack",    "protein": 8.5,  "fat": 5.0,  "carbs": 30.0, "calories": 198, "default_serving": 200, "serving_unit": "g", "valid_units": '["g","oz","cup","serving"]'},
]

# ---------------------------------------------------------------------------
# Turkish meals v2 — proper Turkish names (with diacritics) + name_tr field
# Macros are per serving (not per 100g). Calories = P*4 + F*9 + C*4.
# ---------------------------------------------------------------------------
TURKISH_MEALS_V2 = [
    # -- Soups (Çorbalar) -------------------------------------------------------
    {"name": "Mercimek Çorbası",       "name_tr": "Mercimek Çorbası",       "category": "Turkish", "protein": 9.0,  "fat": 4.0,  "carbs": 22.0, "calories": 160, "default_serving": 250, "serving_unit": "ml", "valid_units": '["ml","cup","glass"]'},
    {"name": "Domates Çorbası",        "name_tr": "Domates Çorbası",        "category": "Turkish", "protein": 4.0,  "fat": 3.0,  "carbs": 15.0, "calories": 103, "default_serving": 250, "serving_unit": "ml", "valid_units": '["ml","cup","glass"]'},
    {"name": "Tavuk Çorbası",          "name_tr": "Tavuk Çorbası",          "category": "Turkish", "protein": 12.0, "fat": 4.0,  "carbs": 10.0, "calories": 124, "default_serving": 250, "serving_unit": "ml", "valid_units": '["ml","cup","glass"]'},
    {"name": "Ezogelin Çorbası",       "name_tr": "Ezogelin Çorbası",       "category": "Turkish", "protein": 8.0,  "fat": 3.0,  "carbs": 25.0, "calories": 159, "default_serving": 250, "serving_unit": "ml", "valid_units": '["ml","cup","glass"]'},
    {"name": "Tarhana Çorbası",        "name_tr": "Tarhana Çorbası",        "category": "Turkish", "protein": 6.0,  "fat": 2.0,  "carbs": 20.0, "calories": 122, "default_serving": 250, "serving_unit": "ml", "valid_units": '["ml","cup","glass"]'},
    {"name": "Yayla Çorbası",          "name_tr": "Yayla Çorbası",          "category": "Turkish", "protein": 8.0,  "fat": 5.0,  "carbs": 18.0, "calories": 149, "default_serving": 250, "serving_unit": "ml", "valid_units": '["ml","cup","glass"]'},
    {"name": "Işkembe Çorbası",        "name_tr": "Işkembe Çorbası",        "category": "Turkish", "protein": 14.0, "fat": 6.0,  "carbs": 6.0,  "calories": 134, "default_serving": 250, "serving_unit": "ml", "valid_units": '["ml","cup","glass"]'},

    # -- Rice & Grains (Tahıllar) -----------------------------------------------
    {"name": "Pilav",                  "name_tr": "Pilav",                  "category": "Turkish", "protein": 5.0,  "fat": 5.0,  "carbs": 50.0, "calories": 265, "default_serving": 200, "serving_unit": "g",  "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Bulgur Pilavı",          "name_tr": "Bulgur Pilavı",          "category": "Turkish", "protein": 7.0,  "fat": 3.0,  "carbs": 45.0, "calories": 235, "default_serving": 200, "serving_unit": "g",  "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Bezelye Pilavı",         "name_tr": "Bezelye Pilavı",         "category": "Turkish", "protein": 7.0,  "fat": 5.0,  "carbs": 48.0, "calories": 265, "default_serving": 200, "serving_unit": "g",  "valid_units": '["g","oz","cup","serving"]'},

    # -- Main Dishes (Ana Yemekler) ---------------------------------------------
    {"name": "İskender Kebap",         "name_tr": "İskender Kebap",         "category": "Turkish", "protein": 35.0, "fat": 20.0, "carbs": 30.0, "calories": 440, "default_serving": 350, "serving_unit": "g",  "valid_units": '["g","oz","serving"]'},
    {"name": "Döner Kebap",            "name_tr": "Döner Kebap",            "category": "Turkish", "protein": 28.0, "fat": 18.0, "carbs": 35.0, "calories": 414, "default_serving": 300, "serving_unit": "g",  "valid_units": '["g","oz","serving"]'},
    {"name": "Adana Kebap",            "name_tr": "Adana Kebap",            "category": "Turkish", "protein": 35.0, "fat": 22.0, "carbs": 5.0,  "calories": 358, "default_serving": 250, "serving_unit": "g",  "valid_units": '["g","oz","serving"]'},
    {"name": "Şiş Kebap",              "name_tr": "Şiş Kebap",              "category": "Turkish", "protein": 38.0, "fat": 8.0,  "carbs": 4.0,  "calories": 240, "default_serving": 200, "serving_unit": "g",  "valid_units": '["g","oz","serving"]'},
    {"name": "Köfte",                  "name_tr": "Köfte",                  "category": "Turkish", "protein": 30.0, "fat": 18.0, "carbs": 8.0,  "calories": 314, "default_serving": 200, "serving_unit": "g",  "valid_units": '["g","oz","piece","serving"]'},
    {"name": "Karnıyarık",             "name_tr": "Karnıyarık",             "category": "Turkish", "protein": 18.0, "fat": 15.0, "carbs": 20.0, "calories": 287, "default_serving": 300, "serving_unit": "g",  "valid_units": '["g","oz","piece","serving"]'},
    {"name": "İmam Bayıldı",           "name_tr": "İmam Bayıldı",           "category": "Turkish", "protein": 4.0,  "fat": 18.0, "carbs": 18.0, "calories": 250, "default_serving": 250, "serving_unit": "g",  "valid_units": '["g","oz","piece","serving"]'},
    {"name": "Hünkar Beğendi",         "name_tr": "Hünkar Beğendi",         "category": "Turkish", "protein": 30.0, "fat": 20.0, "carbs": 22.0, "calories": 388, "default_serving": 350, "serving_unit": "g",  "valid_units": '["g","oz","serving"]'},
    {"name": "Kuzu Tandır",            "name_tr": "Kuzu Tandır",            "category": "Turkish", "protein": 36.0, "fat": 22.0, "carbs": 0.0,  "calories": 342, "default_serving": 200, "serving_unit": "g",  "valid_units": '["g","oz","serving"]'},
    {"name": "Fırın Tavuk",            "name_tr": "Fırın Tavuk",            "category": "Turkish", "protein": 38.0, "fat": 12.0, "carbs": 2.0,  "calories": 268, "default_serving": 200, "serving_unit": "g",  "valid_units": '["g","oz","serving"]'},
    {"name": "Balık Izgara",           "name_tr": "Balık Izgara",           "category": "Turkish", "protein": 36.0, "fat": 8.0,  "carbs": 0.0,  "calories": 216, "default_serving": 200, "serving_unit": "g",  "valid_units": '["g","oz","serving"]'},
    {"name": "Hamsi Tava",             "name_tr": "Hamsi Tava",             "category": "Turkish", "protein": 24.0, "fat": 12.0, "carbs": 10.0, "calories": 244, "default_serving": 150, "serving_unit": "g",  "valid_units": '["g","oz","serving"]'},
    {"name": "Kalamar Tava",           "name_tr": "Kalamar Tava",           "category": "Turkish", "protein": 18.0, "fat": 14.0, "carbs": 16.0, "calories": 262, "default_serving": 150, "serving_unit": "g",  "valid_units": '["g","oz","serving"]'},

    # -- Legumes (Baklagiller) --------------------------------------------------
    {"name": "Kuru Fasulye",           "name_tr": "Kuru Fasulye",           "category": "Turkish", "protein": 18.0, "fat": 8.0,  "carbs": 38.0, "calories": 296, "default_serving": 300, "serving_unit": "g",  "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Nohut Yemeği",           "name_tr": "Nohut Yemeği",           "category": "Turkish", "protein": 14.0, "fat": 7.0,  "carbs": 40.0, "calories": 279, "default_serving": 300, "serving_unit": "g",  "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Mercimek Köftesi",       "name_tr": "Mercimek Köftesi",       "category": "Turkish", "protein": 14.0, "fat": 3.0,  "carbs": 35.0, "calories": 223, "default_serving": 200, "serving_unit": "g",  "valid_units": '["g","oz","piece","serving"]'},
    {"name": "Zeytinyağlı Fasulye",    "name_tr": "Zeytinyağlı Fasulye",    "category": "Turkish", "protein": 5.0,  "fat": 8.0,  "carbs": 20.0, "calories": 172, "default_serving": 250, "serving_unit": "g",  "valid_units": '["g","oz","cup","serving"]'},

    # -- Vegetables (Sebze Yemekleri) ------------------------------------------
    {"name": "Zeytinyağlı Patlıcan",   "name_tr": "Zeytinyağlı Patlıcan",   "category": "Turkish", "protein": 3.0,  "fat": 12.0, "carbs": 15.0, "calories": 180, "default_serving": 200, "serving_unit": "g",  "valid_units": '["g","oz","serving"]'},
    {"name": "Türlü",                  "name_tr": "Türlü",                  "category": "Turkish", "protein": 5.0,  "fat": 8.0,  "carbs": 22.0, "calories": 180, "default_serving": 300, "serving_unit": "g",  "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Patlıcan Musakka",       "name_tr": "Patlıcan Musakka",       "category": "Turkish", "protein": 18.0, "fat": 15.0, "carbs": 18.0, "calories": 279, "default_serving": 300, "serving_unit": "g",  "valid_units": '["g","oz","serving"]'},

    # -- Breads & Pastry (Ekmek ve Hamur İşleri) --------------------------------
    {"name": "Simit",                  "name_tr": "Simit",                  "category": "Turkish", "protein": 10.0, "fat": 4.0,  "carbs": 55.0, "calories": 296, "default_serving": 1,   "serving_unit": "piece", "g_per_unit": 120, "valid_units": '["piece","g","oz"]'},
    {"name": "Açma",                   "name_tr": "Açma",                   "category": "Turkish", "protein": 7.0,  "fat": 12.0, "carbs": 42.0, "calories": 304, "default_serving": 1,   "serving_unit": "piece", "g_per_unit": 90,  "valid_units": '["piece","g","oz"]'},
    {"name": "Poğaça",                 "name_tr": "Poğaça",                 "category": "Turkish", "protein": 6.0,  "fat": 10.0, "carbs": 30.0, "calories": 234, "default_serving": 1,   "serving_unit": "piece", "g_per_unit": 80,  "valid_units": '["piece","g","oz"]'},
    {"name": "Börek",                  "name_tr": "Börek",                  "category": "Turkish", "protein": 12.0, "fat": 16.0, "carbs": 28.0, "calories": 304, "default_serving": 150, "serving_unit": "g",     "valid_units": '["g","oz","slice","piece","serving"]'},
    {"name": "Gözleme",                "name_tr": "Gözleme",                "category": "Turkish", "protein": 14.0, "fat": 12.0, "carbs": 40.0, "calories": 324, "default_serving": 200, "serving_unit": "g",     "valid_units": '["g","oz","piece","serving"]'},
    {"name": "Lahmacun",               "name_tr": "Lahmacun",               "category": "Turkish", "protein": 14.0, "fat": 8.0,  "carbs": 38.0, "calories": 280, "default_serving": 1,   "serving_unit": "piece", "g_per_unit": 140, "valid_units": '["piece","g","oz"]'},
    {"name": "Pide",                   "name_tr": "Pide",                   "category": "Turkish", "protein": 20.0, "fat": 15.0, "carbs": 48.0, "calories": 407, "default_serving": 250, "serving_unit": "g",     "valid_units": '["g","oz","slice","piece","serving"]'},
    {"name": "Katmer",                 "name_tr": "Katmer",                 "category": "Turkish", "protein": 8.0,  "fat": 22.0, "carbs": 42.0, "calories": 398, "default_serving": 150, "serving_unit": "g",     "valid_units": '["g","oz","piece","serving"]'},

    # -- Mezze & Appetizers (Mezeler) -------------------------------------------
    {"name": "Cacık",                  "name_tr": "Cacık",                  "category": "Turkish", "protein": 7.0,  "fat": 4.0,  "carbs": 8.0,  "calories": 96,  "default_serving": 150, "serving_unit": "g",  "valid_units": '["g","oz","tbsp","cup","serving"]'},
    {"name": "Haydari",                "name_tr": "Haydari",                "category": "Turkish", "protein": 9.0,  "fat": 6.0,  "carbs": 6.0,  "calories": 114, "default_serving": 100, "serving_unit": "g",  "valid_units": '["g","oz","tbsp","cup","serving"]'},
    {"name": "Humus",                  "name_tr": "Humus",                  "category": "Turkish", "protein": 8.0,  "fat": 10.0, "carbs": 18.0, "calories": 194, "default_serving": 100, "serving_unit": "g",  "valid_units": '["g","oz","tbsp","cup","serving"]'},
    {"name": "Patates Salatası",       "name_tr": "Patates Salatası",       "category": "Turkish", "protein": 4.0,  "fat": 8.0,  "carbs": 28.0, "calories": 200, "default_serving": 200, "serving_unit": "g",  "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Patlıcan Salatası",      "name_tr": "Patlıcan Salatası",      "category": "Turkish", "protein": 2.0,  "fat": 6.0,  "carbs": 10.0, "calories": 102, "default_serving": 150, "serving_unit": "g",  "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Sigara Böreği",          "name_tr": "Sigara Böreği",          "category": "Turkish", "protein": 8.0,  "fat": 14.0, "carbs": 22.0, "calories": 246, "default_serving": 4,   "serving_unit": "piece", "g_per_unit": 30, "valid_units": '["piece","g","oz"]'},

    # -- Salads (Salatalar) -----------------------------------------------------
    {"name": "Çoban Salatası",         "name_tr": "Çoban Salatası",         "category": "Turkish", "protein": 3.0,  "fat": 6.0,  "carbs": 10.0, "calories": 106, "default_serving": 200, "serving_unit": "g",  "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Gavurdağı Salatası",     "name_tr": "Gavurdağı Salatası",     "category": "Turkish", "protein": 4.0,  "fat": 10.0, "carbs": 12.0, "calories": 154, "default_serving": 200, "serving_unit": "g",  "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Tarator",                "name_tr": "Tarator",                "category": "Turkish", "protein": 4.0,  "fat": 8.0,  "carbs": 10.0, "calories": 128, "default_serving": 100, "serving_unit": "g",  "valid_units": '["g","oz","tbsp","cup","serving"]'},
    {"name": "Mercimek Salatası",      "name_tr": "Mercimek Salatası",      "category": "Turkish", "protein": 12.0, "fat": 5.0,  "carbs": 28.0, "calories": 205, "default_serving": 200, "serving_unit": "g",  "valid_units": '["g","oz","cup","serving"]'},

    # -- Desserts (Tatlılar) ----------------------------------------------------
    {"name": "Baklava",                "name_tr": "Baklava",                "category": "Turkish", "protein": 4.0,  "fat": 12.0, "carbs": 36.0, "calories": 268, "default_serving": 1,   "serving_unit": "piece", "g_per_unit": 60, "valid_units": '["piece","g","oz"]'},
    {"name": "Kadayıf",                "name_tr": "Kadayıf",                "category": "Turkish", "protein": 5.0,  "fat": 14.0, "carbs": 40.0, "calories": 306, "default_serving": 100, "serving_unit": "g",  "valid_units": '["g","oz","piece","serving"]'},
    {"name": "Sütlaç",                 "name_tr": "Sütlaç",                 "category": "Turkish", "protein": 6.0,  "fat": 4.0,  "carbs": 38.0, "calories": 212, "default_serving": 200, "serving_unit": "g",  "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Aşure",                  "name_tr": "Aşure",                  "category": "Turkish", "protein": 6.0,  "fat": 2.0,  "carbs": 45.0, "calories": 222, "default_serving": 200, "serving_unit": "g",  "valid_units": '["g","oz","cup","serving"]'},
    {"name": "Lokum",                  "name_tr": "Lokum",                  "category": "Turkish", "protein": 0.0,  "fat": 0.0,  "carbs": 36.0, "calories": 144, "default_serving": 3,   "serving_unit": "piece", "g_per_unit": 15, "valid_units": '["piece","g","oz"]'},
    {"name": "Revani",                 "name_tr": "Revani",                 "category": "Turkish", "protein": 5.0,  "fat": 6.0,  "carbs": 48.0, "calories": 266, "default_serving": 100, "serving_unit": "g",  "valid_units": '["g","oz","piece","serving"]'},
    {"name": "Helva",                  "name_tr": "Helva",                  "category": "Turkish", "protein": 5.0,  "fat": 12.0, "carbs": 24.0, "calories": 224, "default_serving": 50,  "serving_unit": "g",  "valid_units": '["g","oz","piece","serving"]'},
    {"name": "Muhallebi",              "name_tr": "Muhallebi",              "category": "Turkish", "protein": 5.0,  "fat": 4.0,  "carbs": 30.0, "calories": 176, "default_serving": 150, "serving_unit": "g",  "valid_units": '["g","oz","cup","serving"]'},

    # -- Drinks (İçecekler) -----------------------------------------------------
    {"name": "Ayran",                  "name_tr": "Ayran",                  "category": "Turkish", "protein": 4.0,  "fat": 2.0,  "carbs": 4.0,  "calories": 50,  "default_serving": 200, "serving_unit": "ml", "valid_units": '["ml","cup","glass"]'},
    {"name": "Türk Çayı",              "name_tr": "Türk Çayı",              "category": "Turkish", "protein": 0.0,  "fat": 0.0,  "carbs": 0.0,  "calories": 2,   "default_serving": 200, "serving_unit": "ml", "valid_units": '["ml","cup","glass"]'},

    # -- Additional Authentic Dishes --------------------------------------------
    {"name": "Çiğ Köfte",              "name_tr": "Çiğ Köfte",              "category": "Turkish", "protein": 8.0,  "fat": 2.0,  "carbs": 35.0, "calories": 190, "default_serving": 200, "serving_unit": "g",  "valid_units": '["g","oz","piece","serving"]'},
    {"name": "Künefe",                 "name_tr": "Künefe",                 "category": "Turkish", "protein": 8.0,  "fat": 18.0, "carbs": 38.0, "calories": 346, "default_serving": 150, "serving_unit": "g",  "valid_units": '["g","oz","piece","serving"]'},
    {"name": "İçli Köfte",             "name_tr": "İçli Köfte",             "category": "Turkish", "protein": 10.0, "fat": 14.0, "carbs": 20.0, "calories": 246, "default_serving": 4,   "serving_unit": "piece", "g_per_unit": 40, "valid_units": '["piece","g","oz"]'},
    {"name": "Çılbır",                 "name_tr": "Çılbır",                 "category": "Turkish", "protein": 15.0, "fat": 12.0, "carbs": 6.0,  "calories": 192, "default_serving": 200, "serving_unit": "g",  "valid_units": '["g","oz","serving"]'},
    {"name": "Mücver",                 "name_tr": "Mücver",                 "category": "Turkish", "protein": 8.0,  "fat": 10.0, "carbs": 18.0, "calories": 194, "default_serving": 150, "serving_unit": "g",  "valid_units": '["g","oz","piece","serving"]'},
    {"name": "Kavurma",                "name_tr": "Kavurma",                "category": "Turkish", "protein": 30.0, "fat": 20.0, "carbs": 0.0,  "calories": 300, "default_serving": 200, "serving_unit": "g",  "valid_units": '["g","oz","serving"]'},
    {"name": "Etli Ekmek",             "name_tr": "Etli Ekmek",             "category": "Turkish", "protein": 16.0, "fat": 10.0, "carbs": 36.0, "calories": 298, "default_serving": 200, "serving_unit": "g",  "valid_units": '["g","oz","piece","serving"]'},
]


def seed_turkish_meals():
    """Seed authentic Turkish dishes with proper names and name_tr.

    Idempotent: skips rows where exact name + food_type='meal' already exists.
    Also updates name_tr on existing rows when name_tr is NULL.
    Returns count of newly inserted rows.
    """
    count = 0
    for m in TURKISH_MEALS_V2:
        exists = SavedFood.query.filter_by(name=m["name"], food_type="meal").first()
        if not exists:
            db.session.add(SavedFood(
                name=m["name"],
                name_tr=m.get("name_tr"),
                brand=None,
                category=m.get("category"),
                protein=m["protein"],
                fat=m["fat"],
                carbs=m["carbs"],
                calories=m["calories"],
                default_serving=m.get("default_serving", 100),
                serving_unit=m.get("serving_unit", "g"),
                g_per_unit=m.get("g_per_unit"),
                source="custom",
                food_type="meal",
                is_archived=False,
                valid_units=m.get("valid_units"),
            ))
            count += 1
        else:
            # Back-fill name_tr and valid_units on existing records
            if m.get("name_tr") and not exists.name_tr:
                exists.name_tr = m["name_tr"]
            if exists.valid_units is None and m.get("valid_units"):
                exists.valid_units = m["valid_units"]
    db.session.commit()
    return count


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
                source="custom",
                food_type="meal",
                is_archived=False,
                valid_units=m.get("valid_units"),
            ))
            count += 1
        else:
            # Update valid_units on existing records if not yet set
            if exists.valid_units is None and m.get("valid_units"):
                exists.valid_units = m["valid_units"]
    db.session.commit()
    count += seed_turkish_meals()
    return count

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        n = seed_meals()
    print(f"Seeded {n} meals.")