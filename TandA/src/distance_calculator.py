import math

def compute_a(lat_a, lat_b, lon_a, lon_b):

    diff_lat = lat_b - lat_a
    diff_lon = lon_b - lon_a

    lat_b = math.radians(lat_b)
    lat_a = math.radians(lat_a)
    diff_lat = math.radians(diff_lat)
    diff_lon = math.radians(diff_lon)

    return math.sin(diff_lat/2)**2 + (math.cos(lat_b) * math.cos(lat_a) * math.sin(diff_lon/2)**2)

def compute_c(a):
    return 2 * math.atan2(a**0.5, (1-a)**0.5)

def compute_haversine(lon_a, lat_a, lon_b, lat_b):
    
    a = compute_a(lat_a, lat_b, lon_a, lon_b)
    c = compute_c(a)
    R = 6371

    return c * R
