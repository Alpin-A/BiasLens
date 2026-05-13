import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

# Configuration
num_rows = 300
start_balance = 15000.00
start_time = datetime(2025, 3, 20, 9, 30)

# Tickers (Safe, low-beta or blue chip mostly)
assets = {
    'AMZN': 212.00,
    'AAPL': 262.00,
    'MSFT': 432.00,
    'GOOGL': 192.00,
    'JPM': 180.00,
    'KO': 65.00
}

data = []
current_balance = start_balance
current_time = start_time

for i in range(num_rows):
    # Select Asset
    asset = random.choice(list(assets.keys()))
    base_price = assets[asset]
    
    # Add noise
    entry_price = base_price * (1 + np.random.normal(0, 0.01))
    
    # LOGIC: Loss Averse + Overtrader
    # 1. Sizes too small (Fear of big loss)
    # They use ~2-3% of portfolio per trade, which is tiny for a day trader
    quantity = int(max(1, (current_balance * 0.03) / entry_price))
    
    # 2. Market Outcome
    # They are nervous. They scalp tiny profits and cut losses immediately.
    # This results in a high "win rate" but very low Reward:Risk ratio.
    
    outcome_roll = random.random()
    
    if outcome_roll < 0.55:
        # SCALP WIN (Taking profit too early)
        # They see +0.3% and bail immediately to lock it in
        exit_price = entry_price * (1 + random.uniform(0.002, 0.005))
        
    elif outcome_roll < 0.85:
        # NERVOUS SCRATCH (Breakeven ish)
        # Trade goes nowhere, they get bored/scared and exit
        exit_price = entry_price * (1 + random.uniform(-0.001, 0.001))
        
    else:
        # MICRO LOSS (cutting it fast)
        # Trade drops -0.4%, they panic and sell.
        exit_price = entry_price * (1 - random.uniform(0.002, 0.006))

    # Rounding
    entry_price = round(entry_price, 3)
    exit_price = round(exit_price, 3)
    
    profit_loss = (exit_price - entry_price) * quantity
    profit_loss = round(profit_loss, 3)
    
    current_balance += profit_loss
    current_balance = round(current_balance, 2)
    
    # 3. Time Logic (Overtrading)
    # They can't sit on their hands. As soon as they exit, they find another "setup".
    time_gap = random.randint(2, 8) # Trades every few minutes
    duration = random.randint(1, 5) # Holds for very short time
    
    row = {
        "timestamp": current_time.strftime("%Y-%m-%d %H:%M"),
        "asset": asset,
        "side": "BUY",
        "quantity": quantity,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "profit_loss": profit_loss,
        "balance": current_balance
    }
    data.append(row)
    
    # Increment time
    current_time += timedelta(minutes=time_gap + duration)
    
    # Market Hours Logic
    if current_time.hour >= 16:
        current_time += timedelta(days=1)
        current_time = current_time.replace(hour=9, minute=30)

# Create DataFrame
df_loss_averse = pd.DataFrame(data)

# Save to CSV
csv_path_loss_averse = 'synthetic_loss_averse_overtrader.csv'
df_loss_averse.to_csv(csv_path_loss_averse, index=False)

csv_path_loss_averse