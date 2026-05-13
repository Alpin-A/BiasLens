import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

# Configuration
num_rows = 300
start_balance = 11604.25
start_time = datetime(2025, 3, 9, 9, 45)

# Tickers and approx base prices for 2025 simulation
assets = {
    'AMZN': 210.00,
    'AAPL': 260.00,
    'TSLA': 410.00,
    'NVDA': 145.00,
    'MSFT': 430.00,
    'META': 580.00,
    'GOOGL': 190.00,
    'NFLX': 650.00
}

data = []
current_balance = start_balance
current_time = start_time
state = "NORMAL" # NORMAL, REVENGE

for i in range(num_rows):
    # Select Asset
    asset = random.choice(list(assets.keys()))
    base_price = assets[asset]
    
    # Add some market noise to the price
    entry_price = base_price * (1 + np.random.normal(0, 0.02))
    
    # Logic based on State
    if state == "NORMAL":
        # Normal behavior: Conservative sizing, looking for small wins
        # 5% chance of falling into "Holding Loser" trap
        
        quantity = int(max(1, (current_balance * 0.10) / entry_price)) # 10% of portfolio
        
        is_holding_loser = random.random() < 0.08
        
        if is_holding_loser:
            # Holding Loser: Big Drop, Long Hold (simulated by time jump), Big Loss
            exit_price = entry_price * (1 - random.uniform(0.05, 0.15)) # 5-15% loss
            time_gap = random.randint(30, 240) # Held for 30 mins to 4 hours
            state = "REVENGE" # Trigger revenge mode for next trade
        else:
            # Normal Scalp: Small win or very small loss
            change = random.normalvariate(0.005, 0.01) # Bias slightly positive
            exit_price = entry_price * (1 + change)
            time_gap = random.randint(5, 60) # Normal trade duration
            
    elif state == "REVENGE":
        # Revenge behavior: Aggressive sizing, impulsive entry
        
        # Position size increases to 30-50% of balance (or leverage if we allowed it, limited here to cash)
        quantity = int(max(1, (current_balance * 0.40) / entry_price))
        
        # High volatility outcome
        outcome = random.random()
        if outcome < 0.60: 
            # 60% chance they lose again (emotional trading)
            exit_price = entry_price * (1 - random.uniform(0.02, 0.08))
            state = "REVENGE" # Still angry, might continue
            # If balance gets too low, force reset to normal to avoid bankruptcy in simulation
            if current_balance < 2000: state = "NORMAL"
        else:
            # 40% chance they get lucky
            exit_price = entry_price * (1 + random.uniform(0.02, 0.08))
            state = "NORMAL" # Cooled down by a win
            
        time_gap = random.randint(1, 5) # Immediate re-entry (1-5 mins later)

    # Calculate P&L
    # Assuming 'side' is always BUY for simplicity based on image, but logic holds.
    # We round prices to 3 decimals to match the image style
    entry_price = round(entry_price, 3)
    exit_price = round(exit_price, 3)
    
    profit_loss = (exit_price - entry_price) * quantity
    profit_loss = round(profit_loss, 3)
    
    current_balance += profit_loss
    current_balance = round(current_balance, 2)
    
    # Update Time
    # current_time is the Entry Time. The next row's entry time is:
    # Current Entry + Duration of trade + Rest period
    duration = timedelta(minutes=time_gap)
    rest = timedelta(minutes=random.randint(1, 10)) if state == "NORMAL" else timedelta(seconds=30)
    
    # Append row
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
    
    # Increment time for next loop
    current_time += duration + rest
    
    # Jump to next day if late
    if current_time.hour >= 16:
        current_time += timedelta(days=1)
        current_time = current_time.replace(hour=9, minute=30)

# Create DataFrame
df = pd.DataFrame(data)

# Save to CSV
csv_path = 'synthetic_loss_averse_revenge_trader_data.csv'
df.to_csv(csv_path, index=False)

csv_path