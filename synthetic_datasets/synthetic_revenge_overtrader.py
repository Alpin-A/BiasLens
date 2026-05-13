import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

# Configuration
num_rows = 300
start_balance = 25000.00  # Started with a bit more to survive the churn
start_time = datetime(2025, 3, 15, 9, 30)

# Tickers (Includes volatile "meme" stocks typical of overtraders)
assets = {
    'AMZN': 210.00,
    'TSLA': 410.00,
    'NVDA': 145.00,
    'COIN': 280.00,
    'GME': 45.00,
    'AMD': 180.00,
    'PLTR': 35.00
}

data = []
current_balance = start_balance
current_time = start_time
consecutive_losses = 0

for i in range(num_rows):
    # Select Asset
    asset = random.choice(list(assets.keys()))
    base_price = assets[asset]
    
    # Add noise to entry price
    entry_price = base_price * (1 + np.random.normal(0, 0.03))
    
    # LOGIC: Overtrader + Revenge
    # If previous trade was a loss, they trade BIGGER and FASTER (Revenge)
    # If previous trade was a win, they still trade FAST (Overconfidence/Overtrading)
    
    if consecutive_losses > 0:
        # REVENGE MODE
        # Size up significantly (Martingale attempt)
        risk_multiplier = 1.5 + (consecutive_losses * 0.5) # Escalating risk
        quantity_budget = current_balance * 0.25 * risk_multiplier
        quantity = int(max(1, quantity_budget / entry_price))
        
        # Revenge trades are emotional -> lower probability of success
        is_win = random.random() > 0.60 # 60% chance to lose again
        time_gap = random.randint(1, 5) # Immediate re-entry (1-5 mins)
        
    else:
        # OVERTRADING MODE
        # Standard size, but high frequency
        quantity_budget = current_balance * 0.10
        quantity = int(max(1, quantity_budget / entry_price))
        
        # Overtrading = taking low quality setups (50/50 or worse due to spread)
        is_win = random.random() > 0.52 
        time_gap = random.randint(2, 15) # Very short gaps, constant action

    # Calculate Exit Price based on Win/Loss
    volatility = random.uniform(0.005, 0.02) # Scalping volatility
    
    if is_win:
        exit_price = entry_price * (1 + volatility)
        consecutive_losses = 0 # Reset streak
    else:
        exit_price = entry_price * (1 - volatility)
        consecutive_losses += 1 # Add to streak
        
        # Cap consecutive losses logic to prevent infinite blowup in simulation
        if consecutive_losses > 4: consecutive_losses = 0

    # Rounding to match format
    entry_price = round(entry_price, 3)
    exit_price = round(exit_price, 3)
    
    profit_loss = (exit_price - entry_price) * quantity
    profit_loss = round(profit_loss, 3)
    
    current_balance += profit_loss
    current_balance = round(current_balance, 2)
    
    # Update Time
    duration = timedelta(minutes=random.randint(1, 10)) # Fast scalp trades
    rest = timedelta(minutes=time_gap)
    
    row = {
        "timestamp": current_time.strftime("%Y-%m-%d %H:%M"),
        "asset": asset,
        "side": "BUY", # Overtraders often have a long-bias
        "quantity": quantity,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "profit_loss": profit_loss,
        "balance": current_balance
    }
    data.append(row)
    
    # Increment time
    current_time += duration + rest
    
    # Market Hours Logic (9:30 - 16:00)
    if current_time.hour >= 16:
        current_time += timedelta(days=1)
        current_time = current_time.replace(hour=9, minute=30)
        consecutive_losses = 0 # Sleep resets the emotion slightly

# Create DataFrame
df_revenge = pd.DataFrame(data)

# Save to CSV
csv_path_revenge = 'synthetic_revenge_overtrader_data.csv'
df_revenge.to_csv(csv_path_revenge, index=False)

csv_path_revenge