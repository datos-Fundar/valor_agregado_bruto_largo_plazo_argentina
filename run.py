
import argparse
from datetime import datetime
import csv as csv_
import re
from pandas import DataFrame
from src.fuentes import DataCleaner
from src.fuentes import (
    araoz_loader, 
    araoz_clean, 
    cepal_loader, 
    cepal_clean, 
    fnys_loader_producto, 
    fnys_cleaner_producto,
    fnys_loader_poblacion,
    fnys_cleaner_poblacion,
    indec_loader,
    indec_clean
    )
from src.procesamiento import Empalmador
from src.procesamiento import calcular_empalme_producto, calcular_empalme_poblacion

PATHS = {
    'path_araoz': "input_data/araoz_nicolini_et_al_Table_4_1.csv",
    'path_cepal': "https://repositorio.cepal.org/server/api/core/bitstreams/7399c6c9-0827-42da-b433-d176cb4107c7/content",
    'path_fnys_prod': "https://docs.google.com/spreadsheets/d/e/2PACX-1vTAGGfIqDw18YDI5zasGBRa4sG1ddUfMcKT87fzTkvz8HMe8Ipl6zJU0M2788oZrw/pub?output=xls",
    'path_indec': "https://www.indec.gob.ar/ftp/cuadros/poblacion/c1_proyecciones_prov_2010_2040.xls",
    'path_fnys_pob': "https://docs.google.com/spreadsheets/d/e/2PACX-1vTp7K9ixEWzesZybHJG_e47YfafF49L8dqgtLgqItT45Gb4Ru0YjIF0723lxCHRhA/pub?output=xls"
}

formato_fundar = {
    'encoding': 'utf-8',
    'sep': ',',
    'quoting': csv_.QUOTE_ALL,
    'quotechar': '"',
    'lineterminator': '\n',
    'decimal': '.',
    'index': False,
    'float_format': '%.5f'
}

def save_csv_fundar(data:DataFrame, outpath:str)->None:
    data.to_csv(outpath, **formato_fundar)

today = datetime.today().strftime('%Y%m%d')


def main(path_araoz:str, path_cepal:str, path_fnys_prod:str, path_fnys_pob:str, path_indec:str, guardar_limpias:bool=False):

    # Producto Bruto Geogáfico

    # Araoz participacion de las provincias en el PIB
    AraozData = DataCleaner(func_loader=araoz_loader, func_cleaner=araoz_clean)
    df_araoz = AraozData.process(filepath=path_araoz)
    print("Los datos de 'Araoz et al' fueron cargados...\n")

    # CEPAL-CEPXXI: VAB por provincia 2004-2022 a precios de 2004
    CepalData = DataCleaner(func_loader=cepal_loader, func_cleaner=cepal_clean)
    df_cepal = CepalData.process(filepath=path_cepal)
    print("Los datos de 'CEPAL-CEPXXI' fueron cargados...\n")

    # Fundación Norte y Sur PIB a precios de mercado de 2004
    ProductoFundNySData = DataCleaner(func_loader=fnys_loader_producto, func_cleaner=fnys_cleaner_producto)
    df_fnys_prod = ProductoFundNySData.process(filepath=path_fnys_prod) 
    print("Los datos de 'Fundación Norte y Sur (Producto)' fueron cargados...\n")

    dicc_prod = {'df_araoz':df_araoz,
                 'df_cepal':df_cepal,
                 'df_fnys_prod':df_fnys_prod}

    PbgEmpalme = Empalmador(data_dict=dicc_prod, empalme_func=calcular_empalme_producto).calculate()
    print("El empalme de 'Producto Bruto Geográfico' fue generado...\n")   
    

    # Población por provincia

    # Fundación Norte y Sur Población por provincia hasta 2018
    PoblacionFundNySData = DataCleaner(func_loader=fnys_loader_poblacion, func_cleaner=fnys_cleaner_poblacion)
    df_fnys_pob = PoblacionFundNySData.process(filepath=path_fnys_pob)
    print("Los datos de 'Fundación Norte y Sur (Población)' fueron cargados...\n")

    # INDEC - Proyecciones 2010-2040
    IndecData = DataCleaner(func_loader=indec_loader, func_cleaner=indec_clean)
    df_indec = IndecData.process(filepath=path_indec)
    print("Los datos de 'INDEC' fueron cargados...\n")

    dicc_pob = {'df_fnys_pob':df_fnys_pob, 'df_indec':df_indec}
    PobEmpalme = Empalmador(data_dict=dicc_pob, empalme_func=calcular_empalme_poblacion).calculate()
    print("El empalme de 'Población por provincia' fue generado...\n") 

    # Merge Empalmes

    data_empalmes = PbgEmpalme.merge(PobEmpalme, on=['provincia','anio'], how='left')
    data_empalmes['vab_pb_per_capita'] = data_empalmes['vab_pb'] / data_empalmes['pob_total'] 
    print("Se agregó calculo de Valor Agregado Bruto per cápita para la serie de tiempo...\n") 

    dicc_empalme = {'df_empalme':data_empalmes}
    if guardar_limpias: 
        # Exporto datasets limpios de PBG en '/tablas'
        for key,data in dicc_prod.items():
            outpath = f"tablas/clean_{re.sub('df_','',key)}.csv"
            save_csv_fundar(data=data, outpath=outpath)

        # Exporto datasets limpios de población en '/tablas'
        for key,data in dicc_pob.items():
            outpath = f"tablas/clean_{re.sub('df_','',key)}.csv"
            save_csv_fundar(data=data, outpath=outpath)
        
        print("Se guardaron los datasets limpios en './tablas'...\n") 
    
    save_csv_fundar(data=data_empalmes, outpath="tablas/empalme_series_pbg_pob_vab_pc.csv")
    print("Se guardó el empalme en './tablas'...\n")

    return data_empalmes



class Parser(argparse.ArgumentParser):
    
    def __init__(self):
        super(Parser, self).__init__(description='Expatistan CLI')

        self.add_argument('-g','--generar-tablas', 
                          action="store_true", 
                          help='Guarda en carpeta "tablas" todas las fuentes limpias utilizadas'
                        )
        
        # Argumento de debug para poder testear los argumentos.
        # Si está, no se ejecuta el programa.
        self.add_argument('--testarguments', '--testarguments', type=bool, help=argparse.SUPPRESS)
    
    def get_args(self): ...

    def parse_args(self):
        self.args = super(Parser, self).parse_args().__dict__
        return self
    

if __name__ == '__main__':
    parser = Parser().parse_args()
    args = parser.args

    if all(map(lambda x: x is None, args.values())):
        print('No se especificó ningún argumento')
        parser.print_help()
        exit(1)

    guardar_limpias = args.get('generar_tablas',False)

    main(**PATHS, guardar_limpias=guardar_limpias)




    