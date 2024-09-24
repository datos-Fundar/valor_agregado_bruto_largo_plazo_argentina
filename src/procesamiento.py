import pandas as pd


def calcular_pib_pm_provincial(df_araoz:pd.DataFrame, df_fnys:pd.DataFrame):
    df = df_araoz.merge(df_fnys, left_on='anio', right_on='anio', how="left")
    df['pib_pm'] = (df.share_gdp/100) * df.pib_pm
    return df[['provincia','anio','pib_pm']]

def agg_cepal(df_cepal:pd.DataFrame):
    return df_cepal.groupby(['provincia','anio'])['vab_pb'].sum().reset_index()

def calcular_empalme(A:pd.DataFrame, B:pd.DataFrame): 
        
    # Obtengo los valores del VAB pb del año 2004 
    valoresB2004 = B.loc[(B.anio == 2004)].set_index('provincia')['vab_pb']
    valoresA2004 = A.loc[(A.anio == 2004)].set_index('provincia')['pib_pm']

    ratios = (valoresB2004/valoresA2004).dropna()
    ratios.name = 'ratios'

    # Paso 3: Ajustar los datos del dataset A para años anteriores a 2004
    A_adjusted = A[A['anio'] < 2004].copy()
    A_adjusted = A_adjusted.set_index('provincia').join(ratios).reset_index()

    A_adjusted['vab_pb'] = A_adjusted['ratios'] * A_adjusted['pib_pm']
    A_adjusted = A_adjusted[['provincia','anio','vab_pb']]

    empalme = pd.concat([A_adjusted, B], ignore_index=True)

    return empalme[['provincia','anio','vab_pb']]


