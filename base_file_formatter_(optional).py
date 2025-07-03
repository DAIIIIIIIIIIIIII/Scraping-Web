import csv

def clean_and_fix_csv(file_path):
    with open(file_path, 'r', newline='', encoding='utf-8') as infile:
        lines = infile.readlines()

    fixed_rows = []
    temp_row = []
    semicolon_count = 0

    for line in lines:
        line = line.replace('"', '').strip()  # Rimuove i doppi apici e spazi ai lati
        line = ';'.join([cell.strip() for cell in line.split(';')])  # Rimuove gli spazi tra i `;`
        line = line.replace('; ;', ';;')  # Elimina gli spazi vuoti tra i `;`
        temp_row.append(line)
        semicolon_count += line.count(';')

        if semicolon_count >= 8:  # Quando si raggiungono almeno 8 ";" si salva la riga
            fixed_rows.append(' '.join(temp_row))  # Unisce tutto in un'unica riga
            temp_row = []  # Resetta per la prossima riga
            semicolon_count = 0

    with open(file_path, 'w', newline='', encoding='utf-8') as outfile:
        outfile.write('\n'.join(fixed_rows) + '\n')  # Scrive tutto nel file, con le righe corrette

# Usa il file caricato
file_path = "elenco-completo.csv"

clean_and_fix_csv(file_path)

print("File corretto e formattato con successo!")
