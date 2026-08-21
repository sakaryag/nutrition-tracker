"""Seed two ready-to-use 7-day starter templates into the Template Library.

Idempotent: guarded by NutritionPlan name + is_template.
Exercises all content patterns: Fixed (A), Exchange/rotation (B),
Recipe (D via salad slot), Conditional/optional (F), and is_fallback items.
"""
import json
from models import db
from models.user import User
from models.nutrition_plan import NutritionPlan
from models.program_day import ProgramDay
from models.meal_slot import MealSlot
from models.slot_item import SlotItem
from models.program_guideline import ProgramGuideline
from models.weekly_category_quota import WeeklyCategoryQuota
from models.food_exchange_category import FoodExchangeCategory
from models.exchange_category_member import ExchangeCategoryMember
from models.recipe import Recipe
from models.recipe_ingredient import RecipeIngredient

TEMPLATE_A_NAME = "Balanced Weekly Plan A — Protein Rotation"
TEMPLATE_B_NAME = "Balanced Weekly Plan B — Fixed Main + Salad Rotation"

DAY_LABELS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_LABELS_TR = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]


def _get_or_create_system_user():
    user = User.query.filter_by(username="__system__").first()
    if user:
        return user
    user = User(username="__system__", is_admin=True)
    user.set_pw("!!system-seed-only!!")
    db.session.add(user)
    db.session.flush()
    return user


def _upsert_category(owner_id, name, name_tr, description, members):
    cat = FoodExchangeCategory.query.filter_by(name=name, owner_id=owner_id).first()
    if cat:
        return cat
    cat = FoodExchangeCategory(
        name=name, name_tr=name_tr, owner_id=owner_id, description=description
    )
    db.session.add(cat)
    db.session.flush()
    for i, m in enumerate(members):
        db.session.add(ExchangeCategoryMember(
            category_id=cat.id,
            food_name_override=m["name"],
            equivalent_qty=m["qty"],
            equivalent_unit=m["unit"],
            sort_order=i,
        ))
    return cat


def _upsert_recipe(owner_id, name, name_tr, category_tags, prep_notes, ingredients):
    r = Recipe.query.filter_by(name=name, owner_id=owner_id).first()
    if r:
        return r
    r = Recipe(
        name=name, name_tr=name_tr, owner_id=owner_id,
        category_tags=json.dumps(category_tags),
        prep_notes=prep_notes,
    )
    db.session.add(r)
    db.session.flush()
    for i, ing in enumerate(ingredients):
        db.session.add(RecipeIngredient(
            recipe_id=r.id,
            food_name_override=ing["name"],
            quantity=ing["qty"],
            unit=ing.get("unit", "g"),
            protein=ing.get("protein"),
            fat=ing.get("fat"),
            carbs=ing.get("carbs"),
            calories=ing.get("calories"),
            sort_order=i,
        ))
    db.session.flush()
    r.recalculate_totals()
    return r


def _add_slot(day_id, slot_name, slot_name_tr, sort_order, content_pattern="A", is_optional=False):
    slot = MealSlot(
        day_id=day_id,
        slot_name=slot_name,
        slot_name_tr=slot_name_tr,
        sort_order=sort_order,
        content_pattern=content_pattern,
        is_optional=is_optional,
    )
    db.session.add(slot)
    db.session.flush()
    return slot


def _item(slot_id, food_name_override, quantity, unit, sort_order,
          exchange_category_id=None, recipe_id=None,
          alternative_group=None, rotation_frequency=None,
          is_fallback=False, notes=None, notes_tr=None):
    db.session.add(SlotItem(
        slot_id=slot_id,
        food_name_override=food_name_override,
        quantity=quantity,
        unit=unit,
        sort_order=sort_order,
        exchange_category_id=exchange_category_id,
        recipe_id=recipe_id,
        alternative_group=alternative_group,
        rotation_frequency=rotation_frequency,
        is_fallback=is_fallback,
        notes=notes,
        notes_tr=notes_tr,
    ))


def seed_starter_templates():
    if NutritionPlan.query.filter_by(name=TEMPLATE_A_NAME, is_template=True).first():
        return  # already seeded

    owner = _get_or_create_system_user()

    # ------------------------------------------------------------------ #
    # Shared exchange categories                                           #
    # ------------------------------------------------------------------ #
    dairy_portion = _upsert_category(
        owner.id,
        name="Dairy Portion", name_tr="Süt Ürünü Porsiyonu",
        description="One dairy serving: yogurt, ayran, kefir, or milk",
        members=[
            {"name": "Low-fat yogurt",  "qty": 150, "unit": "g"},
            {"name": "Ayran",           "qty": 200, "unit": "ml"},
            {"name": "Kefir",           "qty": 150, "unit": "ml"},
            {"name": "Low-fat milk",    "qty": 200, "unit": "ml"},
        ],
    )
    nut_portion = _upsert_category(
        owner.id,
        name="Nut Portion", name_tr="Kuruyemiş Porsiyonu",
        description="One nut serving: almonds, walnuts, or hazelnuts",
        members=[
            {"name": "Almonds",   "qty": 15, "unit": "g"},
            {"name": "Walnuts",   "qty": 15, "unit": "g"},
            {"name": "Hazelnuts", "qty": 15, "unit": "g"},
        ],
    )
    starch_portion = _upsert_category(
        owner.id,
        name="Starch Portion", name_tr="Nişasta Porsiyonu",
        description="One starch serving: whole wheat bread, rice, or pasta",
        members=[
            {"name": "Whole wheat bread",           "qty": 40, "unit": "g"},
            {"name": "Cooked rice",                 "qty": 90, "unit": "g"},
            {"name": "Cooked whole grain pasta",    "qty": 90, "unit": "g"},
        ],
    )
    dairy_dessert = _upsert_category(
        owner.id,
        name="Dairy Dessert", name_tr="Sütlü Tatlı Porsiyonu",
        description="Light dairy dessert: rice pudding, custard, or pudding",
        members=[
            {"name": "Rice pudding", "qty": 120, "unit": "g"},
            {"name": "Custard",      "qty": 120, "unit": "g"},
            {"name": "Milk pudding", "qty": 120, "unit": "g"},
        ],
    )

    # ------------------------------------------------------------------ #
    # Shared recipes                                                       #
    # ------------------------------------------------------------------ #
    strawberry_salad = _upsert_recipe(
        owner.id,
        name="Strawberry & Arugula Salad",
        name_tr="Çilekli Roka Salatası",
        category_tags=["salad", "light", "dinner"],
        prep_notes=(
            "Toss fresh arugula with sliced strawberries and crushed walnuts. "
            "Drizzle with olive oil and balsamic vinegar. Season lightly."
        ),
        ingredients=[
            {"name": "Fresh arugula",    "qty": 60,  "unit": "g",  "protein": 1.6, "fat": 0.4, "carbs": 2.0,  "calories": 15},
            {"name": "Strawberries",     "qty": 80,  "unit": "g",  "protein": 0.7, "fat": 0.3, "carbs": 7.7,  "calories": 26},
            {"name": "Walnuts",          "qty": 10,  "unit": "g",  "protein": 1.5, "fat": 6.5, "carbs": 1.4,  "calories": 65},
            {"name": "Olive oil",        "qty": 5,   "unit": "ml", "protein": 0.0, "fat": 5.0, "carbs": 0.0,  "calories": 45},
            {"name": "Balsamic vinegar", "qty": 10,  "unit": "ml", "protein": 0.1, "fat": 0.0, "carbs": 2.7,  "calories": 11},
        ],
    )
    lentil_salad = _upsert_recipe(
        owner.id,
        name="Lentil Salad",
        name_tr="Mercimek Salatası",
        category_tags=["salad", "legume", "dinner"],
        prep_notes=(
            "Cook green lentils until just tender, drain and cool. "
            "Toss with diced tomato, cucumber and fresh parsley. "
            "Dress with olive oil, lemon juice, salt and cumin."
        ),
        ingredients=[
            {"name": "Green lentils (cooked)", "qty": 150, "unit": "g",  "protein": 12.0, "fat": 0.5, "carbs": 23.0, "calories": 143},
            {"name": "Tomato",                 "qty": 80,  "unit": "g",  "protein": 0.9,  "fat": 0.2, "carbs": 3.5,  "calories": 16},
            {"name": "Cucumber",               "qty": 60,  "unit": "g",  "protein": 0.4,  "fat": 0.1, "carbs": 1.8,  "calories": 9},
            {"name": "Fresh parsley",          "qty": 10,  "unit": "g",  "protein": 0.4,  "fat": 0.1, "carbs": 0.8,  "calories": 4},
            {"name": "Olive oil",              "qty": 8,   "unit": "ml", "protein": 0.0,  "fat": 8.0, "carbs": 0.0,  "calories": 72},
            {"name": "Lemon juice",            "qty": 15,  "unit": "ml", "protein": 0.1,  "fat": 0.1, "carbs": 1.3,  "calories": 4},
        ],
    )

    db.session.flush()

    # ================================================================== #
    # Template A — Protein Rotation                                       #
    # ================================================================== #
    plan_a = NutritionPlan(
        name=TEMPLATE_A_NAME,
        name_tr="Dengeli Haftalık Plan A — Protein Rotasyonu",
        description=(
            "7-day rotation plan. Breakfast and evening snack draw from the Dairy Portion exchange. "
            "Dinner protein rotates across chicken, beef, fish, turkey, legumes each day. "
            "Lunch is fixed. Mid-day snack is fixed; an optional add-on slot accommodates hunger."
        ),
        duration_days=7,
        created_by=owner.id,
        is_public=True,
        is_template=True,
        status="active",
        locale="tr",
    )
    db.session.add(plan_a)
    db.session.flush()

    for g in [
        ProgramGuideline(program_id=plan_a.id, guideline_type="general", sort_order=0,
            rule_text="Drink at least 2 litres of water daily.",
            rule_text_tr="Günde en az 2 litre su için."),
        ProgramGuideline(program_id=plan_a.id, guideline_type="frequency", sort_order=1,
            target_category_id=dairy_portion.id,
            frequency_min=2, frequency_max=2,
            rule_text="Two dairy portions per day: one at breakfast, one at evening snack.",
            rule_text_tr="Günde 2 süt ürünü porsiyonu: biri kahvaltıda, biri gece atişturmasında."),
        ProgramGuideline(program_id=plan_a.id, guideline_type="frequency", sort_order=2,
            target_category_id=nut_portion.id,
            frequency_min=1, frequency_max=1,
            rule_text="One nut portion per day as mid-morning snack.",
            rule_text_tr="Öğle arası atişturmada günde bir kuruyemiş porsiyonu."),
        ProgramGuideline(program_id=plan_a.id, guideline_type="cooking_method", sort_order=3,
            rule_text="Prefer grilling, steaming or baking. Avoid frying.",
            rule_text_tr="Izgara, buharlama veya fırın yöntemlerini tercih edin. Kızartmadan kaçının."),
    ]:
        db.session.add(g)

    db.session.add(WeeklyCategoryQuota(
        program_id=plan_a.id,
        exchange_category_id=dairy_portion.id,
        quota_per_week=14,
        notes="2 per day × 7 days (breakfast + evening snack)",
    ))
    db.session.add(WeeklyCategoryQuota(
        program_id=plan_a.id,
        exchange_category_id=nut_portion.id,
        quota_per_week=7,
        notes="1 per day (mid-morning snack)",
    ))

    # Dinner protein options that cycle day by day
    PROTEIN_ROTATION = [
        ("Grilled chicken breast",  130, "g"),
        ("Lean beef stew",          130, "g"),
        ("Baked salmon",            130, "g"),
        ("Grilled turkey breast",   130, "g"),
        ("Red lentil soup",         300, "ml"),
        ("Baked sea bass",          130, "g"),
        ("Chickpea stew",           250, "ml"),
    ]

    for d in range(7):
        day = ProgramDay(
            program_id=plan_a.id,
            day_offset=d,
            label=DAY_LABELS[d],
            label_tr=DAY_LABELS_TR[d],
            sort_order=d,
        )
        db.session.add(day)
        db.session.flush()

        # --- Breakfast (B: Dairy Portion exchange) ---
        s = _add_slot(day.id, "Breakfast", "Kahvaltı", sort_order=0, content_pattern="B")
        for i, (fname, qty, unit) in enumerate([
            ("Low-fat yogurt", 150, "g"),
            ("Ayran",          200, "ml"),
            ("Kefir",          150, "ml"),
            ("Low-fat milk",   200, "ml"),
        ]):
            _item(s.id, fname, qty, unit, i,
                  exchange_category_id=dairy_portion.id,
                  alternative_group=1, rotation_frequency=2)
        _item(s.id, "Whole wheat toast",   40,  "g",  10)
        _item(s.id, "Cucumber + tomato",   150, "g",  11)
        _item(s.id, "Plain crackers + cheese (emergency fallback)", 30, "g", 99, is_fallback=True)

        # --- Lunch (A: Fixed) ---
        s = _add_slot(day.id, "Lunch", "Öğle Yemeği", sort_order=1, content_pattern="A")
        _item(s.id, "Grilled chicken breast", 120, "g", 0)
        _item(s.id, "Starch Portion", 1, "serving", 1, exchange_category_id=starch_portion.id)
        _item(s.id, "Mixed greens salad",     80,  "g",  2)

        # --- Mid-day Snack (A: Fixed) ---
        s = _add_slot(day.id, "Snack", "Ara Öğün", sort_order=2, content_pattern="A")
        _item(s.id, "Nut Portion",    1,   "serving", 0, exchange_category_id=nut_portion.id)
        _item(s.id, "Seasonal fruit", 150, "g",       1)

        # --- Optional extra snack (F: Conditional/optional) ---
        s = _add_slot(day.id, "Extra Snack (optional)", "Ek Atişturma (isteğe bağlı)",
                      sort_order=3, content_pattern="F", is_optional=True)
        _item(s.id, "Fruit or vegetable sticks", 100, "g", 0,
              notes="Add only if hungry between snack and dinner.",
              notes_tr="Ara öğün ile akşam yemeği arasında açlık hissedilirse ekleyin.")

        # --- Dinner (B: protein rotation) ---
        s = _add_slot(day.id, "Dinner", "Akşam Yemeği", sort_order=4, content_pattern="B")
        for i, (pname, pqty, punit) in enumerate(PROTEIN_ROTATION):
            _item(s.id, pname, pqty, punit, i,
                  alternative_group=1, rotation_frequency=1)
        _item(s.id, "Starch side",        1,   "serving", 10, exchange_category_id=starch_portion.id)
        _item(s.id, "Steamed vegetables", 150, "g",       11)
        _item(s.id, "2 boiled eggs + rye bread (fallback)", 2, "piece", 99, is_fallback=True)

        # --- Evening Snack (B: Dairy Dessert exchange) ---
        s = _add_slot(day.id, "Evening Snack", "Gece Atişturması", sort_order=5, content_pattern="B")
        for i, (dname, dqty, dunit) in enumerate([
            ("Rice pudding",               120, "g"),
            ("Custard",                    120, "g"),
            ("Milk pudding",               120, "g"),
            ("Low-fat yogurt with honey",  150, "g"),
        ]):
            _item(s.id, dname, dqty, dunit, i,
                  exchange_category_id=dairy_dessert.id,
                  alternative_group=1, rotation_frequency=2)

    # ================================================================== #
    # Template B — Fixed Main + Salad Rotation                           #
    # ================================================================== #
    plan_b = NutritionPlan(
        name=TEMPLATE_B_NAME,
        name_tr="Dengeli Haftalık Plan B — Sabit Ana Öğün + Salata Rotasyonu",
        description=(
            "7-day plan with a consistent fixed breakfast and fixed dinner base. "
            "The dinner salad rotates between two signature recipes: "
            "Strawberry & Arugula Salad and Lentil Salad. "
            "Evening snack slot is optional."
        ),
        duration_days=7,
        created_by=owner.id,
        is_public=True,
        is_template=True,
        status="active",
        locale="tr",
    )
    db.session.add(plan_b)
    db.session.flush()

    for g in [
        ProgramGuideline(program_id=plan_b.id, guideline_type="general", sort_order=0,
            rule_text="Eat breakfast within 1 hour of waking. Keep meal timing consistent daily.",
            rule_text_tr="Uyanıştan sonraki 1 saat içinde kahvaltı yapın. Öğün saatlerini her gün tutarlı tutun."),
        ProgramGuideline(program_id=plan_b.id, guideline_type="cooking_method", sort_order=1,
            rule_text="Use at most 1 tablespoon of olive oil per meal. Avoid frying.",
            rule_text_tr="Öğün başına en fazla 1 yemek kaşığı zeytinyаğı kullanın. Kızartmadan kaçının."),
        ProgramGuideline(program_id=plan_b.id, guideline_type="frequency", sort_order=2,
            frequency_min=3, frequency_max=4,
            rule_text="Alternate dinner salad: each recipe appears 3–4 times per week.",
            rule_text_tr="Akşam salatasını dönüşmlü yapın: her tarif haftada 3–4 kez yer alsın."),
    ]:
        db.session.add(g)

    db.session.add(WeeklyCategoryQuota(
        program_id=plan_b.id,
        exchange_category_id=dairy_portion.id,
        quota_per_week=7,
        notes="1 per day at breakfast",
    ))

    for d in range(7):
        day = ProgramDay(
            program_id=plan_b.id,
            day_offset=d,
            label=DAY_LABELS[d],
            label_tr=DAY_LABELS_TR[d],
            sort_order=d,
        )
        db.session.add(day)
        db.session.flush()

        # --- Breakfast (A: Fixed with dairy exchange) ---
        s = _add_slot(day.id, "Breakfast", "Kahvaltı", sort_order=0, content_pattern="A")
        _item(s.id, "Dairy Portion",  1,   "serving", 0, exchange_category_id=dairy_portion.id)
        _item(s.id, "2 boiled eggs",  2,   "piece",   1)
        _item(s.id, "Whole wheat bread", 40, "g",     2)
        _item(s.id, "Tomato + cucumber", 150, "g",    3)
        _item(s.id, "Olives",         15,  "g",       4)

        # --- Morning Snack (A: Fixed) ---
        s = _add_slot(day.id, "Morning Snack", "Kuşluk", sort_order=1, content_pattern="A")
        _item(s.id, "Nut Portion",         1,   "serving", 0, exchange_category_id=nut_portion.id)
        _item(s.id, "1 medium apple or pear", 150, "g",   1)

        # --- Lunch (A: Fixed) ---
        s = _add_slot(day.id, "Lunch", "Öğle Yemeği", sort_order=2, content_pattern="A")
        _item(s.id, "Grilled chicken or turkey breast", 120, "g", 0)
        _item(s.id, "Starch Portion", 1, "serving", 1, exchange_category_id=starch_portion.id)
        _item(s.id, "Steamed or raw seasonal vegetables", 150, "g", 2)

        # --- Afternoon Snack (A: Fixed) ---
        s = _add_slot(day.id, "Afternoon Snack", "İkindi Arası", sort_order=3, content_pattern="A")
        _item(s.id, "Low-fat yogurt", 150, "g", 0)
        _item(s.id, "Seasonal fruit", 100, "g", 1)

        # --- Dinner base (A: Fixed protein + veg) ---
        s = _add_slot(day.id, "Dinner", "Akşam Yemeği", sort_order=4, content_pattern="A")
        _item(s.id, "Grilled fish or chicken", 150, "g",  0)
        _item(s.id, "Steamed vegetables",       200, "g",  1)

        # --- Dinner salad (B: Recipe rotation between two salads) ---
        s = _add_slot(day.id, "Dinner Salad", "Akşam Salatası", sort_order=5, content_pattern="B")
        _item(s.id, "Strawberry & Arugula Salad", 1, "serving", 0,
              recipe_id=strawberry_salad.id,
              alternative_group=1, rotation_frequency=4)
        _item(s.id, "Lentil Salad", 1, "serving", 1,
              recipe_id=lentil_salad.id,
              alternative_group=1, rotation_frequency=3)
        _item(s.id, "Simple green salad (fallback)", 100, "g", 99, is_fallback=True)

        # --- Evening Snack (B: optional, Dairy Dessert exchange) ---
        s = _add_slot(day.id, "Evening Snack", "Gece Atişturması",
                      sort_order=6, content_pattern="B", is_optional=True)
        _item(s.id, "Dairy Dessert", 1, "serving", 0,
              exchange_category_id=dairy_dessert.id,
              alternative_group=1, rotation_frequency=3)
        _item(s.id, "Herbal tea only (if not hungry)", 200, "ml", 1,
              alternative_group=2, rotation_frequency=4,
              notes="Skip the dessert if not hungry; herbal tea is fine.",
              notes_tr="Aç değilseniz tatlıyı atlayabilirsiniz; bitkisel çay uygun.")

    db.session.commit()
