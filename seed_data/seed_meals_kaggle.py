import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import json
import pandas as pd
from app import create_app
from models import db
from models.recipe_catalog import RecipeCatalog

TURKISH_PATH = Path(r"C:\Users\z004mvzt\.cache\kagglehub\datasets\bit104\turkish-recipes-structured\versions\1\recipes_groq_cleaned.json")
A3M_PATH = Path(r"C:\Users\z004mvzt\.cache\kagglehub\datasets\nazmussakibrupol\3a2m-cooking-recipe-dataset\versions\1\3A2M.csv")


def import_turkish(app):
    print("\n--- Turkish Recipes (bit104/turkish-recipes-structured) ---")
    if not TURKISH_PATH.exists():
        print(f"  ERROR: File not found: {TURKISH_PATH}")
        return 0

    with open(TURKISH_PATH, encoding="utf-8") as f:
        data = json.load(f)
    print(f"  Records in file: {len(data)}")

    count = 0
    skipped = 0
    with app.app_context():
        # Build a set of existing names for this source to avoid per-row queries
        existing = set(
            r[0] for r in db.session.query(RecipeCatalog.name)
            .filter_by(source="turkish-kaggle").all()
        )
        batch = []
        for item in data:
            name = str(item.get("tarif_adi") or item.get("name") or item.get("title") or "").strip()
            if not name:
                continue
            if name in existing:
                skipped += 1
                continue
            category = str(item.get("kategori") or item.get("category") or "").strip() or None
            batch.append(RecipeCatalog(
                name=name,
                category=category,
                cuisine="Turkish",
                source="turkish-kaggle",
            ))
            existing.add(name)
            count += 1

        if batch:
            db.session.add_all(batch)
            db.session.commit()

    print(f"  Imported: {count}  |  Skipped (already exist): {skipped}")
    return count


def import_3a2m(app):
    print("\n--- 3A2M Cooking Recipes (nazmussakibrupol/3a2m-cooking-recipe-dataset) ---")
    if not A3M_PATH.exists():
        print(f"  ERROR: File not found: {A3M_PATH}")
        return 0

    print("  Reading CSV (this may take a moment)...")
    df = pd.read_csv(A3M_PATH, usecols=["title", "genre"], dtype=str, low_memory=False)
    print(f"  Total rows in CSV: {len(df)}")

    # Filter: title length between 3 and 80, drop nulls
    df = df.dropna(subset=["title"])
    df["title"] = df["title"].str.strip()
    df = df[df["title"].str.len().between(3, 80)]
    print(f"  After length filter: {len(df)}")

    # Deduplicate by title
    df = df.drop_duplicates(subset=["title"])
    print(f"  After deduplication: {len(df)}")

    # Sample up to 15,000 spread across genres (up to 1,500 per genre)
    sampled = (
        df.groupby("genre", dropna=False)
        .apply(lambda x: x.sample(min(len(x), 1500), random_state=42))
        .reset_index(drop=True)
    )
    sampled = sampled.head(15000)
    print(f"  Sampled: {len(sampled)}")

    count = 0
    skipped = 0
    BATCH_SIZE = 500

    with app.app_context():
        # Build set of existing names for this source
        existing = set(
            r[0] for r in db.session.query(RecipeCatalog.name)
            .filter_by(source="3a2m-kaggle").all()
        )
        batch = []
        for _, row in sampled.iterrows():
            name = str(row["title"]).strip()
            if not name or name in existing:
                skipped += 1
                continue
            genre = row.get("genre")
            category = str(genre).strip() if pd.notna(genre) and str(genre).strip() else None
            batch.append(RecipeCatalog(
                name=name,
                category=category,
                cuisine=None,
                source="3a2m-kaggle",
            ))
            existing.add(name)
            count += 1

            if len(batch) >= BATCH_SIZE:
                db.session.add_all(batch)
                db.session.commit()
                batch = []
                print(f"  ...committed {count} rows so far")

        if batch:
            db.session.add_all(batch)
            db.session.commit()

    print(f"  Imported: {count}  |  Skipped (already exist): {skipped}")
    return count


if __name__ == "__main__":
    app = create_app()
    turkish_count = import_turkish(app)
    a3m_count = import_3a2m(app)
    print(f"\nDone.")
    print(f"  Turkish recipes imported: {turkish_count}")
    print(f"  3A2M recipes imported:    {a3m_count}")
    print(f"  Total:                    {turkish_count + a3m_count}")