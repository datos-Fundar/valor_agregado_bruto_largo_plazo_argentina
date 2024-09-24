from abc import ABC, abstractmethod
import pandas as pd
from pandas import read_csv, read_excel
from typing import Callable

class DataCleaner(ABC):

    @abstractmethod
    def load_data(self, filepath, reader:Callable[[str],pd.DataFrame]):
        """Establecer la conexión con la fuente de datos"""
        return reader(filepath)

    @abstractmethod
    def clean_data(self, data:pd.DataFrame|dict, data_wrangling:Callable[[pd.DataFrame],pd.DataFrame]):
        
        return data_wrangling(data)

    


def check_na_threshold(df, threshold):
    return df.apply(lambda row: row.isna().sum() >= threshold, axis=1)


class AraozData(DataCleaner):

    def init(self, filepath:str):
        self.filepath = filepath

    def load_data(self):

        def araoz_loader(filepath:str): 
            return read_csv(filepath)

        return super().load_data(filepath = self.filepath, reader = araoz_loader)
    
    def clean_data(self, data):

        def araoz_clean(data:pd.DataFrame):
            data['provincia'] = data['provincia'].str.replace("Capital Federal", "CABA") 
            data = data.melt(id_vars='provincia', var_name= 'anio', value_name='share_gdp')
            data['anio'] = data['anio'].astype('int')
            return data

        return super().clean_data(data = data, data_wrangling=araoz_clean)



class CepalData(DataCleaner):

    def init(self, filepath:str):
        self.filepath = filepath

    def load_data(self):
        
        def cepal_loader(filepath:str)->dict[str,pd.DataFrame]: 
            return read_excel(filepath, sheet_name=None)

        return super().load_data(filepath = self.filepath, reader = cepal_loader)
    
    def clean_data(self, data:dict[str,pd.DataFrame]):

        def cepal_clean(data:dict[str,pd.DataFrame]): 
            
            replacements = {"Cordoba":"Córdoba",
                            "Entre Rios":"Entre Ríos",
                            "Neuquen":"Neuquén",
                            "Rio Negro":"Río Negro",
                            "Tucuman": "Tucumán"
                            }

            # Me quedo con todas las hojas menos la primera.
            sheets_names = list(pd.read_excel(self.filepath, sheet_name=None).keys())[1:]
            
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
                df['vab_pb'] = pd.to_numeric(df['vab_pb'], errors='coerce')
                df['provincia'] = sheet_name_normalized if sheet_name_normalized != "Ciudad de Buenos Aires" else "CABA"

                # Limpiar nombres de columnas (similar a janitor::clean_names en R)
                df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

                cepal_data.append(df)

            return pd.concat(cepal_data, axis=0)

        return super().clean_data(data, data_wrangling=cepal_clean)
    


class FundNorteySurData(DataCleaner):

    def init(self, filepath:str):
        self.filepath = filepath

    def load_data(self):
        
        def fundnorteysur_loader(filepath:str)->dict[str,pd.DataFrame]: 
            return read_excel(filepath, 
                            sheet_name="OyD Precios ctes", 
                            header=None, usecols = [0,1], 
                            skiprows=16, 
                            dtype={0:int, 1:float}, 
                            names=['anio','pib_pm']
                            )

        return super().load_data(filepath = self.filepath, reader = fundnorteysur_loader)
    
    def clean_data(self, data:pd.DataFrame):

        def fundnorteysur_clean(data:pd.DataFrame): 
                       
            return data.dropna(subset='pib_pm', axis=0)

        return super().clean_data(data, data_wrangling=fundnorteysur_clean)
