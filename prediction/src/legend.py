import folium
import numpy as np
import pandas as pd
from shapely.geometry import box, Point
import geopandas as gpd

# 1. Stansiyalar ma'lumotlari
stations = pd.read_excel("src/Stations.xlsx")
# dustforecast = pd.read_excel("/content/DustForecast_10days_per_station.xlsx")

# 2. Toshkent shahar chegarasini yuklash
city_boundary = gpd.read_file("src/karakalpakstan.geojson")

# 3. Grid (maydonchalar) yaratish
lat_min, lat_max = 40, 46
lon_min, lon_max = 55, 67
step = 0.05

lat_bins = np.arange(lat_min, lat_max, step)
lon_bins = np.arange(lon_min, lon_max, step)

grid_cells = []

# 4. IDW interpolyatsiya funksiyasi
def idw_interpolation(x, y, stations, power=2):
    dists = np.sqrt((stations['latitude'] - x)**2 + (stations['longitude'] - y)**2)
    weights = 1 / (dists**power + 1e-10)
    # Ensure 'mean_forecast' column exists in stations DataFrame
    if 'mean_forecast' in stations.columns:
        return np.sum(100 * weights * stations['mean_forecast']) / np.sum(weights)
    else:
        # Handle the case where 'mean_forecast' is not available, maybe return a default or raise an error
        return 0.0 # Or handle as appropriate for your data


# 5. Har bir grid uchun qiymat va shahar ichida bo‘lsa, qo‘shish
for lat in lat_bins:
    for lon in lon_bins:
        lat_center = lat + step / 2
        lon_center = lon + step / 2
        center_point = Point(lon_center, lat_center)

        if city_boundary.contains(center_point).any():
            # Ensure stations DataFrame has necessary columns before calling interpolation
            if all(col in stations.columns for col in ['latitude', 'longitude', 'mean_forecast']):
                 interpolated_value = idw_interpolation(lat_center, lon_center, stations)
            else:
                 interpolated_value = 0.0 # Default if stations data is incomplete

            grid_cells.append({
                'lat': lat,
                'lon': lon,
                'value': interpolated_value,
                'geometry': box(lon, lat, lon + step, lat + step)
            })

# 6. Rang va xavf darajasi funksiyasi
def get_color_and_label(value):
    if value <30:
        return 'green', 'Juda past DSP'
    elif value <50:
        return 'yellow', 'Past DSP'
    elif value <80:
        return 'orange', 'O‘rta DSP'
    else:
        return 'red', 'Yuqori DSP'

# 7. Vizualizatsiya
m = folium.Map(location=[43, 61], zoom_start=7)

# Shahar chegarasini chizish
folium.GeoJson(city_boundary, name="Boundry of Karakalpakstan").add_to(m)

# Grid maydonlarni chizish
for cell in grid_cells:
    color, label = get_color_and_label(cell['value'])

    coords = [[
        [cell['lat'], cell['lon']],
        [cell['lat'], cell['lon'] + step],
        [cell['lat'] + step, cell['lon'] + step],
        [cell['lat'] + step, cell['lon']],
        [cell['lat'], cell['lon']]
    ]]

    folium.Polygon(
        locations=coords,
        color=None,
        fill=True,
        fill_opacity=0.6,
        fill_color=color,
        # tooltip=folium.Tooltip(f"AQI: {round(cell['value'])} — {label}", sticky=True)
        tooltip=folium.Tooltip(f"DSP: {round(cell['value'],2)}", sticky=True)
    ).add_to(m)

# Stansiyalarni marker sifatida chizish
for idx, row in stations.iterrows():
    # Use 'latitude' and 'longitude' from the stations DataFrame
    folium.Marker(
        location=[row['latitude'], row['longitude']],
        popup=f"{row['name']} stansiyadagi DSP: {round(100 * row['mean_forecast'],2)}",
        icon=folium.Icon(color='blue')
    ).add_to(m)


# 8. RANGGA QARAB LEGENDA QO‘SHISH
legend_html = """
<div style="
    position: fixed;
    bottom: 50px;
    left: 50px;
    width: 180px;
    height: 200px;
    background-color: white;
    border:2px solid grey;
    z-index:9999;
    font-size:12px;
    padding: 10px;
    box-shadow: 2px 2px 6px rgba(0,0,0,0.3);
">
<b>Chang bo'ronlarining stansiyalar bo'yicha sodir bo'lish ehtimolligi: 25.12.2023</b><br>
<i style="background:green;width:12px;height:12px;display:inline-block;margin-right:5px;"></i> Juda past ehtimol (<30%)<br>
<i style="background:yellow;width:12px;height:12px;display:inline-block;margin-right:5px;"></i> Past ehtimol (30%–50%)<br>
<i style="background:orange;width:12px;height:12px;display:inline-block;margin-right:5px;"></i> O‘rta ehtimol (50%-80%)<br>
<i style="background:red;width:12px;height:12px;display:inline-block;margin-right:5px;"></i> Yuqori ehtimol (80%>)<br>
</div>
"""

m.get_root().html.add_child(folium.Element(legend_html))
# m.save("Karakalpakstan Dust Forecast.html")
# 9. Xarita
m
m.save("src/Karakalpakstan Dust Forecast.html")