import pandas as pd
import sys
sys.stdout.reconfigure(encoding='utf-8')
df = pd.read_csv(r'C:\Users\z004mvzt\.cache\kagglehub\datasets\berkebykkpr\yemek-veri-tabani\versions\1\Yemek_Veri_Tabani.csv', encoding='utf-8-sig')
print('Shape:', df.shape)
print('Columns:', df.columns.tolist())
print(df.head(20).to_string())