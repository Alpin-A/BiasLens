import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

# Configuration
num_rows = 300
start_balance = 20000.00
start_time = datetime(2025, 4, 1, 9, 30)
daily_loss_limit = -1500.00

# Tickers
# Revenge phase favors high volatility. Calm phase favors liquidity.
assets_volatile = {'TSLA': 415.00, 'NVDA': 148.00, 'AMD': 175.00, 'COIN': 270.00}
assets_stable = {'AAPL': 265.00, 'MSFT': 435.00, 'GOOGL': 195.00, 'AMZN': 215.00}

data = []
current_balance = start_balance
current_time = start_time
daily_pnl = 0.0
mode = "REVENGE" # Start in chaos
mode_switch_day = None # Track when the change happened

for i in range(num_rows):
    
    # 1. Check if it's a new day to reset daily PnL
    if len(data) > 0:
        last_time = datetime.strptime(data[-1]['timestamp'], "%Y-%m-%d %H:%M")
        if current_time.date() > last_time.date():
            daily_pnl = 0.0
            # If we were in REVENGE mode and hit the limit yesterday, 
            # we are now CALM because we were forced to take a break.
            if mode == "REVENGE" and mode_switch_day:
                mode = "CALM"

    # 2. Select Asset & Strategy based on Mode
    if mode == "REVENGE":
        # Strategy: Aggressive, Upsizing after loss
        asset_dict = assets_volatile
        asset = random.choice(list(asset_dict.keys()))
        base_price = asset_dict[asset]
        
        # Position Sizing: Dangerous (20-40% of account)
        quantity = int((current_balance * random.uniform(0.2, 0.4)) / base_price)
        
        # Behavior: Erratic, chasing
        entry_price = base_price * (1 + np.random.normal(0, 0.005))
        
        # Outcome: Lower probability due to emotion
        if random.random() < 0.60: # High chance of loss
            change = -random.uniform(0.01, 0.04) # Big hits
        else:
            change = random.uniform(0.01, 0.03)
            
        time_gap = random.randint(1, 10) # Overtrading frequency
        
    else: # Mode == "CALM"
        # Strategy: Disciplined, Fixed Risk
        asset_dict = assets_stable
        asset = random.choice(list(asset_dict.keys()))
        base_price = asset_dict[asset]
        
        # Position Sizing: Conservative (Fixed ~5% of account or risk based)
        quantity = int((current_balance * 0.05) / base_price)
        
        # Behavior: Waiting for setup
        entry_price = base_price * (1 + np.random.normal(0, 0.002))
        
        # Outcome: Better win rate, tighter stops
        if random.random() < 0.55: # Slight edge
            change = random.uniform(0.005, 0.015) # Target hit
        else:
            change = -random.uniform(0.002, 0.008) # Stop loss respected
            
        time_gap = random.randint(45, 180) # Patience (hours between trades)

    # 3. Calculate Trade
    entry_price = round(entry_price, 3)
    exit_price = entry_price * (1 + change)
    exit_price = round(exit_price, 3)
    
    profit_loss = (exit_price - entry_price) * quantity
    profit_loss = round(profit_loss, 3)
    
    # 4. Check Daily Loss Limit (The Trigger)
    # If this trade puts us over the limit, we stop for the day.
    if mode == "REVENGE" and (daily_pnl + profit_loss) < daily_loss_limit:
        # We hit the wall.
        mode_switch_day = current_time.date()
        
        # Force the loss to happen
        current_balance += profit_loss
        current_balance = round(current_balance, 2)
        
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
        
        # INTERVENTION: Forced break until next day
        current_time += timedelta(days=1)
        current_time = current_time.replace(hour=9, minute=30)
        daily_pnl = 0 # Reset for new day
        continue # Skip to next loop iteration
        
    # Standard update
    current_balance += profit_loss
    current_balance = round(current_balance, 2)
    daily_pnl += profit_loss
    
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
    
    # Time Increment
    current_time += timedelta(minutes=time_gap)
    
    # Market Close Logic
    if current_time.hour >= 16:
        current_time += timedelta(days=1)
        current_time = current_time.replace(hour=9, minute=30)
        daily_pnl = 0

# Create DataFrame
df_calm = pd.DataFrame(data)
csv_path_calm = 'synthetic_revenge_to_calm.csv'
df_calm.to_csv(csv_path_calm, index=False)