import numpy as np

def calculate_price_pax(fuel_price: np.ndarray, n_passengers: int) -> np.ndarray[float]:
    return fuel_price / n_passengers

def calculate_price_per_ticker(price_fuel_pax: np.ndarray, fare: float) -> np.ndarray[float]:
    return price_fuel_pax / fare
