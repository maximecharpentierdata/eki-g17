import pandas as pd
import numpy as np
import os
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from tqdm import tqdm
import haversine

DATA_DIR = "./data_clean/"

pd.options.mode.chained_assignment = None

## Data loading


def load_data(DATA_DIR):
    for csv_file in os.listdir(DATA_DIR):
        if csv_file[-3:] == "csv":
            globals()[csv_file[:-4]] = pd.read_csv(DATA_DIR + csv_file)


## Preparing data for one day and one warehouse


def create_df(date, warehouse, capacity):
    sub_orders = orders[
        (orders["delivered_date"] == date) & (orders["from_warehouse"] == warehouse)
    ]
    groupedby = (
        sub_orders[["delivery_location", "order_total_volume", "order_id", "n_units"]]
        .groupby("delivery_location")
        .agg({"order_total_volume": sum, "n_units": sum, "order_id": list})
        .reset_index()
    )

    # Handling cities with too much orders
    new_groupedby = groupedby[groupedby["order_total_volume"] < capacity]
    over_capacity_cities = groupedby[groupedby["order_total_volume"] >= capacity]
    over_capacity_orders = sub_orders[
        ["delivery_location", "order_total_volume", "order_id", "n_units"]
    ][sub_orders["delivery_location"].isin(over_capacity_cities)]
    over_capacity_orders["order_id"] = over_capacity_orders["order_id"].apply(
        lambda order_id: [order_id]
    )
    groupedby = new_groupedby.append(over_capacity_orders)

    # Handling warehouse
    if warehouse in groupedby.delivery_location.tolist():
        house = groupedby[groupedby["delivery_location"] == warehouse]
        house.order_total_volume = 0
        house.n_units = 0
        house.order_id = None
        groupedby = pd.concat([house, groupedby], axis=0)
    else:
        house = pd.DataFrame(
            dict(
                delivery_location=[warehouse],
                order_total_volume=[0],
                n_units=[0],
                order_id=[None],
            )
        )
        groupedby = pd.concat([house, groupedby], axis=0)

    return pd.merge(
        groupedby,
        cities[["city", "lat", "lng"]],
        left_on="delivery_location",
        right_on="city",
    )


def _distance_calculator(_df):
    _distance_result = np.zeros((len(_df), len(_df)))
    for i in range(len(_df)):
        for j in range(len(_df)):
            # append distance to result list
            _distance_result[i][j] = haversine.haversine(
                (_df.iloc[i]["lat"], _df.iloc[i]["lng"]),
                (_df.iloc[j]["lat"], _df.iloc[j]["lng"]),
            )

    return _distance_result


def create_data(date, warehouse, capacity):
    df = create_df(date, warehouse, capacity)
    distances = _distance_calculator(df)
    data = dict(
        demands=df.order_total_volume,
        distances=distances * 1000,
        depot=0,
        num_vehicles=50,
        vehicle_capacity=capacity,
    )
    return data, df


# Utils function


def save_solution(data, manager, routing, solution):
    """."""
    vehicules = []
    for vehicle_id in range(data["num_vehicles"]):
        index = routing.Start(vehicle_id)
        route_distance = 0
        route_load = 0
        stops_vehicle = list()
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            stops_vehicle.append(node_index)
            route_load += data["demands"][node_index]
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route_distance += routing.GetArcCostForVehicle(
                previous_index, index, vehicle_id
            )
        vehicules.append(
            dict(
                route_distance=route_distance / 1000,
                stops_vehicle=stops_vehicle,
                route_load=route_load,
            )
        )
    return vehicules


def make_routes(output, df, date, warehouse):
    routes_list = []
    for route in output:
        if route["route_load"] > 0:
            route_row = dict()
            route_row["truck_id"] = None
            route_row["duration"] = None
            route_row["fill_volume"] = route["route_load"]
            route_row["n_units"] = np.sum(
                [df["n_units"][k] for k in route["stops_vehicle"]]
            )
            orders_list = [
                " > ".join(df["order_id"][k])
                for k in route["stops_vehicle"]
                if df["order_id"][k]
            ]
            route_row["orders"] = " > ".join(
                [order for order in orders_list if order != ""]
            )
            route_row["from_warehouse"] = warehouse
            route_row["route_date"] = date[:10]
            route_row["stops"] = " > ".join(
                [df["city"][k] for k in route["stops_vehicle"]]
            )
            route_row["total_distance"] = route["route_distance"]
            routes_list.append(route_row)
    return pd.DataFrame.from_records(routes_list)


# Solving function


def solve(data):
    """Solve the CVRP problem."""
    # Create the routing index manager.
    manager = pywrapcp.RoutingIndexManager(
        len(data["distances"]), data["num_vehicles"], data["depot"]
    )

    # Create Routing Model.
    routing = pywrapcp.RoutingModel(manager)

    # Create and register a transit callback.
    def distance_callback(from_index, to_index):
        """Returns the distance between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data["distances"][from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)

    # Define cost of each arc.
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Add Capacity constraint.
    def demand_callback(from_index):
        """Returns the demand of the node."""
        # Convert from routing variable Index to demands NodeIndex.
        from_node = manager.IndexToNode(from_index)
        return data["demands"][from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimension(
        demand_callback_index,
        0,  # null capacity slack
        data["vehicle_capacity"],  # vehicle maximum capacities
        True,  # start cumul to zero
        "Capacity",
    )

    # Setting first solution heuristic.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.FromSeconds(1)

    # Solve the problem.
    solution = routing.SolveWithParameters(search_parameters)

    # Print solution on console.
    if solution:
        output = save_solution(data, manager, routing, solution)
        return output


# Run function


def run(date, warehouse, capacity):
    data, df = create_data(date, warehouse, capacity)
    output = solve(data)
    if output:
        new_routes = make_routes(output, df, date, warehouse)
        if "fill_volume" in new_routes:
            if new_routes.fill_volume.max() > 81.25:
                return run(date, warehouse, capacity - 2)
            else:
                return new_routes


def main():
    new_routes = pd.DataFrame()
    errors = []
    for date in tqdm(orders.delivered_date.unique().tolist()):
        for warehouse in orders.from_warehouse.unique().tolist():
            output = run(date, warehouse, 80)
            if output is not None:
                new_routes = new_routes.append(output)
            else:
                print("Erreur!")
                errors.append((date, warehouse))

    new_routes.to_csv("./new_routes.csv")
    print("End!")


if __name__ == "__main__":
    load_data(DATA_DIR)
    main()
