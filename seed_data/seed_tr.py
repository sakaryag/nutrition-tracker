import sys
sys.path.insert(0, r'C:\Users\z004mvzt\nutrition-tracker')
from app import create_app
from models import db
from models.saved_food import SavedFood

app = create_app()

FOODS = [
  # (name, category, calories, protein, fat, carbs)
  # Corbalar
  ("Adile Sultan Usulü Sebze Çorbası", "Çorba", 45, 1.81, 2.23, 4.50),
  ("Ezogelin Çorbası", "Çorba", 42, 1.9, 1.2, 5.95),
  ("Fırınlanmış Mercimek Çorbası", "Çorba", 28, 1.11, 0.80, 3.99),
  ("Adile Sultan Usulü Yoğurt Çorbası", "Çorba", 94, 5.2, 4.5, 8.23),
  ("Kaşarlı Domates Çorbası", "Çorba", 36, 2.00, 1.73, 3.07),
  ("Köz Patlıcan Çorbası", "Çorba", 29, 0.9, 1.9, 2.10),
  ("Ayran Aşı Çorbası", "Çorba", 62, 2.37, 2.73, 6.96),
  ("Terbiyeli Tavuk Suyu Çorbası", "Çorba", 35, 2.5, 1.2, 3.53),
  ("Tarhana Çorbası (Ege Usulü)", "Çorba", 59, 2.30, 3.29, 4.99),
  ("Kelle Paça Çorbası (Antep Usulü)", "Çorba", 128, 11.5, 7.0, 4.67),
  # Etli Yemekler
  ("İzmir Köfte", "Etli Yemek", 107, 6.66, 4.50, 10.03),
  ("Püre Yatağında Kadınbudu Köfte", "Etli Yemek", 174, 9.1, 8.1, 16.20),
  ("Karışık Izgara ve Bulgur Pilavı", "Etli Yemek", 138, 10.00, 6.80, 9.30),
  ("Izgara Köfte ve Buharda Sebzeler", "Etli Yemek", 90, 7.50, 4.3, 5.20),
  ("Püre Yatağında Mangalda Köfte", "Etli Yemek", 119, 6.6, 6.70, 8.00),
  ("Beğendili Mangalda Köfte", "Etli Yemek", 130, 7.2, 8.7, 5.80),
  ("Mangalda Köfte ve Köz Domates Soslu Penne", "Etli Yemek", 171, 9.50, 9.30, 12.40),
  ("Mangalda Köfte ve Şehriyeli Pirinç Pilavı", "Etli Yemek", 165, 9.8, 7.2, 15.20),
  ("Özbek Ev Mantısı", "Etli Yemek", 149, 5.00, 5.00, 21.00),
  ("Kayseri Ev Mantısı", "Etli Yemek", 141, 5.00, 5.00, 19.00),
  ("Dana Kavurma ve Pirinç Pilavı", "Etli Yemek", 128, 6.00, 8.00, 8.00),
  ("Et Sote ve Kaşarlı Patates Püresi", "Etli Yemek", 98, 6.3, 3.2, 11.10),
  ("Hünkarbeğendi", "Etli Yemek", 134, 6.30, 9.60, 5.60),
  ("Etli Mantar Sote", "Etli Yemek", 140, 12.00, 9.00, 6.00),
  ("Kıymalı Lazanya", "Etli Yemek", 140, 7.5, 5.0, 16.20),
  ("Orman Kebabı", "Etli Yemek", 131, 7.3, 6.00, 12.00),
  ("Kuzu Tandır ve İç Pilav", "Etli Yemek", 175, 7.0, 11.0, 12.00),
  ("Kuzu Tandır ve Şehriyeli Pirinç Pilavı", "Etli Yemek", 170, 8.00, 10.0, 12.00),
  # Tavuklu Yemekler
  ("Hindi Tandır ve Buharda Sebze", "Tavuklu Yemek", 107, 8.00, 6.60, 4.00),
  ("Beğendi Yatağında Hindi Tandır", "Tavuklu Yemek", 104, 9.00, 5.30, 5.00),
  ("Acı Soslu Tavuk ve Penne Makarna", "Tavuklu Yemek", 181, 10.0, 8.6, 16.00),
  ("Mantar Soslu Tavuk ve Penne Makarna", "Tavuklu Yemek", 160, 9.80, 6.80, 15.00),
  ("Köri Soslu Tavuk ve Penne Makarna", "Tavuklu Yemek", 130, 9.0, 4.2, 14.00),
  ("Beğendi Yatağında Mangalda Tavuk", "Tavuklu Yemek", 110, 7.60, 6.20, 6.00),
  ("Bulgur Pilavı Üstü Mangalda Tavuk", "Tavuklu Yemek", 95, 6.9, 4.3, 7.10),
  ("Mangalda Tavuk ve Pirinç Pilavı", "Tavuklu Yemek", 103, 6.0, 5.4, 7.60),
  ("Izgara Tavuk ve Karışık Sebze", "Tavuklu Yemek", 102, 7.50, 5.80, 5.00),
  ("Duble Izgara Tavuk ve Karışık Sebze", "Tavuklu Yemek", 102, 8.60, 6.0, 3.30),
  ("Bulgur Pilav Üstü Mangalda Duble Tavuk", "Tavuklu Yemek", 122, 9.50, 7.00, 5.20),
  ("Mangalda Duble Tavuk ve Pirinç Pilavı", "Tavuklu Yemek", 143, 9.00, 7.00, 11.00),
  ("Tavuk Sote ve Şehriyeli Pirinç Pilavı", "Tavuklu Yemek", 110, 5.20, 5.5, 10.00),
  ("Tavuk Sote ve Kaşarlı Patates Püresi", "Tavuklu Yemek", 101, 6.00, 5.30, 7.30),
  ("Özel Soslu Tavuk ve Penne", "Tavuklu Yemek", 152, 14.8, 8.5, 4.00),
  ("Özel Soslu Tavuk ve Ispanak", "Tavuklu Yemek", 134, 13.40, 7.10, 4.00),
  ("Baharatlı Tereyağlı Tavuk ve Kaşarlı Patates", "Tavuklu Yemek", 148, 7.00, 7.6, 13.00),
  ("Izgara Tavuk ve Sebze Sote", "Tavuklu Yemek", 119, 6.00, 7.40, 7.00),
  ("Duble Izgara Tavuk ve Sebze Sote", "Tavuklu Yemek", 137, 9.00, 7.0, 9.50),
  ("Mangalda Tavuk ve Köz Domates Soslu Penne", "Tavuklu Yemek", 120, 6.50, 6.40, 9.00),
  # Etli Sebzeli
  ("Etli Yaprak Sarma", "Etli Sebzeli", 166, 4.33, 8.7, 17.77),
  ("Etli Lahana Sarma", "Etli Sebzeli", 130, 7.5, 6.00, 10.00),
  ("Etli Biber Dolma", "Etli Sebzeli", 124, 6.7, 4.40, 14.50),
  ("Fırınlanmış Kabak Dolma", "Etli Sebzeli", 112, 5.00, 4.20, 13.60),
  ("Kıymalı Ispanak", "Etli Sebzeli", 78, 5.00, 5.00, 3.30),
  ("Kıymalı Kapuska", "Etli Sebzeli", 76, 5.00, 4.70, 3.30),
  ("Kıymalı Yeşil Mercimek", "Etli Sebzeli", 59, 3.50, 3.00, 4.52),
  ("Patlıcan Musakka", "Etli Sebzeli", 98, 3.30, 6.80, 6.00),
  ("Fırında Karnıyarık", "Etli Sebzeli", 105, 6.6, 7.00, 4.00),
  ("Patates Oturtma", "Etli Sebzeli", 121, 3.30, 5.80, 14.00),
  # Sebzeli
  ("Bezelye", "Sebzeli Yemek", 94, 6.00, 2.70, 11.40),
  ("Kuru Fasulye", "Sebzeli Yemek", 153, 8.1, 6.7, 15.00),
  ("Tereyağlı İspir Kuru Fasulye", "Sebzeli Yemek", 179, 9.40, 7.70, 18.00),
  ("Ispanak Kavurma", "Sebzeli Yemek", 37, 2.0, 1.9, 2.90),
  ("Nohut", "Sebzeli Yemek", 140, 8.40, 4.80, 15.70),
  ("Türlü", "Sebzeli Yemek", 50, 1.2, 2.8, 5.00),
  ("Buharda Karışık Sebze", "Sebzeli Yemek", 54, 2.10, 2.30, 6.10),
  ("Mercimekli Özbek Mantı", "Sebzeli Yemek", 145, 4.0, 5.00, 21.00),
  ("Ispanaklı Özbek Mantı", "Sebzeli Yemek", 134, 3.0, 5.5, 18.00),
  ("Zerdeçal Soslu Karışık Sebze", "Sebzeli Yemek", 80, 4.30, 4.30, 6.00),
  ("Beğendi Yatağında Sebzeli Falafel", "Sebzeli Yemek", 148, 12.0, 4.0, 16.00),
  ("Siyez Unlu Fırın Mücver", "Sebzeli Yemek", 141, 7.70, 4.0, 18.50),
  # Makarna
  ("Acı Soslu Penne", "Makarna", 129, 2.65, 6.00, 16.00),
  ("Bolonez Soslu Spagetti", "Makarna", 134, 4.5, 6.2, 15.00),
  ("Kremalı Mantarlı Tavuklu Penne", "Makarna", 170, 7.87, 7.00, 19.00),
  ("Domates Soslu Penne", "Makarna", 122, 3.1, 5.00, 16.13),
  # Pilavlar
  ("Bulgur Pilavı", "Pilav", 125, 2.30, 6.00, 15.50),
  ("Nohutlu Pirinç Pilavı", "Pilav", 160, 3.4, 4.5, 26.50),
  ("Şehriyeli Pirinç Pilavı", "Pilav", 153, 2.80, 4.00, 26.45),
  ("Basmati Pirinç Pilavı", "Pilav", 179, 3.7, 4.5, 31.00),
  ("Penne Makarna", "Pilav", 169, 6.10, 3.65, 28.00),
  ("Közlenmiş Domates Soslu Penne", "Makarna", 169, 6.1, 4.0, 27.20),
  ("Arpa Şehriye Pilavı", "Pilav", 149, 4.75, 2.55, 26.70),
  ("Fırında Makarna", "Makarna", 257, 7.7, 11.4, 31.00),
  ("Tereyağlı Erişte", "Makarna", 145, 4.45, 3.00, 25.00),
  # Pilav Ustu
  ("Pilav Üstü Etli Patlıcan Musakka", "Pilav Üstü", 124, 3.10, 5.70, 15.00),
  ("Pilav Üstü Etsiz Patlıcan Musakka", "Pilav Üstü", 112, 2.1, 4.0, 17.00),
  ("Pilav Üstü Nohut", "Pilav Üstü", 133, 3.50, 6.50, 15.00),
  ("Pilav Üstü Kuru Fasulye", "Pilav Üstü", 134, 3.0, 6.8, 15.30),
  # Yan Urunler
  ("Patlıcan Salatası", "Salata", 78, 1.1, 4.9, 7.30),
  ("Kaşarlı Patates Püresi", "Yan Ürün", 111, 1.80, 4.10, 16.81),
  ("Kıymalı Mini İçli Köfte", "Yan Ürün", 313, 12.40, 12.50, 37.70),
  ("Cacık", "Salata", 41, 2.6, 2.0, 3.20),
  ("Mevsim Salata", "Salata", 29, 1.55, 0.66, 4.09),
  ("Maş Fasulyesi Salatası", "Salata", 219, 14.2, 0.8, 38.70),
  ("Elmalı Pancarlı Kinoa Salatası", "Salata", 197, 4.00, 9.00, 25.00),
  ("Mısırlı Sebze Mücver", "Yan Ürün", 105, 4.50, 3.30, 14.40),
  ("Pancarlı Humus", "Yan Ürün", 260, 8.80, 18.00, 15.30),
  ("Karışık Turşu", "Yan Ürün", 16, 0.7, 0.01, 2.92),
  ("Çiğ Köfte", "Yan Ürün", 187, 5.67, 0.90, 39.00),
  ("Peynirli Su Böreği", "Yan Ürün", 184, 6.5, 7.5, 22.50),
  ("Humuslu Mini İçli Köfte", "Yan Ürün", 246, 4.90, 9.70, 34.70),
  ("Ispanaklı Mini İçli Köfte", "Yan Ürün", 241, 4.7, 9.6, 34.00),
  ("Patatesli Mini İçli Köfte", "Yan Ürün", 194, 4.50, 3.60, 36.00),
  # Zeytinyaglılar
  ("Zeytinyağlı Biber Dolması", "Zeytinyağlı", 77, 1.70, 0.20, 17.02),
  ("Zeytinyağlı Brokoli", "Zeytinyağlı", 46, 2.5, 0.7, 7.34),
  ("Zeytinyağlı Yaprak Sarma", "Zeytinyağlı", 181, 3.08, 7.77, 24.90),
  ("Zeytinyağlı Lahana Sarma", "Zeytinyağlı", 170, 2.50, 7.00, 20.00),
  ("Şakşuka", "Zeytinyağlı", 67, 0.86, 5.00, 4.73),
  ("Buharda Sebze", "Zeytinyağlı", 58, 1.0, 3.4, 5.90),
  ("Zeytinyağlı Pırasa", "Zeytinyağlı", 86, 1.1, 5.0, 9.12),
  ("Zeytinyağlı Barbunya", "Zeytinyağlı", 80, 3.8, 2.3, 11.30),
  # Tatlilar
  ("İrmik Helvası", "Tatlı", 201, 3.60, 4.10, 37.30),
  ("Meyve Kompostosu", "Tatlı", 71, 0.4, 0.1, 17.18),
  ("Trakya Peynir Helvası", "Tatlı", 378, 6.92, 14.78, 54.42),
  ("Fırın Sütlaç", "Tatlı", 127, 3.0, 2.6, 22.76),
  ("Kazandibi", "Tatlı", 150, 2.67, 2.44, 29.28),
  ("Portakallı Revani", "Tatlı", 242, 3.00, 6.00, 44.00),
  ("Kemalpaşa Peynir Tatlısı", "Tatlı", 327, 7.2, 15.8, 39.26),
  ("Ekmek Kadayıfı", "Tatlı", 181, 2.92, 2.48, 36.66),
  ("İzmir Bomba", "Tatlı", 492, 6.00, 23.88, 63.18),
  ("Tahinli İzmir Bomba", "Tatlı", 526, 7.00, 34.0, 48.00),
  ("Aşure", "Tatlı", 148, 2.72, 3.81, 25.73),
  ("Kabak Tatlısı", "Tatlı", 185, 1.4, 3.5, 36.94),
  ("Çilekli ve Bisküvili Muhallebi", "Tatlı", 149, 3.20, 7.06, 18.25),
  ("Çikolata Soslu Kaşık Tatlısı", "Tatlı", 220, 4.21, 14.0, 20.37),
  ("Haşhaşlı Limonlu Kek", "Tatlı", 180, 7.2, 2.8, 36.83),
  ("Bol Çikolatalı ve Cevizli Brownie", "Tatlı", 484, 5.0, 28.0, 53.00),
  ("Badelli Kavala Kurabiyesi", "Tatlı", 505, 5.5, 27.0, 60.00),
  ("Hurmalı Bademli Kavala Kurabiyesi", "Tatlı", 126, 8.98, 15.18, 15.00),
  ("Karamelli Balkan Pastası", "Tatlı", 282, 6.2, 13.0, 35.00),
  ("Portakallı Kakao Topları", "Tatlı", 81, 6.46, 3.00, 7.00),
  ("Çikolatalı Vişneli Pasta", "Tatlı", 444, 6.0, 20.00, 60.00),
  ("Bitter Çikolatalı Kakao Topları", "Tatlı", 408, 7.0, 30.8, 57.50),
  # Ek Lezzetler
  ("Yoğurt", "Ek Lezzet", 102, 7.50, 5.80, 5.00),
  ("Sade Ekmek", "Ek Lezzet", 270, 9.3, 2.7, 51.0),
  ("Kepek Ekmek", "Ek Lezzet", 268, 11.0, 3.2, 47.0),
  ("Karabiber", "Ek Lezzet", 327, 10.4, 3.3, 63.95),
  ("Pul Biber", "Ek Lezzet", 430, 12.1, 17.27, 56.63),
]

with app.app_context():
    existing = {f.name.lower() for f in SavedFood.query.with_entities(SavedFood.name).all()}
    added = 0
    skipped = 0
    batch = []
    for name, category, calories, protein, fat, carbs in FOODS:
        if name.lower() in existing:
            skipped += 1
            continue
        existing.add(name.lower())
        batch.append(SavedFood(
            name=name,
            name_tr=name,
            category=category,
            protein=float(protein),
            fat=float(fat),
            carbs=float(carbs),
            calories=float(calories),
            default_serving=100.0,
            serving_unit='g',
            food_type='meal',
            source='tr',
            is_archived=False,
        ))
    db.session.add_all(batch)
    db.session.commit()
    added = len(batch)
    total = SavedFood.query.filter_by(source='tr').count()
    print(f"Added: {added}, Skipped (dups): {skipped}, Total TR foods in DB: {total}")