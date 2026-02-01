from pathlib import Path
text = Path('D:/i18Token/Beispiel_Programm_Python/game.py').read_text().splitlines()
for i,line in enumerate(text,1):
    if '000Q' in line:
        print(i, line)
