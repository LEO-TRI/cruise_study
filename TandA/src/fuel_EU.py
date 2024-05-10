from abc import ABC, abstractmethod
from numbers import Number
import itertools as it
import functools as ft
import pandas as pd
from dataclasses import dataclass
from utils import array_like, dataclass_converter
from typing import Callable, TypeVar

V = TypeVar('V')
R = TypeVar('R')


@dataclass
class Fuel:

    name: str
    price: list[Number]
    lcv: list[Number]
    wtw_ef: Number | list[Number]


@dataclass
class Comparison:

    name: str
    penalty_strat: list[float]
    mix_strat: list[float]
    optimal_mix: list[float]
    verdict: list[str]

    def __post_init__(self):

        def func(x): return round(x,3) if isinstance(x, Number) else x

        for (attr_name, attr_value) in vars(self).items():
            if isinstance(attr_value, list):
                new_attr_value = list(map(func, attr_value))
                setattr(self, attr_name, new_attr_value)

    def to_dataframe(self) -> pd.DataFrame:

        data = {k:v for (k,v) in vars(self).items() if isinstance(v, array_like)}
        cols = ['penaltyCost', 'mixCost', 'optimalMix', 'verdict']
        return pd.DataFrame(data=data,) #columns=cols


class FuelBaseClass(ABC): 

    @abstractmethod
    def compute(self):
        pass

    def inplace_checker(self, arg: object, name: str) -> object:
        
        if arg is None: 
            arg = vars(self)[name]
            if arg is None: 
                msg = f'You must pass argument {name} or run compare before with inplace=True'
                raise ValueError(msg)
                
        return arg
    
class FuelPenaltyOptimiser(FuelBaseClass):

    def __init__(self) -> None:
        
        self.penalty_cost = None

    def compute(self, 
                target_intensity: float, 
                wtw_co2_mj: float, 
                lcv: float, 
                penalty: int, 
                inplace: bool=False
                ) -> 'float | FuelPenaltyOptimiser':

        #Edge case if someone tries to calculate green electricity
        if wtw_co2_mj==0:        
            raise ValueError('wtw_co2_mj must be different from 0') 

        overshoot = max(0., wtw_co2_mj - target_intensity) 

        self.penalty_cost = (overshoot*penalty) / (wtw_co2_mj*lcv)  

        return self if inplace else self.penalty_cost

    def compute_cost(self, 
                     total_fuel: float, 
                     price: float, 
                     penalty_cost: float=None
                     ) -> float:
        
        penalty_cost = self.inplace_checker(penalty_cost, 'penalty_cost')

        return total_fuel * (price + penalty_cost)

class FuelMixOptimiser(FuelBaseClass):

    def __init__(self) -> None:
        
        self.proportion_junior_fuel = None

    def compute(self,
                target_intensity: float, 
                wtw_co2_mj_fuel_senior: float, 
                wtw_co2_mj_fuel_junior: float,
                inplace: bool=False
                ) -> 'float | FuelMixOptimiser':
        
        fuels_ratio = (wtw_co2_mj_fuel_junior-wtw_co2_mj_fuel_senior)
        target_ratio = (target_intensity-wtw_co2_mj_fuel_senior)

        #If fuel_ratio>=0, then there is no benefit in mixing the fuels
        check = fuels_ratio < 0
        self.proportion_junior_fuel = max(target_ratio/fuels_ratio, 0.) if check else 0.

        return self if inplace else self.proportion_junior_fuel
    
    def compute_cost(self,
                     total_fuel: float, 
                     senior_fuel_price: float,  
                     junior_fuel_price: float,
                     junior_fuel_prop: float | None = None, 
                    ) -> float:
        
        junior_fuel_prop = self.inplace_checker(junior_fuel_prop, 'junior_fuel_prop')
        senior_fuel_prop = (1-junior_fuel_prop)

        return ((senior_fuel_prop*senior_fuel_price) + (junior_fuel_prop*junior_fuel_price)) * total_fuel


class FuelManager():

    def __init__(self, year_range: None | list[str]=None) -> None:
        
        self.penalty_calc = FuelPenaltyOptimiser()
        self.mix_calc = FuelMixOptimiser()

        self.year_range = range(2025, 2051, 5) if (year_range is None) else year_range

        self.result = None

    def compare(self, 
                total_fuel: float | list[float], 
                main_fuel: Fuel, 
                second_fuel: Fuel,
                target_intensity: array_like, 
                penalty: float, 
                ) -> Comparison:
                
        kwargs = {'predicate':lambda x : isinstance(x, Number), 'transformation':lambda x : it.repeat(x)}
        _itercheck_partial = ft.partial(self._itercheck, **kwargs)

        main_fuel, second_fuel = map(dataclass_converter, (main_fuel, second_fuel), it.repeat(_itercheck_partial,2))

        total_fuel, penalty = map(_itercheck_partial, (total_fuel, penalty))

        args_penalty = (target_intensity, main_fuel.wtw_ef, main_fuel.lcv, penalty)
        penalty_list = list(map(self.penalty_calc.compute, *args_penalty))

        args_costs = (total_fuel, main_fuel.price, penalty_list)
        penalty_costs = list(map(self.penalty_calc.compute_cost, *args_costs))
        
        args_mixes = (target_intensity, main_fuel.wtw_ef, second_fuel.wtw_ef)
        mixes_list = list(map(self.mix_calc.compute, *args_mixes))

        args_mix_costs = (total_fuel, main_fuel.price, second_fuel.price, mixes_list)
        mix_costs = list(map(self.mix_calc.compute_cost, *args_mix_costs))

        mix_str = f'Mix {main_fuel.name} & {second_fuel.name}'
        penalty_str = f'Penalty only {main_fuel.name}'

        bool_mask = list(map(lambda x,y: x<y, mix_costs, penalty_costs))
        verdict = map(lambda x: mix_str if x else penalty_str, bool_mask)
        optimal_mix = map(lambda x,y: round(y,3) if x else 0., bool_mask, mixes_list)

        comparison_name = f'Comparison {main_fuel.name} & {second_fuel.name}'

        return Comparison(name=comparison_name, 
                          penalty_strat=penalty_costs, 
                          mix_strat=mix_costs,
                          optimal_mix=list(optimal_mix),
                          verdict=list(verdict)
                          )
    @staticmethod
    def _itercheck(arg: any, 
                   transformation: Callable[[V], R], 
                   predicate: Callable[[V], bool]
                   ) -> 'any | R':
        """
        Check if an argument returns true to a predicate function. 
        
        If it does, return func(arg), else returns arg

        Parameters
        ----------
        arg : any
            Any argument. Must be compatible with the predicate and transformation function
        transformation: Callable[[V], R]
            A transformation function. Takes an argument V and returns a result R. 
            R can be of the same type or a different type from V
        predicate: Callable[[V], bool]
            A predicate function. Takes an argument V and returns a bool. 
            Depending on the bool result, the transformation func will be executed or the original
            arg will be returned untouched
         
        Returns
        -------
        any | R
            The original arg or the transformed version depending on the result of predicate
        """
        if predicate(arg):
            return transformation(arg) 
        return arg

def process_fuel(ef_df: pd.DataFrame,
                prices_df: pd.DataFrame,
                lcv_df: pd.DataFrame,
                fuel_names: list[str] | str
                ):
    
    fuel_names = [fuel_names] if isinstance(fuel_names, str) else fuel_names

    for fuel in fuel_names:
        
        ef_list = ef_df.loc[fuel,:].to_list()
        ef_list = ef_list if len(set(ef_list))>1 else ef_list[0]
        lcv = lcv_df.loc[fuel,'lcv']
        price = prices_df.loc[fuel,'2025':].to_list()

        yield Fuel(fuel, price, lcv, ef_list)











    



    
