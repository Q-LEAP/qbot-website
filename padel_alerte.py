import datetime
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
import requests
from bs4 import BeautifulSoup

# --- CONFIGURATION INDIVIDUELLE ---
EMAIL_RECEPTEUR = "ton_adresse_email@gmail.com"  
EMAIL_EMETTEUR = "ton_adresse_email@gmail.com"   
MOT_DE_PASSE_APPLICATION = "xxxx xxxx xxxx xxxx" # Code Google à 16 lettres

# Créneaux spécifiques recherchés
CRENEAUX_RECHERCHES = ["17:00", "17:30", "18:00"]

def generer_tous_les_vendredis():
    """Génère la liste des dates des 4 prochains vendredis."""
    vendredis = []
    aujourdhui = datetime.now()
    jours_avant_vendredi = (4 - aujourdhui.weekday()) % 7
    if jours_avant_vendredi == 0 and aujourdhui.hour >= 20:
        jours_avant_vendredi = 7 # Si le vendredi soir est en cours, on passe aux suivants
        
    premier_vendredi = aujourdhui + timedelta(days=jours_avant_vendredi)
    for i in range(4): # Analyse les 4 vendredis à venir
        prochain = premier_vendredi + timedelta(days=i * 7)
        vendredis.append(prochain.strftime('%Y-%m-%d'))
    return vendredis

def verifier_creneaux_sur_page(url):
    """Analyse la page et renvoie la liste des heures disponibles correspondantes."""
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    creneaux_libres = []
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Repère toutes les lignes ou blocs contenant l'option de réservation
            elements_creneaux = soup.find_all(string=lambda text: text and "BUCHUNG" in text.upper())
            
            for element in elements_creneaux:
                parent_text = element.find_parent().get_text() if element.find_parent() else element
                # Vérifie si un de nos créneaux clés est écrit à côté du bouton de réservation
                for heure in CRENEAUX_RECHERCHES:
                    if heure in parent_text and heure not in creneaux_libres:
                        creneaux_libres.append(heure)
    except Exception as e:
        print(f"Erreur réseau sur {url} : {e}")
    return creneaux_libres

def envoyer_alerte(date_terrain, créneaux, url_direct):
    heures_texte = ", ".join(créneaux)
    sujet = f"🚨 PADEL DISPO - Vendredi {date_terrain} ({heures_texte})"
    corps = f"Bonne nouvelle ! Le(s) créneau(x) suivant(s) sont libres pour le vendredi {date_terrain} :\n⏱️ {heures_texte}\n\nRéservez immédiatement ici : {url_direct}"
    
    msg = MIMEText(corps)
    msg['Subject'] = sujet
    msg['From'] = EMAIL_EMETTEUR
    msg['To'] = EMAIL_RECEPTEUR
    
    try:
        with smtplib.SMTP_SSL('://gmail.com', 465) as server:
            server.login(EMAIL_EMETTEUR, MOT_DE_PASSE_APPLICATION)
            server.sendmail(EMAIL_EMETTEUR, EMAIL_RECEPTEUR, msg.as_string())
        print(f"E-mail d'alerte envoyé pour le {date_terrain} à {heures_texte} !")
    except Exception as e:
        print(f"Échec de l'envoi de l'e-mail : {e}")

# --- ANALYSE DES DISPONIBILITÉS ---
liste_vendredis = generer_tous_les_vendredis()

for date in liste_vendredis:
    # URL structure officielle CK Sportcenter pour le calendrier des terrains
    url_p1 = f"https://ck-sportcenter.lu{date}&page=1"
    url_p2 = f"https://ck-sportcenter.lu{date}&page=2"
    
    creneaux_p1 = verifier_creneaux_sur_page(url_p1)
    if creneaux_p1:
        envoyer_alerte(date, creneaux_p1, url_p1)
        
    creneaux_p2 = verifier_creneaux_sur_page(url_p2)
    if creneaux_p2:
        envoyer_alerte(date, creneaux_p2, url_p2)


