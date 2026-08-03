"""
Fix foods.csv and live DB with verified per-serving USDA values.

The CSV has two classes of errors:
  A) Piece/slice foods where macros are stored per-100g instead of per-piece.
     Some piece foods are correct (apple, avocado, prepared meals) — only
     explicit overrides are safe here.
  B) Tbsp/tsp condiments where macros are stored per-100g instead of per-tbsp.
     All of these are wrong and can be fixed via overrides.

Values sourced from USDA FoodData Central (per serving as listed in the CSV).
"""

import csv, os, sys

CSV_PATH = os.path.join(os.path.dirname(__file__), "seed_data", "foods.csv")

# ── Overrides keyed by usda_fdc_id ────────────────────────────────────────
# (protein, fat, carbs, calories, fiber, sugar)  — all per DEFAULT serving
# None = leave existing value unchanged
OVERRIDES = {
    # Eggs (50g each) — was stored per-100g, should be per-egg
    170013: (6.3,  5.0,  0.6,  72, None, None),   # raw
    170014: (6.3,  5.0,  0.6,  72, None, None),   # boiled
    170015: (6.3,  5.3,  0.4,  78, None, None),   # fried (extra fat from cooking)

    # Sausage patty 45g — was per-100g
    170003: None,  # this is chicken thigh, skip

    # String cheese 28g — was per-100g: P=28g → 7.8g
    # usda_fdc_id for String cheese is implicit in CSV — matched by name below

    # Butter per tbsp (~14g) — was per-100g: F=81g → 11.5g
    # Tbsp foods don't have fdc_ids that map cleanly so handled by name patterns below
}

# ── Name-based overrides (matched as exact name substrings) ───────────────
# (name_substring, protein, fat, carbs, calories, fiber, sugar)
# For piece foods: values are per-piece (default_serving=1)
# For tbsp foods: values are per-tbsp (multiply by default_serving if > 1)
NAME_OVERRIDES = [
    # ── Eggs ──────────────────────────────────────────────────────────────
    ("Egg, whole, raw",          6.3,  5.0, 0.6,  72, None, None),
    ("Egg, whole, boiled",       6.3,  5.0, 0.6,  72, None, None),
    ("Egg, whole, fried",        6.3,  5.3, 0.4,  78, None, None),

    # ── Dairy / Cheese (per piece) ─────────────────────────────────────────
    ("String cheese, mozzarella", 7.8, 5.6, 0.3,  85, None, None),  # 28g piece

    # ── Sausage patty 45g ─────────────────────────────────────────────────
    ("Sausage patty, pork, cooked", 5.0, 7.7, 0.5,  95, None, None),

    # ── Tbsp / Tsp condiments & fats ──────────────────────────────────────
    # Values are per 1 tbsp; if default_serving > 1 we multiply below.
    ("Butter, salted",           0.1, 11.5, 0.0, 102, None, None),
    ("Butter, unsalted",         0.1, 11.5, 0.0, 102, None, None),
    ("Ghee (clarified butter)",  0.0, 12.7, 0.0, 112, None, None),
    ("Ghee",                     0.0, 12.7, 0.0, 112, None, None),
    ("Heavy cream, whipping",    0.3,  5.4, 0.4,  51, None, None),
    ("Sour cream",               0.5,  2.9, 1.0,  33, None, None),
    ("Whipped cream",            0.2,  2.0, 0.5,  19, None, None),
    ("Parmesan cheese, grated",  1.9,  1.3, 0.2,  22, None, None),

    # Nut/seed butters per tbsp
    ("Peanut butter, powdered",  5.0,  1.5, 4.0,  45, 0.0, 2.0),
    ("Peanut butter, chunky",    7.7, 16.0, 7.7, 188, 1.3, 3.4),
    ("Peanut butter, natural",   7.7, 16.0, 7.7, 188, 1.3, 3.4),
    ("Peanut butter, creamy",    7.7, 16.0, 7.7, 188, 1.3, 3.4),
    ("Almond butter",            6.7, 18.0, 6.0, 196, 1.6, 2.3),
    ("Cashew butter",            5.6, 14.0, 9.4, 188, 0.6, 2.4),
    ("Sunflower seed butter",    5.5, 16.0, 7.5, 197, 1.0, 2.0),
    ("Tahini, from hulled",      2.6,  8.1, 3.2,  89, 1.0, 0.0),
    ("Tahini, from whole",       2.4,  7.2, 3.1,  85, 1.0, 0.0),
    ("Sesame paste (tahini)",    2.4,  7.2, 3.1,  85, 1.0, 0.0),

    # Oils per tbsp (~14g) — all are ~120 kcal, F~14g
    ("Olive oil, extra virgin",  0.0, 13.5, 0.0, 119, None, None),
    ("Olive oil, light",         0.0, 13.5, 0.0, 119, None, None),
    ("Olive oil, virgin",        0.0, 13.5, 0.0, 119, None, None),
    ("Coconut oil",              0.0, 13.6, 0.0, 117, None, None),
    ("Vegetable oil",            0.0, 13.6, 0.0, 120, None, None),
    ("Canola oil",               0.0, 14.0, 0.0, 124, None, None),
    ("Sesame oil",               0.0, 14.0, 0.0, 120, None, None),
    ("Avocado oil",              0.0, 14.0, 0.0, 124, None, None),
    ("Peanut oil",               0.0, 13.5, 0.0, 119, None, None),
    ("Sunflower oil",            0.0, 14.0, 0.0, 120, None, None),
    ("Safflower oil",            0.0, 14.0, 0.0, 120, None, None),
    ("Grapeseed oil",            0.0, 14.0, 0.0, 120, None, None),
    ("Walnut oil",               0.0, 14.0, 0.0, 120, None, None),
    ("Flaxseed oil",             0.0, 14.0, 0.0, 120, None, None),
    ("MCT oil",                  0.0, 14.0, 0.0, 115, None, None),
    ("Mustard seed oil",         0.0, 14.0, 0.0, 120, None, None),

    # Mayonnaise per tbsp
    ("Mayonnaise, olive oil",    0.1, 11.0, 0.0,  99, None, None),
    ("Mayonnaise, light",        0.1,  5.0, 0.3,  50, None, None),
    ("Mayonnaise, regular",      0.1, 11.0, 0.0,  99, None, None),
    ("Margarine, light",         0.1,  5.5, 0.5,  49, None, None),
    ("Margarine, regular",       0.2, 11.0, 0.0,  99, None, None),
    ("Lard",                     0.0, 12.8, 0.0, 115, None, None),
    ("Shortening, vegetable",    0.0, 12.2, 0.0, 110, None, None),

    # Sauces / condiments per tbsp
    ("Soy sauce",               1.7,  0.1, 1.6,  11, 0.1, 0.5),
    ("Soy sauce, low sodium",   1.5,  0.1, 1.0,   9, 0.1, 0.5),
    ("Tamari sauce",            1.7,  0.1, 1.6,  11, 0.1, 0.5),
    ("Chocolate chips, semi-sweet", 0.7, 3.2, 9.4, 64, 0.5, 7.5),
    ("Chocolate chips, dark",   0.9,  4.2, 8.8,  68, 0.7, 5.2),
    ("Honey",                   0.0,  0.0,17.3,  64, 0.0,17.3),
    ("Maple syrup",             0.0,  0.0,13.4,  52, 0.0,12.1),
    ("Agave nectar",            0.0,  0.0,15.2,  60, 0.0,15.2),
    ("Corn syrup",              0.0,  0.0,16.1,  53, 0.0, 0.0),
    ("Pesto, basil",            1.0,  8.7, 1.1, 100, 0.3, 0.0),
    ("Alfredo sauce",           1.1,  4.8, 0.8,  51, 0.0, 0.0),
    ("BBQ sauce, low sugar",    0.0,  0.0, 1.0,   5, 0.0, 0.5),
    ("Barbecue sauce",          0.1,  0.0, 2.9,  11, 0.0, 2.4),
    ("Hummus, roasted red pepper", 1.0, 1.3, 3.0, 28, 0.5, 0.2),
    ("Hummus, roasted garlic",  1.2,  1.4, 2.7,  27, 0.6, 0.1),
    ("Hummus, classic",         1.2,  1.4, 2.7,  27, 0.6, 0.1),
    ("Guacamole, light",        0.3,  1.2, 1.5,  17, 0.5, 0.1),
    ("Guacamole",               0.5,  2.8, 1.5,  33, 0.9, 0.1),
    ("Miso, white",             1.2,  0.9, 2.4,  25, 0.3, 0.6),
    ("Miso, red",               1.9,  0.9, 1.4,  25, 0.3, 0.3),
    ("Soy butter",              5.6,  9.8, 1.1, 110, 0.5, 0.0),

    # Sugars per tsp
    ("White granulated sugar",  0.0,  0.0, 4.0,  16, None, 4.0),
    ("Brown sugar",             0.0,  0.0, 4.0,  15, None, 4.0),
]

TBSP_TSP_UNITS = {"tbsp", "tsp"}
# These name overrides are per-tbsp/tsp × default_serving
PIECE_UNITS = {"piece", "slice"}
# Piece overrides are per-default-serving (not scaled further)


def r2(v): return round(v, 2)


def find_override(name):
    name_l = name.lower().strip()
    for row in NAME_OVERRIDES:
        pattern = row[0].lower().strip()
        # Require the pattern to match from the start of the name, or after
        # a comma/space, to avoid "honey" matching "honeycrisp" etc.
        if name_l == pattern:
            return row[1:]
        if name_l.startswith(pattern + ",") or name_l.startswith(pattern + " "):
            return row[1:]
        # Also allow pattern embedded after a comma-space: "Cereal, Honey Nut"
        # but only if the food's serving unit is tbsp/tsp (condiments)
        # For safety, only do exact-prefix or exact-name matching.
    return None


def fix_rows(rows):
    fixed = 0
    for row in rows:
        name   = row["name"].strip()
        unit   = row["serving_unit"].strip()
        ov     = find_override(name)
        if ov is None:
            continue

        srv_str = row["default_serving"].strip()
        srv = float(srv_str) if srv_str else 1.0

        p_ov, f_ov, c_ov, k_ov, fi_ov, su_ov = ov

        if unit in TBSP_TSP_UNITS:
            # overrides are per-1-tbsp/tsp; scale up if serving is > 1
            scale = srv
        else:
            # piece/slice: overrides are per-serving already
            scale = 1.0

        row["protein"]  = r2(p_ov * scale)
        row["fat"]      = r2(f_ov * scale)
        row["carbs"]    = r2(c_ov * scale)
        row["calories"] = round(k_ov * scale)
        if fi_ov is not None:
            row["fiber"] = r2(fi_ov * scale)
        if su_ov is not None:
            row["sugar"] = r2(su_ov * scale)
        fixed += 1

    print(f"Fixed {fixed} rows.")
    return rows


def load_csv():
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        return list(reader), fieldnames


def write_csv(rows, fieldnames):
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows to {CSV_PATH}")


def patch_db():
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from app import create_app
    from models import db
    from models.saved_food import SavedFood

    app = create_app()
    with app.app_context():
        rows, _ = load_csv()
        updated = 0
        for row in rows:
            fdc_id_str = row.get("usda_fdc_id", "").strip()
            if not fdc_id_str:
                continue
            fdc_id = int(fdc_id_str)
            food = SavedFood.query.filter_by(usda_fdc_id=fdc_id).first()
            if food is None:
                continue

            def _f(k):
                v = row.get(k, "").strip()
                return float(v) if v else None

            food.protein  = _f("protein")  or 0
            food.fat      = _f("fat")      or 0
            food.carbs    = _f("carbs")    or 0
            food.calories = _f("calories") or 0
            fi = _f("fiber")
            su = _f("sugar")
            if fi is not None: food.fiber = fi
            if su is not None: food.sugar = su
            updated += 1

        db.session.commit()
        print(f"DB: updated {updated} rows.")


if __name__ == "__main__":
    rows, fieldnames = load_csv()

    if "--preview" in sys.argv:
        import copy
        original = copy.deepcopy(rows)
        fix_rows(rows)
        for orig, fixed in zip(original, rows):
            if orig != fixed:
                u = orig["serving_unit"]
                srv = orig["default_serving"]
                print(f"  {orig['name'][:52]:52} | unit={u:6} srv={srv}")
                print(f"    BEFORE: P={orig['protein']:6} F={orig['fat']:6} C={orig['carbs']:6} Cal={orig['calories']}")
                print(f"    AFTER:  P={fixed['protein']:6} F={fixed['fat']:6} C={fixed['carbs']:6} Cal={fixed['calories']}")
        sys.exit(0)

    fix_rows(rows)
    write_csv(rows, fieldnames)

    if "--db" in sys.argv:
        patch_db()
    else:
        print("Pass --db to also update the live database.")
