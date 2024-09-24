import pandas as pd
from pandas import DataFrame
from dataclasses import dataclass

@dataclass
class Empalmador:
    data_dict : dict[str, DataFrame]
    empalme_func : callable[[DataFrame],DataFrame]

    def calculate(self)-> DataFrame: 
        return self.empalme_func(**self.data_dict)
    

def calcular_pib_pm_provincial(df_araoz:pd.DataFrame, df_fnys:pd.DataFrame):
    df = df_araoz.merge(df_fnys, left_on='anio', right_on='anio', how="left")
    df['pib_pm'] = (df.share_gdp/100) * df.pib_pm
    return df[['provincia','anio','pib_pm']]

def agg_cepal(df_cepal:pd.DataFrame):
    return df_cepal.groupby(['provincia','anio'])['vab_pb'].sum().reset_index()

def calcular_empalme_producto(df_fnys_prod:DataFrame, df_araoz:DataFrame, df_cepal:DataFrame): 
    
    A = calcular_pib_pm_provincial(df_araoz=df_araoz, df_fnys=df_fnys_prod)
    B = agg_cepal(df_cepal=df_cepal)

    # Obtengo los valores del VAB pb del año 2004 
    valoresA2004 = A.loc[(A.anio == 2004)].set_index('provincia')['pib_pm']
    valoresB2004 = B.loc[(B.anio == 2004)].set_index('provincia')['vab_pb']
    
    ratios = (valoresB2004/valoresA2004).dropna()
    ratios.name = 'ratios'

    # Paso 3: Ajustar los datos del dataset A para años anteriores a 2004
    A_adjusted = A[A['anio'] < 2004].copy()
    A_adjusted = A_adjusted.set_index('provincia').join(ratios).reset_index()

    A_adjusted['vab_pb'] = A_adjusted['ratios'] * A_adjusted['pib_pm']
    A_adjusted = A_adjusted[['provincia','anio','vab_pb']]

    empalme = pd.concat([A_adjusted, B], ignore_index=True)

    return empalme[['provincia','anio','vab_pb']]


def calcular_empalme_poblacion(df_indec:pd.DataFrame, df_fnys_pob:pd.DataFrame): 

    anio_empalme = df_indec.anio.min()
    valores_indec = df_indec.loc[(df_indec.anio == anio_empalme)].set_index('provincia')['pob_total']
    valores_fnys = df_fnys_pob.loc[(df_fnys_pob.anio == anio_empalme)].set_index('provincia')['poblacion']

    ratios = (valores_indec/valores_fnys).dropna()
    ratios.name = 'ratios'

    # Paso 3: Ajustar los datos del dataset A para años anteriores a 2004
    fnys_adjusted = df_fnys_pob[df_fnys_pob['anio'] < anio_empalme].copy()
    fnys_adjusted = fnys_adjusted.set_index('provincia').join(ratios).reset_index()

    fnys_adjusted['pob_total'] = fnys_adjusted['ratios'] * fnys_adjusted['poblacion']
    fnys_adjusted = fnys_adjusted[['provincia','anio','pob_total']]

    empalme = pd.concat([fnys_adjusted, df_indec], ignore_index=True)

    return empalme[['provincia','anio','pob_total']]
