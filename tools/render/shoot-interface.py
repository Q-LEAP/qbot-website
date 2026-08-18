# -*- coding: utf-8 -*-
"""Capture la maquette « Interface & API » dans les deux langues.

Ce script n'existait pas : la capture d'origine avait été faite à la main, et c'est
précisément pour ça qu'une correction de casse dans la maquette (« Q-BOT » → « Q-Bot »)
ne s'était pas propagée à l'image publiée — le texte est cuit dans le JPEG.

Rappel de ce que produit la maquette : ce n'est PAS une capture du produit, c'est un
schéma. À remplacer dès qu'une vraie capture de l'interface existe.

Deux points non négociables, sinon l'image change de cadrage :
- la maquette est dessinée à sa taille d'affichage réelle (680 × 560) et capturée en
  DPR 2 → 1360 × 1120, comme les fichiers actuels ;
- les polices Google doivent être chargées avant la capture, sinon le texte tombe
  sur une police de repli et la mise en page bouge.

Usage :  python3 tools/render/shoot-interface.py            (depuis la racine du dépôt)
"""
import pathlib
from playwright.sync_api import sync_playwright

RACINE = pathlib.Path(__file__).resolve().parents[2]
SRC = (RACINE / "tools/render/interface-mockup.html").as_uri()
W, H, DPR = 680, 560, 2

# Traductions appliquées par clé `data-t`. La maquette porte le français en dur.
EN = {
    "url": "q-bot.local / scenarios",
    "eyebrow": "Scenario",
    "title": "Two-factor authentication",
    "s1": "Open the application under test",   "s1d": "Browser, mobile or desktop",
    "s2": "Enter the credentials",             "s2d": "From your test script",
    "s3": "Trigger two-factor authentication", "s3d": "Notification sent to the phone",
    "s4": "Q-Bot approves the request",        "s4d": "No human intervention",
    "s5": "Continue the test scenario",        "s5d": "The session is authenticated",
    "api": "REST API",
    "ok": "Authentication approved",
}

with sync_playwright() as p:
    b = p.chromium.launch()
    for suffixe, trad in (("", None), ("-en", EN)):
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=DPR)
        pg.goto(SRC, wait_until="load")
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(1200)                      # polices Google
        if trad:
            pg.evaluate("""(t) => { for (const k in t) {
                const e = document.querySelector('[data-t="'+k+'"]');
                if (e) e.textContent = t[k]; } }""", trad)
            pg.wait_for_timeout(400)
        cible = RACINE / f"assets/img/qbot-interface{suffixe}.jpg"
        pg.screenshot(path=str(cible), type="jpeg", quality=92)
        pg.close()
        print(f"{cible.name} écrit")
    b.close()
