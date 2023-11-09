# Verwijder rijen met Volwassen==0 en Kinder==0
# Apart script maken om de wegenkaart aan te passen en op te slaan
# Snelheden controleren, straat aan vosken verwijderen
# Laat max_aantal_wagens toenemen zodat er geen routeplan met 5 wagens worden berekend als er al geen gunstige routes met 4 wagens waren.
# Incorporeer de terugrit
import pandas as pd
from matplotlib import pyplot as plt
import numpy as np
import osmnx as ox
import itertools as it
import PySimpleGUI as sg
from os import getcwd


############### Ingeven van parameters ###############
# De volgende parameters worden gebruikt doorheen het programma en kunnen worden aangepast indien gewenst.
vertrekpunt = 'Binkomstraat 12A, Lubbeek'
excel_filename = 'Ontbijt.xlsx'
wegenkaart_folder = getcwd() + '\Wegenkaarten'
wegenkaart_bestandsnaam = 'OSMNX_Wegenkaart'
max_aantal_wagens = 3
max_reistijd_per_route = 25 # Uitgedrukt in minuten
aan_de_deur_tijd_per_levering = 2 # uitgedrukt in minuten
aantal_resultaten_tonen = 35


############### Definiëren van functies ###############
def verwijder_onvolledige_data(df,noodzakelijk):
    # Syntax: df_volledig = verwijder_onvolledige_data(df,noodzakelijk)
    # De input df is een dataframe en noodzakelijk is een lijst van kolomnamen in df.
    # De output df_volledig is een dataframe die enkel de rijen van df bevat waarbij de noodzakelijke kolommen ingevuld zijn.
    # De onvolledige rijen worden verwijderd en bij wijze van waarschuwing geprint in de log.
    df_volledig = df.dropna(subset=noodzakelijk, how='any')
    if df_volledig.shape[0] < df.shape[0]:
        print('\n', 'De volgende rijen in', excel_filename, 'zijn onvolledig en worden niet verwerkt in het programma. Vervolledig de rijen indien ze van belang zijn. De noodzakelijke kolommen voor verwerking zijn:', ', '.join(noodzakelijk),'.')
        print(df[~df.index.isin(df_volledig.index)])
    return df_volledig

def verwijder_onherkende_adressen(df):
    # Zoek voor alle herkende adressen het dichtstbijzijnde knooppunt op de wegenkaart.
    # Verwijder alle onherkende adressen en plaats een waarschuwing in de log.
    df = df.assign(Adres = df["Straat"] + ' ' + df["Huisnr"] + ', ' + df["Plaats"])
    df = df.assign(Coordinaten = adres_naar_coordinaten(list(df['Adres']))) # Onherkende adressen krijgen Coordinaten='Adres niet herkend'

    # onherkende adressen
    onherkende_adressen = df[df.Coordinaten=='Adres niet herkend']
    onherkende_adressen = onherkende_adressen.drop(columns=['Adres','Coordinaten'])
    print('\n', 'De volgende adressen in', excel_filename, 'werden niet herkend en worden niet verwerkt in het programma. Corrigeer de adressen.')
    print(onherkende_adressen)
    
    # herkende adressen
    df = df[df.Coordinaten!='Adres niet herkend']
    df = df.assign(Knooppunt = coordinaten_naar_knooppunt(list(df['Coordinaten'])))
    return df

def adres_naar_coordinaten(adres):
    if isinstance(adres, str):
        # De input is een string die een adres voorstelt.
        # De output is een tuples die de overeenkomstige coordinaten voorstelt.
        try:
            coordinaten = ox.geocode(adres)
            return coordinaten
        except:
            return 'Adres niet herkend'
    elif isinstance(adres, list):
        # De input is een lijst van strings die adressen voorstellen.
        # De output is een lijst van tuples die de overeenkomstige coordinaten voorstellen.
        return [adres_naar_coordinaten(a) for a in adres]

def coordinaten_naar_knooppunt(coordinaten):
    if isinstance(coordinaten,tuple):
        # De input is een tuple die coordinaten voorstellen.
        # De output is een integer die het overeenkomstige dichtsbijzijnde knooppunt op de wegenkaart voorstelt.
        coordinatenY = coordinaten[0]
        coordinatenX = coordinaten[1]
    elif isinstance(coordinaten,list):
        # De input is een lijst van tuples die coordinaten voorstellen.
        # De output is een lijst van integers die de overeenkomstige dichtsbijzijnde knooppunten op de wegenkaart voorstellen.
        coordinatenY = [c[0] for c in coordinaten]
        coordinatenX = [c[1] for c in coordinaten]
    return ox.nearest_nodes(G, coordinatenX,coordinatenY)

def onderlinge_route_gegevens(knooppunten):
    # De output is een lijst van integers die knooppunten op de wegenkaart voorstellen.
    # De outputs onderlinge_reistijden en onderlinge_afstanden zijn matrices die de reistijden en afstanden 
    # van de snelste verbindingen tussen de verschillende knooppunten (en het vertrekpunt) bevatten.
    # Syntax: De diagonaalelementen onderlinge_reistijden[ii,ii] stellen de reistijden van het startpunt naar knooppunt[ii] voor.
    # De andere elementen onderlinge_reistijden[ii,jj] stellen de reistijden van knooppunt[ii] naar knooppunt[jj] voor.
    onderlinge_reistijden = np.zeros([aantal_bestemmingen, aantal_bestemmingen])
    onderlinge_afstanden = np.zeros([aantal_bestemmingen, aantal_bestemmingen])
    for ii in range(aantal_bestemmingen):
        for jj in range(aantal_bestemmingen):
            if ii == jj:
                route = snelste_route(vertrekpunt_knooppunt, knooppunten[ii]) #De snelste route van het vertrekpunt naar bestemming ii
            else:
                route = snelste_route(knooppunten[ii], knooppunten[jj]) #De snelste route van bestemming ii naar bestemming jj
            onderlinge_reistijden[ii,jj] = sum(ox.utils_graph.route_to_gdf(G, route, weight='travel_time')['travel_time'])
            onderlinge_afstanden[ii,jj] = sum(ox.utils_graph.route_to_gdf(G, route, weight='travel_time')['length']) / 1000 # Uitgedrukt in km
    return onderlinge_reistijden, onderlinge_afstanden

def snelste_route(startpunt,eindpunt):
    # Stel de snelste route samen tussen de twee opgegeven knooppunten.
    return ox.shortest_path(G, startpunt, eindpunt, weight='travel_time')

def visualiseer_routeplan(routeplan):
    # Construeer de gehele route voor elke wagen
    routes = []
    for rp in routeplan:
        tussenstops = [df_Tijdsblok['Knooppunt'].iloc[ii] for ii in rp]
        routes.append(construeer_route(tussenstops))
    colors = ['r','g','b','y','m','c','tab:orange','tab:purple','tab:pink','tab:gray','tab:brown','k']
    fig, ax = ox.plot_graph_routes(G, routes, route_colors=colors[0:len(routes)], bgcolor='w', route_linewidth=6, node_size=0, show=False, close=False)

    # Toon de routes op de wegenkaart
    coordinaten = list(df_Tijdsblok['Coordinaten'])
    coordinatenY = [c[0] for c in coordinaten]
    coordinatenX = [c[1] for c in coordinaten]
    ax.scatter(coordinatenX, coordinatenY, c='k')
    return ax

def construeer_route(knooppunten):
    # Construeer een route die langs alle opgegeven knooppunten gaat in de opgegeven volgorde.
    route = snelste_route(vertrekpunt_knooppunt, knooppunten[0])
    for ii in range(len(knooppunten)-1):
        next_part = snelste_route(knooppunten[ii], knooppunten[ii+1])
        route = concatenate_routes(route, next_part)
    next_part = snelste_route(knooppunten[-1], vertrekpunt_knooppunt)
    route = concatenate_routes(route, next_part)
    return route

def concatenate_routes(route1,route2):
    # Combineer 2 routes die op elkaar volgen tot 1 route
    if route1[-1] != route2[0]:
        raise Exception("Kan routes niet combineren omdat route ",route1," eindigt in knooppunt ",route1[-1]," en route ",route2," begint in knooppunt ",route2[0],".")
    else:
        route1.extend(route2[1:])
        return route1


############### importeer wegenkaart ###############
# De wegenkaart is een collectie van knooppunten en verbindingen tussen die knooppunten
G = pd.read_pickle(wegenkaart_folder + "\\" + wegenkaart_bestandsnaam)
print('\n', 'Het bestand', wegenkaart_bestandsnaam, 'werd ingelezen.')


############### Inlezen van data ###############
# Importeer en controleer excel data
df = pd.read_excel(excel_filename, converters={'Huisnr':str, 'Busnr':str, 'Postcode':str})
df.index += 2 # Wijzig de indices in de dataframe zodat ze overeenkomen met de rijnummers in excel
df = verwijder_onvolledige_data(df, noodzakelijk=['Straat', 'Huisnr', 'Postcode', 'Plaats', 'Volwassen', 'Kind', 'Levering'])
df = verwijder_onherkende_adressen(df)


############### Selecteer een tijdsblok ###############
Tijdsblokken = set(df['Levering'].unique())
# print(Tijdsblokken)

# Manuele selectie
Tijdsblok = '09u00 - 09u30'
df_Tijdsblok = df[df.Levering == Tijdsblok]


############### Vind de meest efficiënte routes ###############
vertrekpunt_knooppunt = coordinaten_naar_knooppunt(adres_naar_coordinaten(vertrekpunt))
aantal_bestemmingen = df_Tijdsblok.shape[0]
onderlinge_reistijden, onderlinge_afstanden = onderlinge_route_gegevens(list(df_Tijdsblok['Knooppunt']))

resultaten = pd.DataFrame()
verdeling = [1] * aantal_bestemmingen
while True:
    totale_afstand = 0
    routeplan = []
    reistijden = []
    for auto_num in range(1,max_aantal_wagens+1): # auto_num = 1,2,... (begint bij 1)
        indices = [ii for ii, x in enumerate(verdeling) if x == auto_num]
        # Vind voor elke wagen de meest efficiënte route voor zijn opgegeven bestemmingen
        if len(indices) > 0:
            reistijd_snelste_route = float('inf')
            for volgorde in list(it.permutations(indices)):
                route_reistijd = onderlinge_reistijden[volgorde[0]][volgorde[0]] + onderlinge_reistijden[volgorde[-1]][volgorde[-1]] # Van vertrekpunt naar eerste bestemming + van laatste bestemming naar vertrekpunt
                for bestemming_num in range(len(volgorde)-1):
                    route_reistijd += onderlinge_reistijden[volgorde[bestemming_num]][volgorde[bestemming_num+1]] # Van bestemming i naar bestemming (i+1)
                if route_reistijd < reistijd_snelste_route:
                    beste_volgorde = list(volgorde)
                    reistijd_snelste_route = route_reistijd
            route_afstand = onderlinge_afstanden[beste_volgorde[0]][beste_volgorde[0]] + onderlinge_afstanden[beste_volgorde[-1]][beste_volgorde[-1]]
            for bestemming_num in range(len(beste_volgorde)-1):
                route_afstand += onderlinge_afstanden[beste_volgorde[bestemming_num]][beste_volgorde[bestemming_num+1]]
            routeplan.append(beste_volgorde)
            reistijden.append(reistijd_snelste_route + len(beste_volgorde)*aan_de_deur_tijd_per_levering)
            totale_afstand += route_afstand
        te_laat_mins = sum( [max(0, t-max_reistijd_per_route) for t in reistijden] )

    nieuw_resultaat = pd.DataFrame(data={'routeplan':[routeplan], 'reistijden_mins':[reistijden], 'max reistijd [min]':[max(reistijden)], 'totale afstand [km]':[totale_afstand], 'te laat [min]': te_laat_mins})
    resultaten = pd.concat([resultaten,nieuw_resultaat], ignore_index=True)

    # Selecteer de volgende verdeling
    changed = False
    idx = aantal_bestemmingen - 1
    while idx > 0:
        if verdeling[idx] <= min([max(verdeling[:idx]), max_aantal_wagens-1]):
            verdeling = verdeling[:idx] + [verdeling[idx]+1] + [1]*(aantal_bestemmingen-1-idx)
            changed = True
            break
        else:
            idx -= 1
    if changed == False:
        break

resultaten = resultaten.sort_values(['te laat [min]', 'totale afstand [km]', 'max reistijd [min]'], ascending=[True,True,True])
resultaten = resultaten.reset_index(drop=True)
resultaten.index += 1 # Wijzig de indices in de dataframe zodat ze beginnen bij 1.


############### Selecteer het gewenste routeplan ###############
resultaten_display = resultaten.iloc[range(aantal_resultaten_tonen)].to_string(columns=['totale afstand [km]', 'max reistijd [min]', 'te laat [min]'])
resultaten_display = resultaten_display.split('\n')

layout = [ [sg.Text(resultaten_display[0])],
           [sg.Listbox(resultaten_display[1:], default_values=resultaten_display[1], select_mode='multiple', size=(100, aantal_resultaten_tonen), key='keuze')],
           [sg.Button('Toon route'), sg.Button('Kies')] ]
window = sg.Window(str(Tijdsblok), layout)
while True:
    event, values = window.read()
    keuze = [int(k[0:k.index(' ')]) for k in values["keuze"]]
    if event == 'Toon route':
        if len(keuze) == 0:
            sg.popup('Selecteer minstens één keuze om te weergeven.')
        else:
            for k in keuze:
                ax = visualiseer_routeplan(resultaten['routeplan'].iloc[k])
            plt.show()
    else:
        if len(keuze) == 1:
            keuze = keuze[0]
            print('keuze =', keuze)
            break
        else:
            sg.popup('Selecteer één en slechts één keuze.')
window.close()

############### Genereer output ###############
