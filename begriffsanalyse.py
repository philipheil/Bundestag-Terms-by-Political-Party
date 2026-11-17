"""
Begriffsanalyse von Bundestagsreden: Wie oft kommen bestimmte Wörter vor,
und welche Fraktion benutzt sie?

Liest alle Plenarprotokolle (XML) im Ordner "Plenarprotokolle", ordnet jede Rede
der Fraktion des Redners zu und zählt Reden, in denen einer der gesuchten
Begriffe vorkommt. Gezählt wird nur der Text des Redners selbst – Zwischenrufe
(<kommentar>) und Einwürfe des Präsidiums werden ignoriert.

Aufruf:
  python3 begriffsanalyse.py                      # Begriffe aus BEGRIFFE unten
  python3 begriffsanalyse.py Klimageld Heizungs-gesetz
  python3 begriffsanalyse.py Bürgergeld --csv buergergeld.csv

Mehrwörtige Begriffe gehören in Anführungszeichen, sonst werden sie als
mehrere einzelne Begriffe gesucht:
  python3 begriffsanalyse.py "soziale Marktwirtschaft"   # eine Wortfolge
  python3 begriffsanalyse.py soziale Marktwirtschaft     # zwei Begriffe!

Ausgabe: Tabelle in der Konsole + CSV-Datei (jede Fundstelle mit Kontext)
"""
import argparse
import csv
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

ORDNER = Path(__file__).parent / "Plenarprotokolle"
AUSGABE = "begriffsanalyse.csv"

# Standardbegriffe, wenn beim Aufruf keine angegeben werden. Zum Austauschen
# einfach diese Liste ändern – oder die Begriffe beim Aufruf mitgeben, dann
# bleibt die Liste unberührt.
BEGRIFFE = ["Regenbogenflagge", "Regenbogenfahne"]

# Für die Begriffe in BEGRIFFE und die beim Aufruf übergebenen gilt:
#
# Groß- und Kleinschreibung spielt keine Rolle. Mitgezählt werden immer
#   - Mehrzahl und Beugung: Regenbogenflaggen, Regenbogenfahnen
#   - Zusammensetzungen: Regenbogenflaggenverbot, Regenbogenfahnenwerk
# Andere Wörter mit demselben Anfang (z. B. Regenbogenfamilie) dagegen nicht,
# weil der Begriff vollständig vorkommen muss.
#
# Eine Wortfolge gehört als ein Eintrag in die Liste, z. B.
# "geschlechtergerechte Sprache". Die Beugung gilt dann für jedes Wort darin,
# gefunden wird also auch "geschlechtergerechter Sprache". Zwischen den
# Wörtern dürfen beliebig viele Leerzeichen oder ein Zeilenumbruch stehen,
# wie sie im Protokoll vorkommen.
#
# Ein Bindestrich im Begriff markiert eine Stelle, an der im Text ebenso gut
# ein Leerzeichen oder nichts stehen darf: "Lieferketten-gesetz" findet
# "Lieferkettengesetz", "Lieferketten-Gesetz" und "Lieferketten Gesetz".
# Für die Standardbegriffe wird das nicht gebraucht, weil "Regenbogenflagge"
# und "Regenbogenfahne" in den Protokollen durchweg zusammengeschrieben sind.


def baue_muster(begriffe):
    """Baut aus einer Liste von Begriffen einen regulären Ausdruck."""
    teile = []
    for b in begriffe:
        woerter = []
        for wort in b.split():
            # Bindestrich = optionale Trennstelle innerhalb eines Wortes
            stuecke = [re.escape(s) for s in wort.split("-") if s]
            if stuecke:
                # \w* nur am Wortende: erfasst Beugung und Zusammensetzungen
                woerter.append(r"[\s-]*".join(stuecke) + r"\w*")
        if woerter:
            teile.append(r"\b" + r"[\s-]+".join(woerter))
    if not teile:
        raise SystemExit("Keine Begriffe angegeben.")
    return re.compile("|".join(teile), re.IGNORECASE)


BUNDESLAENDER = {
    "BADEN-WÜRTTEMBERG", "BAYERN", "BERLIN", "BRANDENBURG", "BREMEN", "HAMBURG",
    "HESSEN", "MECKLENBURG-VORPOMMERN", "NIEDERSACHSEN", "NORDRHEIN-WESTFALEN",
    "RHEINLAND-PFALZ", "SAARLAND", "SACHSEN", "SACHSEN-ANHALT",
    "SCHLESWIG-HOLSTEIN", "THÜRINGEN",
}

LAND_IN_KLAMMERN = re.compile(
    r"\(\s*(" + "|".join(sorted(BUNDESLAENDER)) + r")\s*\)", re.IGNORECASE)


def ohne_fraktion(rolle):
    """Ordnet Redner ohne Fraktionsangabe nach ihrem Amt ein.

    Wer ein Regierungsamt innehat, wird im Protokoll ohne Fraktion geführt
    (geprüft: keine einzige Rede trägt Fraktion und Amt zugleich). Hier sind
    das vor allem Kabinettsmitglieder, daneben Staatssekretäre, Vertreter der
    Länder im Bundesrat und einzelne Amtsträger wie der Wehrbeauftragte.
    """
    r = re.sub(r"\s+", " ", (rolle or "")).strip()
    # Satzfehler im Protokoll reparieren: vereinzelt ist der Wortanfang
    # abgetrennt, etwa "B undesministerin" oder "S taatsministerin".
    r = re.sub(r"\b([A-ZÄÖÜ]) (?=[a-zäöü])", r"\1", r)
    if not r:
        return "sonstige ohne Fraktion"
    # Zuerst das Land prüfen: Landesminister aus Bayern, Sachsen, Hessen und
    # Rheinland-Pfalz heißen
    # "Staatsminister (Bayern)" und gehören zum Bundesrat, nicht zum Bund.
    if LAND_IN_KLAMMERN.search(r):
        return "Länder (Bundesrat)"
    if re.match(r"Bundeskanzler|Bundesminister", r):
        return "Bundesregierung (Kabinett)"
    if re.match(r"Parl\. Staatssekret|Staatsminister|Staatssekret|"
                r"(Beauftragte[rn]?|Koordinator(in)?) (der Bundesregierung|"
                r"des Bundesministeriums)", r):
        return "Bundesregierung (Staatssekretäre u. a.)"
    if re.match(r"Ministerpräsident|Minister|Senator|Bürgermeister", r):
        return "Länder (Bundesrat)"
    return "sonstige ohne Fraktion"


def normalisiere_fraktion(roh, rolle=None):
    f = re.sub(r"\s+", "", (roh or "")).upper()
    if not f:
        return ohne_fraktion(rolle)
    # Bei Vertretern der Länder steht gelegentlich das Bundesland im
    # Fraktionsfeld, z. B. "Bremen" beim Bremer Bürgermeister.
    if f in BUNDESLAENDER:
        return "Länder (Bundesrat)"
    if "GRÜNE" in f or f.startswith("BÜNDNIS"):
        return "Grüne"
    if f.startswith("CDU"):
        return "CDU/CSU"
    if f.startswith("SPD"):
        return "SPD"
    if "AFD" in f:
        return "AfD"
    if f.startswith("FDP"):
        return "FDP"
    if "LINKE" in f:
        return "Die Linke"
    if f == "BSW":
        return "BSW"
    if "FRAKTIONSLOS" in f:
        return "fraktionslos (Abgeordnete)"
    return "sonstige"


def reden(datei):
    """Liefert (wahlperiode, datum, redner, fraktion, text) je Rede."""
    wurzel = ET.parse(datei).getroot()
    wp = wurzel.get("wahlperiode")
    datum = wurzel.get("sitzung-datum")
    for rede in wurzel.iter("rede"):
        redner_el = rede.find(".//p[@klasse='redner']/redner")
        if redner_el is None:
            continue
        name = redner_el.find("name")
        person = " ".join(
            filter(None, (name.findtext("vorname"), name.findtext("nachname")))
        )
        rolle = name.findtext("rolle/rolle_lang")
        if not (rolle or "").strip():
            # Einzelne Protokolle führen das Amt nur im Text der Redner-Zeile,
            # z. B. "Carsten Schneider, Beauftragter der Bundesregierung ...:"
            zeile = rede.find("p[@klasse='redner']")
            if zeile is not None:
                txt = re.sub(r"\s+", " ", "".join(zeile.itertext())).strip().rstrip(":")
                if "," in txt:
                    rolle = txt.split(",", 1)[1].strip()
        fraktion = normalisiere_fraktion(name.findtext("fraktion"), rolle)

        teile, spricht_redner = [], True
        for kind in rede:
            if kind.tag == "name":  # Präsidium übernimmt das Wort
                spricht_redner = False
            elif kind.tag == "p" and kind.get("klasse") == "redner":
                spricht_redner = kind.find("redner") is not None and \
                    kind.find("redner").get("id") == redner_el.get("id")
            elif kind.tag == "p" and spricht_redner:
                teile.append("".join(kind.itertext()))
        yield wp, datum, person, fraktion, " ".join(teile)


def main():
    p = argparse.ArgumentParser(
        description="Zählt Begriffe in Bundestagsreden, aufgeschlüsselt nach Fraktion.",
        epilog='Mehrwörtige Begriffe in Anführungszeichen setzen. Ein '
               'Bindestrich im Begriff erlaubt an dieser Stelle auch ein '
               'Leerzeichen oder nichts: "Lieferketten-gesetz" findet ebenso '
               '"Lieferkettengesetz".')
    p.add_argument("begriffe", nargs="*", default=BEGRIFFE,
                   help=f"zu suchende Begriffe (Standard: {' '.join(BEGRIFFE)})")
    p.add_argument("--csv", default=AUSGABE,
                   help=f"Name der Ausgabedatei (Standard: {AUSGABE})")
    args = p.parse_args()
    muster = baue_muster(args.begriffe)

    print("Gesuchte Begriffe:", ", ".join(args.begriffe))
    print("Suchmuster:", muster.pattern, "\n")

    reden_gesamt = Counter()
    reden_mit_treffer = Counter()
    treffer_gesamt = Counter()
    pro_wp = defaultdict(Counter)
    fundstellen = []

    dateien = sorted(ORDNER.glob("*.xml"))
    if not dateien:
        raise SystemExit(f"Keine XML-Dateien in {ORDNER}. "
                         "Zuerst download_plenarprotokolle.R ausführen.")
    for datei in dateien:
        for wp, datum, person, fraktion, text in reden(datei):
            reden_gesamt[fraktion] += 1
            funde = list(muster.finditer(text))
            if not funde:
                continue
            reden_mit_treffer[fraktion] += 1
            treffer_gesamt[fraktion] += len(funde)
            pro_wp[wp][fraktion] += 1
            for m in funde:
                kontext = text[max(0, m.start() - 120): m.end() + 120]
                # Umbrüche und die im Protokollsatz vorkommenden
                # Leerzeichenketten zu je einem Leerzeichen zusammenziehen
                fundstellen.append([datei.name, wp, datum, person, fraktion,
                                    re.sub(r"\s+", " ", m.group(0)),
                                    re.sub(r"\s+", " ", kontext).strip()])

    print(f"{len(dateien)} Protokolle, {sum(reden_gesamt.values())} Reden ausgewertet\n")
    kopf = f"{'Fraktion':<42}{'Reden':>8}{'mit Treffer':>13}{'Anteil ‰':>10}{'Treffer':>9}"
    print(kopf)
    print("-" * len(kopf))
    for fraktion in sorted(reden_gesamt, key=lambda f: -reden_mit_treffer[f]):
        n, t = reden_gesamt[fraktion], reden_mit_treffer[fraktion]
        print(f"{fraktion:<42}{n:>8}{t:>13}{1000 * t / n:>10.1f}{treffer_gesamt[fraktion]:>9}")

    print("\nReden mit Treffer je Wahlperiode:")
    for wp in sorted(pro_wp):
        print(f"  WP {wp}: " + ", ".join(f"{f} {c}" for f, c in pro_wp[wp].most_common()))

    print("\nGefundene Wortformen:")
    if fundstellen:
        for wort, n in Counter(f[5] for f in fundstellen).most_common():
            print(f"  {wort}: {n}")
    else:
        print("  keine – passt das Suchmuster zu den Begriffen?")

    ziel = Path(__file__).parent / args.csv
    with open(ziel, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["Datei", "WP", "Datum", "Redner", "Fraktion", "Begriff", "Kontext"])
        w.writerows(fundstellen)
    print(f"\n{len(fundstellen)} Fundstellen gespeichert in {ziel.name}")


if __name__ == "__main__":
    main()
