# Je foto's sorteren per maand, dubbelen eruit, oldtimers apart

## Wat doet dit programma

1. **Dubbelen eraf**: foto's die exact hetzelfde bestand zijn, gaan naar de map `Dubbelen`.
2. **Oldtimers apart**: foto's waarop de AI een *oudere klassieke auto (oldtimer)* herkent,
   gaan naar `Oldtimers\JJJJ-MM` (dus ook per maand, op fotodatum).
3. **Alles per maand**: alle overige foto's gaan naar `Gesorteerd\JJJJ-MM`, bijvoorbeeld
   `Gesorteerd\2023-05`.

De maand komt uit de **fotodatum in de EXIF-data** (de datum waarop de foto is gemaakt).
Ontbreekt die, dan wordt de wijzigingsdatum van het bestand gebruikt.

Er wordt **niets verwijderd**: alleen verplaatst (dubbelen gaan naar de map `Dubbelen`,
die kun je daarna zelf controleren en met een gerust hart weggooien).

## Benodigd (eenmalig)

- **Python** voor Windows: download van https://www.python.org/downloads/
  en vink bij de installatie **"Add Python to PATH"** aan.
- Internetverbinding bij de eerste keer starten (packages + AI-model, ca. 600 MB,
  daarna werkt alles volledig offline).

Opmerking: HEIC-foto's (iPhone) worden ondersteund. Video's worden niet verplaatst.

## Gebruik

1. Zet `fotos_sorteren.bat` en `sorteer_fotos.py` samen in één map, bijv. `C:\Fotoprogramma`.
2. Dubbelklik op **`fotos_sorteren.bat`**.
3. Sleep de map met je foto's in het zwarte venster en druk op Enter.
4. Antwoord **j** als je eerst wilt zien wat er gaat gebeuren (er wordt dan niets verplaatst),
   of **n** om meteen echt te sorteren.

### Vanaf de opdrachtprompt (gevorderd)

```
python sorteer_fotos.py --bron "C:\Fotos" --droog        :: alleen bekijken
python sorteer_fotos.py --bron "C:\Fotos" --uitvoeren    :: echt verplaatsen
python sorteer_fotos.py --bron "C:\Fotos" --doel "D:\Gesorteerd" --uitvoeren
```

## Eindresultaat (voorbeeld)

```
C:\Fotos\
├── Dubbelen\            <- dubbele foto's (zelf weggooien)
├── Gesorteerd\
│   ├── 2022-08\
│   ├── 2022-09\
│   └── 2023-05\
└── Oldtimers\
    ├── 2022-08\        <- oldtimer-foto's, ook per maand
    └── 2023-05\
```

## Tips

- **Test eerst met `j`** (alleen bekijken). Sta in de lijst de verplaatsingen toe
  die je verwacht, en kies daarna **n** om ze echt uit te voeren.
- De AI-herkenning (CLIP) werkt het best op duidelijke foto's. Slaat de AI
  een oldtimer over, dan belandt de foto gewoon in `Gesorteerd` — je kunt hem
  daarna zelf verslepen naar `Oldtimers`.
- De AI-detectie kun je ook overslaan: voer het script uit terwijl de AI-packages
  (torch, transformers) niet geïnstalleerd zijn. Alle foto's gaan dan naar
  `Gesorteerd\JJJJ-MM` en je kunt oldtimers daarna zelf verslepen naar `Oldtimers`.
