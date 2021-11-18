import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import pandas as pd
import geopandas as gpd
import contextily as cx
import os
import seaborn as sns
import shapely as shp
import streamlit as st

for csv_file in os.listdir("./data_clean"):
    if csv_file[-3:] == "csv":
        globals()[csv_file[:-4]] = pd.read_csv("./data_clean/" + csv_file)


st.title('Exploration de la stratégie')


def check_and_see(warehouse, date):
    sub_orders = orders[(orders["delivered_date"]==date) & (orders["from_warehouse"]==warehouse)]
    st.write(f"**{len(sub_orders)} commandes** le jour {date[:10]}")

    sub_routes = routes[routes["orders"].apply(contain, words=sub_orders["order_id"])]
    st.write(f"**{len(sub_routes)} routes** le jour {date[:10]}")
    
    sub_routes.loc[:,"path"] = sub_routes["stops"].apply(create_path)

    sub_routes.loc[:, "fill_rate"] = sub_routes.loc[:, "fill_volume"] / 81.25

    st.write(f"Taux de remplissage moyen sur tous les trajets : **{sub_routes.loc[:, 'fill_rate'].mean()*100:.0f}%**")

    for k in range(len(sub_routes)):
        st.subheader(f"Route {k + 1}")
        s_df = sub_routes.iloc[[k]]
        st.write(f"Taux de remplissage : **{s_df.iloc[0].fill_rate*100:.0f}%**")
        st.write(f"Villes desservies : **{s_df.iloc[0].stops}**")
        fig, ax = plt.subplots(figsize=(15, 15))

        sub_cities = pd.merge(sub_orders[["delivery_location", "order_total_volume"]].groupby("delivery_location").agg(sum).reset_index(),
                            cities, left_on="delivery_location", right_on="city")

        gdf_cities = gpd.GeoDataFrame(sub_cities, geometry=gpd.points_from_xy(sub_cities.lng, sub_cities.lat), crs=4326)
        gdf_cities.to_crs(epsg=3857).plot(ax=ax, column="order_total_volume", markersize=200)#, legend=True)

        gdf = gpd.GeoDataFrame(s_df, geometry=s_df.path, crs=4326)
        gdf.to_crs(epsg=3857).plot(ax=ax, column="n_units")

        cx.add_basemap(ax, source=cx.providers.CartoDB.Voyager, zoom=7)
        ax.axis('off')
        ax.set_title("Localisation des villes")
        st.pyplot(fig)

warehouse = st.selectbox("Choisir un entrepôt", options=warehouses.warehouse_city.tolist())
date = st.selectbox("Choisir une date de livraison", options=orders.delivered_date.unique().tolist())


def create_path(stops):
    stops = stops.split(" > ")
    coordinates = []
    for stop in stops:
        city = cities[cities["city"] == stop].iloc[0]
        coordinates.append([city["lng"], city["lat"]])
    if len(coordinates) == 1:
        coordinates = 2*coordinates
    return shp.geometry.LineString(coordinates)


def contain(orders, words):
    for word in words:
        if word in orders:
            return True
    else:
        return False


check_and_see(warehouse, date)