import pandas as pd
import osmnx as ox
import PySimpleGUI as sg
from matplotlib import pyplot as plt
from os import getcwd
from math import ceil

vertrekpunt_default = 'Binkomstraat 12A, 3210 Lubbeek'

############### Definiëren van functies ###############
def download_OSM_wegenkaart():
    # Vraag de gebruiker een input van parameters en laad de overeenkomstige cirkelschijf van de OSM wegenkaart
    layout = [[sg.Text('Adres van het vertrekpunt')], [sg.Input(default_text=vertrekpunt_default, key='vertrekpunt')],
              [sg.Text('Straal van de cirkel rondom het vertrekpunt [km]')], [sg.Input(default_text=6, key='straal')],
              [sg.Button('Ok', key='Ok')]]
    window = sg.Window('Selectievenster 2', layout)
    while True:
        _,values = window.read()
        try:
            straal = float(values['straal'])
            if straal <= 0:
                sg.popup("De straal kan enkel een positief getal zijn.")
                continue
        except:
            sg.popup("De straal kan enkel een positief getal zijn.")
            continue

        # Laad de wegenkaart in de omgeving van het vertrekpunt
        try:
            G = ox.graph_from_address(values['vertrekpunt'], dist=straal*1000, network_type='drive', simplify=False)
            print('\n', 'De Open Street Map van', straal, 'km rondom', values['vertrekpunt'], 'werd ingelezen.')
            break
        except:
            sg.popup("De wegenkaart kan niet geladen worden. Waarschijnlijk doordat het vertrekpunt niet herkend werd door Open Street Maps.")
    window.close()
    return G

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

def bestand_opslaan(G):
    folder = getcwd() + '\Wegenkaarten'
    layout = [[sg.T("")], [sg.Text("Opslaan als: "), sg.Input(), sg.FileSaveAs(initial_folder=folder, key="bestandsnaam")],[sg.Button("Ok")]]
    window = sg.Window('My File Browser', layout, size=(600,150))

    while True:
        _, values = window.read()
        if values['bestandsnaam'] == '':
            sg.popup('Geef een bestandsnaam op.')
            continue
        else:
            try:
                with open(values['bestandsnaam'], 'wb') as file:
                    pd.to_pickle(G, file)
                    print('De gewijzigde wegenkaart is opgeslagen als ' + values['bestandsnaam'] + '.')
                    break
            except:
                sg.popup('De wegenkaart kon niet worden opgeslagen.')
    window.close()


############### Beginsel van de nieuwe wegenkaart ###############
# De gebruiker krijgt 2 opties:
# 1. De OSM wegenkaart van een cirkelvormig gebied wordt gedownload. Het centrum en de straal van de cirkel worden opgevraagd aan de gebruiker.
# 2. Een kaart die reeds bewerkt is en opgeslagen in de map Wegenkaarten, wordt ingelezen.

layout = [ [sg.Text('Vanuit welk beginsel creëren we de nieuwe wegenkaart?')],
           [sg.Button('Een nieuwe download van Open Street Map')],
           [sg.Button('Een reeds bewerkte kaart op dit toestel')] ]
event = sg.Window('Selectievenster 1', layout).read(close=True)

if event[0] == 'Een nieuwe download van Open Street Map':
    G = download_OSM_wegenkaart()

    default_speed = 50
    for u, v, d in G.edges(data=True):
        if 'maxspeed' not in d:
            d['maxspeed_int'] = default_speed
        else:
            if isinstance(d['maxspeed'], list):
                if len(d['maxspeed']) == 0:
                    d['maxspeed_int'] = default_speed
                else:
                    d['maxspeed_int'] = int(d['maxspeed'][ceil(len(d['maxspeed'])/2)-1])
            elif d['maxspeed'] == '':
                d['maxspeed_int'] = default_speed
            else:
                d['maxspeed_int'] = int(d['maxspeed'])
        d['travel_time'] = d['length'] / d['maxspeed_int'] * .06 # Uitgedrukt in minuten
    print('\n', 'Alle ontbrekende snelheden werden aangepast naar', default_speed, 'km/h. In alle straten waar meer dan 1 snelheid gegeven was, werd de middelste genomen.')
else:
    G = bestand_selecteren_en_inlezen()


############### Wijzigingen aan de wegenkaart ###############
def onclick(event):
    while True:
        click_x, click_y = event.xdata, event.ydata
        try:
            nearedge = ox.nearest_edges(G, click_x, click_y)
            break
        except:
            print('Geen verbinding gevonden. Selecteer een verbinding.')

    knooppunt1 = nearedge[0]
    knooppunt2 = nearedge[1]
    edgenum = nearedge[2]
    edge = G.edges._adjdict[knooppunt1][knooppunt2][edgenum]
    #edge = G.edges._adjdict[knooppunt2][knooppunt1][edgenum]

    edge_keys = list(edge.keys())
    layout = [ [sg.Text('U selecteerde deze verbinding:')],
                [[sg.Text(k), sg.Push(), sg.Input(default_text=edge[k], key=k)] for k in edge_keys],
                [sg.Button('Wijzigingen toepassen voor deze verbinding')],
                [sg.Button('Wijzigingen toepassen voor de hele straat')],
                [sg.Button('Wijzigingen niet toepassen')] ]
    event,values = sg.Window('Selectievenster', layout).read(close=True)
    if event == 'Wijzigingen toepassen voor deze verbinding':
        print(values)
    elif event == 'Wijzigingen toepassen voor de hele straat':
        print(values)

Gu = ox.get_undirected(G)
fig, ax = plt.subplots()
ec = ox.plot.get_edge_colors_by_attr(G, 'maxspeed_int', cmap='plasma')
ox.plot_graph(Gu, ax=ax, edge_color=ec, edge_linewidth=3, node_size=0, show=False, close=False)

while True:
    cid = fig.canvas.mpl_connect('button_press_event', onclick)
    plt.show()
fig.canvas.mpl_disconnect(cid)

############### De nieuwe wegenkaart opslaan ###############
bestand_opslaan(G)