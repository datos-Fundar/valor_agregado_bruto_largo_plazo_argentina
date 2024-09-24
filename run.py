
from src.fuentes import AraozData, CepalData, FundNorteySurData
from src.procesamiento import *
import argparse
from datetime import datetime



PATHS = {
    'path_araoz': "input_data/araoz_nicolini_et_al.csv",
    'path_cepal': "https://repositorio.cepal.org/server/api/core/bitstreams/7399c6c9-0827-42da-b433-d176cb4107c7/content",
    'path_fnys': "https://docs.google.com/spreadsheets/d/e/2PACX-1vTAGGfIqDw18YDI5zasGBRa4sG1ddUfMcKT87fzTkvz8HMe8Ipl6zJU0M2788oZrw/pub?output=xls"
}


today = datetime.today().strftime('%Y%m%d')

def main(path_araoz:str, path_cepal:str, path_fnys:str, guardar_limpias:bool=False): 
    
    print("Cargando y limpiando fuentes de información...\n")
    # Araoz et al
    araoz = AraozData()
    araoz.init(filepath=path_araoz)
    data_araoz = araoz.load_data()
    data_transformed_araoz = araoz.clean_data(data_araoz)

    # Cepal
    cepal = CepalData()
    cepal.init(filepath=path_cepal)
    data_cepal = cepal.load_data()
    data_transformed_cepal = cepal.clean_data(data_cepal)

    # Fundación Norte y Sur
    fundnorteysur = FundNorteySurData()
    fundnorteysur.init(filepath=path_fnys)
    data_fundnorteysur = fundnorteysur.load_data()
    data_transformed_fundnorteysur = fundnorteysur.clean_data(data_fundnorteysur) 

    if guardar_limpias: 
        data_transformed_araoz.to_csv(f"tables/CLEAN_araoz_et_al_{today}.csv", index=False)
        data_transformed_cepal.to_csv(f"tables/CLEAN_cepal_{today}.csv", index=False)
        data_transformed_fundnorteysur.to_csv(f"tables/CLEAN_fundacion_norte_y_sur_{today}.csv", index=False)
        print("Tablas limpias guardadas...\n")

    print("Generando procesamiento a partir de fuentes limpias...\n")

    # utilizamos el PIB a precios de mercados de Fundación Norte y Sur y lo distribuimos a las provincias
    # con la participación en el VAB a precios básicos calculada por Araoz et al
    A = calcular_pib_pm_provincial(df_araoz = data_transformed_araoz, df_fnys= data_transformed_fundnorteysur)

    # Nos traemos el dato de CEPAL agregado por provincia (suamndo el todas las actividades)
    B = agg_cepal(df_cepal=data_transformed_cepal)

    # Calculamos el empalme tomando el año 2004 como año de empalme. Llevando la serie de CEPAL hacia atrás. 
    empalme = calcular_empalme(A=A, B=B)

    print("Finalizó procesamiento...\n")

    ultimo_anio = empalme.anio.max()

    empalme.to_csv(f"tables/serie_empalmada_vab_pb_1895_{ultimo_anio}_{today}.csv", index=False)
    print("Empalme guardado...")

    return empalme



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




    