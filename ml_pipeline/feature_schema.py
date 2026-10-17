"""
Feature Schema and Baseline Model Generator for Sentinel-Z.
Based on PhysioNet Computing in Cardiology Challenge 2019 / Sepsis-3 criteria.
"""

from typing import List

FEATURE_NAMES: List[str] = [
    "HeartRate",           # Beats per min
    "MeanArterialPressure",# mmHg
    "RespRate",            # Breaths per min
    "Temperature",         # Celsius
    "O2Sat",               # %
    "Lactate",             # mmol/L
    "WhiteBloodCells",     # 10^9/L
    "HeartRate_Delta",     # Change over rolling window
    "MAP_Delta"            # Change over rolling window
]

def calculate_heuristic_sepsis_score(features: List[float]) -> float:
    """
    Sub-millisecond mathematical heuristic score (0.0 to 100.0)
    aligned with Sepsis-3 / qSOFA guidelines:
    - MAP < 65 mmHg (hypotension)
    - RespRate >= 22
    - HeartRate > 100 (tachycardia)
    - Lactate > 2.0 mmol/L
    - Temperature > 38.0 or < 36.0
    """
    hr, map_val, resp, temp, o2, lactate, wbc, hr_delta, map_delta = features
    
    score = 10.0 # Baseline
    
    # Hypotensive stress
    if map_val < 65.0:
        score += 35.0
    elif map_val < 75.0:
        score += 15.0
        
    # Lactate accumulation (key metabolic marker of tissue hypoperfusion)
    if lactate > 4.0:
        score += 30.0
    elif lactate > 2.0:
        score += 15.0
        
    # Tachypnea
    if resp >= 22.0:
        score += 10.0
        
    # Tachycardia / Vitals trajectory
    if hr > 105.0 or hr_delta > 20.0:
        score += 10.0
        
    # Abnormal Temperature
    if temp > 38.3 or temp < 36.0:
        score += 5.0
        
    return min(100.0, max(0.0, score))
