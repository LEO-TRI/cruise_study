import sys
from pathlib import Path
import functools as ft
import pandas as pd

sys.path.append(Path(__file__).absolute().parent.as_posix())
from fuel_EU import process_fuel, FuelManager

#Which LNG to use
LNG_FUEL = 'Fossil LNG 4 stroke W MDO'

if __name__ == '__main__':

    gen_target = zip((89.3, 85.7, 77.9, 62.9, 34.6, 18.2), range(2025, 2051, 5))
    target_dict = {k:v for (v,k) in gen_target}

    data_path = Path(__file__).absolute().parents[1] / "data" / "processed_data" / 'FEUM_IA'

    ef_fuels_df = pd.read_csv(data_path / 'fuels_ef.csv').set_index('Fuel')
    lcv_df = pd.read_csv(data_path / 'lcv_fuels.csv').set_index('Fuel')
    price_ef_df = pd.read_csv(data_path / 'fuels_price.csv').set_index('Fuel')

    #Prefills the required tables
    process_fuel_partial = ft.partial(process_fuel, ef_fuels_df, price_ef_df, lcv_df)
    comparisons = ['VLSFO', 'Fossil LNG 4 stroke', 'Fossil LNG LP 2 stroke', 'e-LNG LP 2 stroke', 'e-NH3', 'e-Methanol', 'Fossil LNG 4 stroke W MDO', 'Bio-LNG']

    FUEL_MIX = 0.01
    price_ef_df.loc['Fossil LNG 4 stroke W MDO'] = price_ef_df.loc['Fossil LNG 4 stroke']*(1-FUEL_MIX) + price_ef_df.loc['VLSFO']*FUEL_MIX

    #Extract for each fuel the required parameters -> lCV, ef, prices 
    fuel_kwargs = {kwargs.name:kwargs for kwargs in process_fuel_partial(comparisons)}
    fuel_kwargs['fossil lng'] = fuel_kwargs[LNG_FUEL] #We designate LNG 4 strokes as the default LNG fuel, and pop it afterwards
    fuel_kwargs.pop(LNG_FUEL)
    fuel_kwargs['fossil lng'].name = 'fossil lng'

    df = pd.read_excel(data_path.parent/'joules_used.xlsx', index_col=0)

    penalty = 2400
    targets = list(target_dict.values())

    fm = FuelManager()


    output_path = data_path.parents[1] / 'comparisons'
    output_path.mkdir(parents=True, exist_ok=True)

    #Remove the previously exisitn files
    for f in output_path.glob('*.json'):
        f.unlink(missing_ok=True)

    ships =  df.index.unique()
    for ship in ships: 

        #Get the energy used for the trip
        total_fuel = df.at[ship, 'GJ_used']

        #For the LNG ships
        if ship in {9781891, 9837420, 9781865, 9826548}:
            
            args = (('fossil lng','fossil lng'), ('fossil lng','Bio-LNG'), ('fossil lng','e-LNG LP 2 stroke'), ('e-LNG LP 2 stroke','e-LNG LP 2 stroke'), ('Bio-LNG','Bio-LNG'))
            for (f1, f2) in args:
                filename = f'results_{ship}_{f1}_{f2}.json'
                res = fm.compare(total_fuel, fuel_kwargs[f1], fuel_kwargs[f2], targets, penalty)
                res.save_result(output_path / filename)

        #For the VLSFO ships
        else:
            
            args = (('VLSFO','e-Methanol'), ('VLSFO', 'VLSFO'), ('e-NH3', 'e-NH3'), ('e-Methanol', 'e-Methanol'))
            for (f1, f2) in args:
                filename = f'results_{ship}_{f1}_{f2}.json'
                res = fm.compare(total_fuel, fuel_kwargs[f1], fuel_kwargs[f2], targets, penalty)
                res.save_result(output_path / filename)

