import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

file_path = 'data/processed/master_dataset.csv'
if os.path.exists(file_path):
    df = pd.read_csv(file_path)
else:
    df = pd.DataFrame()

crops = ['Onion', 'Tomato', 'Wheat']
dates = [datetime.today() - timedelta(days=x) for x in range(500)]
dates.reverse()

np.random.seed(42)
all_new_data = []

for crop in crops:
    base_price = np.random.randint(1000, 3000)
    prices = []
    for i in range(500):
        base_price += np.random.normal(0, 50)
        seasonal = np.sin(i / 365.0 * 2 * np.pi) * 300
        prices.append(max(500, base_price + seasonal))
    
    new_data = pd.DataFrame({
        'state': 'Madhya Pradesh',
        'district': 'Indore',
        'mandi': 'Indore',
        'crop': crop,
        'variety': 'Local',
        'grade': 'FAQ',
        'date': [d.strftime('%Y-%m-%d') for d in dates],
        'min_price': [p * 0.9 for p in prices],
        'max_price': [p * 1.1 for p in prices],
        'modal_price': prices,
        'arrivals_qtl': np.random.randint(50, 500, size=500)
    })
    all_new_data.append(new_data)

df = pd.concat([df] + all_new_data, ignore_index=True)
df.to_csv(file_path, index=False)
print("Added historical data for multiple crops at Indore!")
