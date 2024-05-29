import PySimpleGUI as sg
import pandas as pd
from os import getcwd

def bestand_selecteren_en_inlezen():
    folder = getcwd() + '\Wegenkaarten'
    layout = [[sg.T("")], [sg.Text("Selecteer het bestand: "), sg.Input(), sg.FileBrowse(initial_folder=folder, key="bestandsnaam")],[sg.Button("Ok")]]
    window = sg.Window('My File Browser', layout, size=(600,150))

    while True:
        _, values = window.read()
        if values['bestandsnaam'] == '':
            sg.popup('Selecteer een bestand.')
            continue
        else:
            try:
                G = pd.read_pickle(values['bestandsnaam'])
                print('\n', 'Het bestand', values['bestandsnaam'], 'werd ingelezen.')
                break
            except:
                sg.popup('De wegenkaart kon niet worden ingelezen.')
    window.close()
    return G

G = bestand_selecteren_en_inlezen()

