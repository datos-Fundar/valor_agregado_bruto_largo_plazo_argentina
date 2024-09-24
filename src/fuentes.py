from dataclasses import dataclass
import pandas as pd
from pandas import DataFrame
from pandas import read_csv, read_excel
from typing import Callable
import re


# Funciones auxiliares
def check_na_threshold(df, threshold):
    return df.apply(lambda row: row.isna().sum() >= threshold, axis=1)


# Lista de conectores y preposiciones que no se deben capitalizar
excepciones = ['del', 'de']

def corregir_provincia(nombre_provincia):
    # Remover el código numérico y el guión
    nombre_sin_codigo = re.sub(r'^.*?-','', nombre_provincia) 
    
    # Capitalizar el nombre, excepto preposiciones y conectores
    palabras = nombre_sin_codigo.lower().split()
    nombre_corregido = ' '.join([palabra.capitalize() if palabra not in excepciones else palabra for palabra in palabras])
    
    return nombre_corregido

@dataclass
class DataCleaner:

    func_loader : Callable[[str],DataFrame]
    func_cleaner: Callable[[DataFrame],DataFrame]

    
    def load_data(self, filepath)-> DataFrame:
        """Establecer la conexión con la fuente de datos"""
        return self.func_loader(filepath)

    def clean_data(self, data:DataFrame|dict)->DataFrame:
               
        return self.func_cleaner(data)
    
    def process(self, filepath:str)-> DataFrame: 

        data = self.load_data(filepath=filepath)
        clean_df = self.clean_data(data=data)
        return clean_df

####################################################################
# Funciones propias para la base de Araoz

def araoz_loader(filepath:str): 
    return read_csv(filepath)

def araoz_clean(data:pd.DataFrame):
    data['provincia'] = data['provincia'].str.replace("Capital Federal", "CABA") 
    data = data.melt(id_vars='provincia', var_name= 'anio', value_name='share_gdp')
    data['anio'] = data['anio'].astype('int')
    return data


####################################################################
# Funciones propias para la base de CEPAL

def cepal_loader(filepath:str)->dict[str,pd.DataFrame]: 
    return read_excel(filepath, sheet_name=None)

def cepal_clean(data:dict[str,pd.DataFrame]): 
    
    replacements = {"Cordoba":"Córdoba",
                    "Entre Rios":"Entre Ríos",
                    "Neuquen":"Neuquén",
                    "Rio Negro":"Río Negro",
                    "Tucuman": "Tucumán"
                    }

    # Me quedo con todas las hojas menos la primera.
    sheets_names = list(data.keys())[1:]
    
    cepal_data = []
    # Limpio provincias
    for sheet in sheets_names: 
        # print(f"Limpiando datos de CEPAL - Hoja: {sheet}\n")

            # Normalizo el nombre de la hoja
        sheet_name_normalized = sheet.replace("_", " ") 
        sheet_name_normalized = replacements.get(sheet_name_normalized) or sheet_name_normalized

        df_raw = data[sheet]

        # Me quedo con las columnas salteando la primera, y con todas las filas salteando las 5 primeras
        sheet_data = df_raw.iloc[5:,1:]

        cols = df_raw.iloc[4, 1:].tolist()

        sheet_data.columns = cols
                        
        # Cuento la cantidad de columnas
        num_cols = sheet_data.shape[1]

        # Aplico el filtro para remover filas con (num_cols - 1) nulos
        filter_bool = check_na_threshold(sheet_data, num_cols - 1)
        df = sheet_data[~filter_bool]

        # Elimino la última fila (fila agregada)
        df = df.iloc[:-1, :]

        # Obtengo el nombre de la primera columna
        primera_col = df.columns[0]

        # Obtengo los años
        primer_anio = int(df.columns[1])
        ultimo_anio = primer_anio + num_cols - 2
        anios = list(range(primer_anio, ultimo_anio + 1))

        # Genero el nuevo vector de columnas
        wide_cols = [primera_col] + [str(x) for x in anios]
        df.columns = wide_cols

        # Pivoteo los datos
        df = pd.melt(df, id_vars=[primera_col], var_name='anio', value_name='vab_pb')

        # Transformo las columnas y agrego la columna 'provincia'
        df['anio'] = pd.to_numeric(df['anio'], errors='coerce')
        df['vab_pb'] = pd.to_numeric(df['vab_pb'], errors='coerce')*1000000
        df['provincia'] = sheet_name_normalized if sheet_name_normalized != "Ciudad de Buenos Aires" else "CABA"

        # Limpiar nombres de columnas (similar a janitor::clean_names en R)
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

        cepal_data.append(df)

    return pd.concat(cepal_data, axis=0)


####################################################################
# Funcioens propias para las bases de Fundación Norte y Sur

fnys_loader_producto = lambda filepath: read_excel(filepath, 
                                                    sheet_name="OyD Precios ctes", 
                                                    header=None, usecols = [0,1], 
                                                    skiprows=16, 
                                                    dtype={0:int, 1:float}, 
                                                    names=['anio','pib_pm'])

fnys_loader_poblacion = lambda filepath: read_excel(filepath,
                                                    sheet_name="Población", 
                                                    header=1,
                                                    na_values=['-'], 
                                                    skiprows=list(range(2,74)))


def fnys_cleaner_producto(data:DataFrame)->DataFrame:
    data['pib_pm'] = data['pib_pm'] * 1000000
    return data.dropna(subset='pib_pm', axis=0)

def fnys_cleaner_poblacion(data:DataFrame)->DataFrame:
    replacements = {'Ciudad de Buenos Aires': 'CABA',
                    'Sta Cruz':'Santa Cruz',
                    'Santa Fé':'Santa Fe'}
    
    data.rename(columns={"Año":'anio'}, inplace=True)
    data = pd.melt(data, id_vars="anio", var_name="provincia", value_name="poblacion") 
    data['provincia'] = data['provincia'].replace(replacements)
    data['poblacion'] = data['poblacion'] * 1000
                
    return data.dropna(subset='poblacion', axis=0)


####################################################################
# Funcioens propias para la base de INDEC

def indec_loader(filepath:str)->dict[str,pd.DataFrame]: 
    return read_excel(filepath, sheet_name=None)

def indec_clean(data:dict[str,pd.DataFrame]): 
            
    # Me quedo con todas las hojas menos la primera.
    sheets_names = list(data.keys())[2:]
    
    indec_data = []
    # Limpio provincias
    for sheet in sheets_names: 
        # print(f"Limpiando datos de INDEC - Hoja: {sheet}\n")

            # Normalizo el nombre de la hoja
        sheet_name_normalized = corregir_provincia(nombre_provincia=sheet)
        sheet_name_normalized = "CABA" if sheet_name_normalized == "Caba" else sheet_name_normalized.replace("Sante Fe","Santa Fe")
        df_raw = data[sheet]

        sheet_data = df_raw.iloc[4:36,:].dropna(axis=0, how='all')

        cols = ['anio','pob_total','pob_varones','pob_mujeres']

        sheet_data.columns = cols
                        
        df = sheet_data.copy()

        # Agrego la columna 'provincia'
        df['provincia'] = sheet_name_normalized

        indec_data.append(df)

    indec_data = pd.concat(indec_data, axis=0).dropna(subset='pob_total')
    indec_data['anio'] = indec_data['anio'].astype(int)
    indec_data['pob_total'] = indec_data['pob_total'].astype(float)
    indec_data['pob_varones'] = indec_data['pob_varones'].astype(float)
    indec_data['pob_mujeres'] = indec_data['pob_mujeres'].astype(float)

    return indec_data.sort_values(by=['provincia','anio']).reset_index(drop=True)
