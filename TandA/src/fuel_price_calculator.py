import sys
from pathlib import Path
import functools as ft
import data_managers as dm 
import pandas as pd

sys.path.append(Path().absolute().parent.as_posix())
from fuel_EU import process_fuel, FuelManager

LNG_FUEL = 'Fossil LNG 4 stroke'


if __name__ == '__main__':
    gen_target = zip((89.3, 85.7, 77.9, 62.9, 34.6, 18.2), range(2025, 2051, 5))
    target_dict = {k:v for (v,k) in gen_target}


    data_path = Path()
    data_path = data_path.absolute() / "data" / "processed_data"

    csv_loader = dm.CSVDataLoader()
    ef_fuels_df = csv_loader.load_data(data_path / 'fuels_ef').set_index('Fuel')
    ets_df = csv_loader.load_data(data_path / 'ets_prices',).set_index("period").T
    lcv_df = csv_loader.load_data(data_path / 'lcv_fuels').set_index('Fuel')
    price_ef_df = csv_loader.load_data(data_path / 'fuels_price').set_index('Fuel')

    process_fuel_partial = ft.partial(process_fuel, ef_fuels_df, price_ef_df, lcv_df)
    comparisons = ['VLSFO', 'Fossil LNG 4 stroke', 'Fossil LNG LP 2 stroke', 'e-LNG LP 2 stroke', 'e-NH3', 'e-Methanol']
    fuel_kwargs = {kwargs.name: kwargs for kwargs in process_fuel_partial(comparisons)}
    fuel_kwargs['fossil lng'] = fuel_kwargs[LNG_FUEL]
    fuel_kwargs.pop(LNG_FUEL)
    fuel_kwargs['fossil lng'].name = 'fossil lng'

    df = pd.read_excel(data_path / 'joules_used.xlsx', index_col=0)

    penalty = 2400
    targets = list(target_dict.values())

    fm = FuelManager()

    ships =  df.index.unique()

    output_path = Path().absolute()
    output_path = output_path / 'data' / 'comparisons'
    output_path.mkdir(parents=True, exist_ok=True)

    for f in output_path.iterdir():
        f.unlink(missing_ok=True)

    for ship in ships: 

        total_fuel = df.at[ship, 'GJ_used']

        if ship in (9781891, 9837420, 9781865, 9826548):
            
            args = [('fossil lng', 'e-NH3'), ('fossil lng', 'e-LNG LP 2 stroke')]
            for (f1, f2) in args:
                filename = f'results_{ship}_{f1}_{f2}.json'
                fm.compare(total_fuel, fuel_kwargs[f1], fuel_kwargs[f2], targets, penalty).save_result(output_path / filename)

        else:
            
            args = [('VLSFO', 'e-NH3'), ('VLSFO', 'e-Methanol')]
            for (f1, f2) in args:
                filename = f'results_{ship}_{f1}_{f2}.json'
                fm.compare(total_fuel, fuel_kwargs[f1], fuel_kwargs[f2], targets, penalty).save_result(output_path / filename)

