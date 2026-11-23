#!/usr/bin/env python3
"""
Sorteer foto's per maand, haal dubbelen eruit en zet oldtimer-foto's
in een aparte map.

Hoe het werkt:
  1. Dubbelen (exact dezelfde inhoud) gaan naar de map 'Dubbelen'.
  2. Foto's waarop de AI een oldtimer herkent, gaan naar
     'Oldtimers/JJJJ-MM' (op fotodatum gerangschikt).
  3. Alle overige foto's gaan naar 'Gesorteerd/JJJJ-MM'.

De fotodatum komt uit de EXIF-data; als die ontbreekt wordt de
wijzigingsdatum van het bestand gebruikt.

Gebruik:
    python sorteer_fotos.py --bron "C:\\Fotos"
    python sorteer_fotos.py --bron "C:\\Fotos" --droog        (alleen bekijken)
    python sorteer_fotos.py --bron "C:\\Fotos" --uitvoeren    (echt verplaatsen)
"""

import argparse
import hashlib
import shutil
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image, ExifTags
except ImportError:
    print("Fout: de package 'pillow' ontbreekt. Installeer met:")
    print("    python -m pip install pillow pillow-heif")
    sys.exit(1)

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:
    pass

AFBEELDINGEN = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff", ".heic", ".heif"}
GESORTEERD = "Gesorteerd"
OLDTIMERS = "Oldtimers"
DUBBELEN = "Dubbelen"
ONBEKEND = "Onbekende-datum"

DATE_VELDEN = ("DateTimeOriginal", "DateTime", "DateTimeDigitized")

LABELS = [
    "an old vintage classic car, an oldtimer",
    "a modern new car",
    "a photo without any car in it",
]
OLDTIMER_INDEX = 0
OLDTIMER_DRUMPEL = 0.30


def vind_afbeeldingen(bron: Path) -> list[Path]:
    """Zoek alle afbeeldingen in de bronmap, zonder de uitvoermappen zelf."""
    uitgesloten = {GESORTEERD.lower(), OLDTIMERS.lower(), DUBBELEN.lower()}
    gevonden: list[Path] = []
    for pad in bron.rglob("*"):
        if not pad.is_file():
            continue
        if pad.suffix.lower() not in AFBEELDINGEN:
            continue
        tussenmappen = {d.lower() for d in pad.relative_to(bron).parts[:-1]}
        if tussenmappen & uitgesloten:
            continue
        gevonden.append(pad)
    return gevonden


def exif_datum(pad: Path) -> datetime | None:
    try:
        naam_naar_id = {naam: nummer for nummer, naam in ExifTags.TAGS.items()}
        with Image.open(pad) as im:
            exif = im.getexif()
        for veld in DATE_VELDEN:
            ruwe_waarde = exif.get(naam_naar_id.get(veld, -1))
            if not ruwe_waarde:
                continue
            try:
                return datetime.strptime(str(ruwe_waarde).strip()[:19], "%Y:%m:%d %H:%M:%S")
            except ValueError:
                continue
    except Exception:
        pass
    return None


def datum_van_foto(pad: Path) -> datetime:
    return exif_datum(pad) or datetime.fromtimestamp(pad.stat().st_mtime)


def maandmap(pad: Path) -> str:
    d = datum_van_foto(pad)
    if d.year <= 1980:
        return ONBEKEND
    return d.strftime("%Y-%m")


def file_sha256(pad: Path) -> str:
    h = hashlib.sha256()
    with pad.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verplaats(bron: Path, doel_bestand: Path, droog: bool, log: Counter) -> Path:
    """Verplaats (of toon in testmodus) een bestand; los naamconflicten op."""
    echt_doel = doel_bestand
    bestaat_al = None
    if doel_bestand.exists():
        if file_sha256(doel_bestand) == file_sha256(bron):
            bestaat_al = doel_bestand
        else:
            i = 2
            while True:
                kandidaat = doel_bestand.with_name(f"{doel_bestand.stem} ({i}){doel_bestand.suffix}")
                if not kandidaat.exists():
                    echt_doel = kandidaat
                    break
                if file_sha256(kandidaat) == file_sha256(bron):
                    bestaat_al = kandidaat
                    break
                i += 1
        if bestaat_al is not None:
            # exact dezelfde foto staat er al: bron is opnieuw een dubbele
            if droog:
                print(f"  [dubbel] {bron}  ->  zit al in '{bestaat_al}'")
            else:
                bron.unlink()
                print(f"  [dubbel] {bron}  ->  verwijderd (stond al als '{bestaat_al.name}')")
            log["dubbel"] += 1
            return bestaat_al
    if droog:
        print(f"  [{doel_bestand.parent.name}] {bron}  ->  {echt_doel}")
    else:
        echt_doel.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(bron), str(echt_doel))
    log["verplaatst"] += 1
    return echt_doel


def haal_dubbelen_eruit(alle: list[Path], doel: Path, droog: bool, log: Counter) -> list[Path]:
    print(f"\nStap 1/3: dubbelen zoeken ({len(alle)} bestanden)...")
    bekende_hashes: set[str] = set()
    dubbele_bestanden: set[Path] = set()
    for i, pad in enumerate(sorted(alle), start=1):
        try:
            h = file_sha256(pad)
        except OSError as e:
            print(f"  Kon {pad.name} niet lezen ({e}).")
            continue
        if h in bekende_hashes:
            dubbele_bestanden.add(pad)
            verplaats(pad, doel / DUBBELEN / pad.name, droog, log)
            log["dubbel"] += 1
        else:
            bekende_hashes.add(h)
        if i % 25 == 0:
            print(f"  {i}/{len(alle)} bestanden gecontroleerd...")
    print(f"  dubbele foto's gevonden: {len(dubbele_bestanden)}")
    return [p for p in alle if p not in dubbele_bestanden and p.exists()]


class Herkenner:
    def __init__(self, model, processor):
        self.model = model
        self.processor = processor
        self.model.eval()

    def is_oldtimer(self, pad: Path) -> bool:
        with Image.open(pad) as im:
            im = im.convert("RGB")
        inputs = self.processor(text=LABELS, images=im, return_tensors="pt", padding=True)
        import torch

        with torch.no_grad():
            uitvoer = self.model(**inputs)
        kansen = uitvoer.logits_per_image.softmax(dim=1)[0]
        return kansen.argmax().item() == OLDTIMER_INDEX and kansen[OLDTIMER_INDEX].item() >= OLDTIMER_DRUMPEL


def laad_herkenner() -> Herkenner | None:
    try:
        import torch
        from transformers import CLIPModel, CLIPProcessor
    except ImportError:
        print("\nLet op: de AI-packages zijn niet geinstalleerd. Oldtimers"
              " worden nu overgeslagen; alle foto's gaan naar 'Gesorteerd'.")
        print("Installeer ze met:")
        print("    python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu")
        print("    python -m pip install transformers")
        return None

    print("\nAI-model laden (de eerste keer wordt het model gedownload, ca. 600 MB)...")
    model_id = "openai/clip-vit-base-patch32"
    try:
        model = CLIPModel.from_pretrained(model_id)
        processor = CLIPProcessor.from_pretrained(model_id)
    except Exception as e:
        print(f"  AI-model kon niet worden geladen ({e}). Oldtimers worden overgeslagen.")
        return None
    return Herkenner(model, processor)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Foto's sorteren per maand, dubbelen eruit, oldtimers eruit."
    )
    parser.add_argument("--bron", required=True, help="Map met je foto's, bijv. C:\\Fotos")
    parser.add_argument("--doel", default=None, help="Waar de nieuwe mappen komen (standaard: in de bronmap)")
    groep = parser.add_mutually_exclusive_group()
    groep.add_argument("--droog", action="store_true", help="Alles tonen zonder iets te verplaatsen")
    groep.add_argument("--uitvoeren", action="store_true", help="Echt bestanden verplaatsen")
    args = parser.parse_args()

    bron = Path(args.bron).expanduser().resolve()
    if not bron.is_dir():
        print(f"Fout: map bestaat niet: {bron}")
        sys.exit(1)
    doel = Path(args.doel).resolve() if args.doel else bron
    droog = not args.uitvoeren

    alle = vind_afbeeldingen(bron)
    if not alle:
        print("Geen afbeeldingen gevonden in:", bron)
        sys.exit(0)
    print(f"Aantal afbeeldingen gevonden: {len(alle)}")
    if droog:
        print("TESTMODUS: er wordt niets verplaatst. Gebruik --uitvoeren om echt te starten.\n")

    tellers: Counter = Counter()

    over = haal_dubbelen_eruit(alle, doel, droog, tellers)

    over = [p for p in over if p.exists()]
    print(f"\nStap 2/3: oldtimers herkennen ({len(over)} foto's)...")
    herkenner = laad_herkenner() if over else None
    for i, pad in enumerate(over, start=1):
        maand = maandmap(pad)
        is_oldtimer = False
        if herkenner is not None:
            try:
                is_oldtimer = herkenner.is_oldtimer(pad)
            except Exception as e:
                print(f"  Kon {pad.name} niet als beeld lezen ({e}).")
        if is_oldtimer:
            doel_map = doel / OLDTIMERS / maand
            tellers["oldtimers"] += 1
        else:
            doel_map = doel / GESORTEERD / maand
            tellers["gesorteerd"] += 1
        verplaats(pad, doel_map / pad.name, droog, tellers)
        if i % 10 == 0 or i == len(over):
            print(f"  {i}/{len(over)} foto's verwerkt...")

    print("\nStap 3/3: overzicht")
    print(f"  dubbele foto's naar '{DUBBELEN}'      : {tellers['dubbel']}")
    print(f"  oldtimer-foto's naar '{OLDTIMERS}/JJJJ-MM': {tellers['oldtimers']}")
    print(f"  overige foto's naar '{GESORTEERD}/JJJJ-MM': {tellers['gesorteerd']}")
    if droog:
        print("TESTMODUS: er is NIET verplaatst. Voer het script opnieuw uit met --uitvoeren.")


if __name__ == "__main__":
    main()
