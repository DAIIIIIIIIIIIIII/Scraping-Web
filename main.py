import csv
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import re
import difflib
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, WebDriverException, NoSuchElementException
from sentence_transformers import SentenceTransformer, util
from fuzzywuzzy import fuzz
from rapidfuzz import fuzz
import re


model = SentenceTransformer('all-MiniLM-L6-v2')

# Percorso del file CSV
csv_file_path = r"E:\Scraping web merceologico\elenco-completo.csv"
output_csv_file_path = r"E:\Scraping web merceologico\elenco_siti.csv"

# Intestazione corretta del file
correct_header = ['N:', 'SEDE','Nome legale', 'Via', 'CAP', 'Comune', 'Frazione','', 'Sito web']

# Verifica se il file CSV esiste e aggiorna l'intestazione se necessario
if os.path.exists(csv_file_path):
    with open(csv_file_path, mode="r", newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        rows = list(reader)
        header = rows[0] if rows else []
        if header != correct_header:  # Controlla se l'intestazione è diversa da quella corretta
            rows.insert(0, correct_header)  # Inserisci l'intestazione corretta
    with open(csv_file_path, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerows(rows)

# Verifica se il file di output esiste e inizializzalo se necessario
if not os.path.exists(output_csv_file_path) or os.stat(output_csv_file_path).st_size == 0:
    with open(output_csv_file_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        # Scrivi l'intestazione nel file CSV
        writer.writerow(['N:', 'SEDE', 'Nome Legale', 'Sito', 'via', '', 'CAP', 'Comune', 'Frazione', '', 'Email'])

# Configura il driver di Selenium
options = webdriver.ChromeOptions()
options.page_load_strategy = 'eager'  # Carica la pagina più velocemente
driver = webdriver.Chrome(options=options)
driver.set_page_load_timeout(30)  # Imposta un timeout di 30 secondi

# Funzione per estrarre il dominio da un URL
def extract_domain(url):
    match = re.search(r"https?://(www\.)?([^/]+)", url)
    if match:
        full_domain = match.group(2)
        # Rimuovi prefissi e suffissi indesiderati
        clean_domain = re.sub(r"^(www|ww2)\.", "", full_domain, flags=re.IGNORECASE)  # Rimuove "www" o "ww2"
        clean_domain = re.sub(r"\.(it|com|eu|net|org|info|biz|gov|edu)$", "", clean_domain, flags=re.IGNORECASE)  # Rimuove suffissi
        return full_domain, clean_domain
    return None, None

# Funzione per rimuovere parole specifiche dal contenuto della cella
def clean_cell_content(content):
    words_to_remove = ["SOC.", "SEMPLICE", "S.S.", "S.R.L.", "AZIENDA", "C. S.S.", "C.S.S.", "C.S.", "SRL", "SNC", "SAS", "SPA", "S.A.", "S.A.S.", "S.A.P.A.", "S.A.P.", "S.A.P.A", "S.A.", "srl", "snc", "sas", "spa", "s.a.", "s.a.s.", "s.a.p.a.", "s.a.p.", "s.a.p.a", "s.a.", "css"]
    for word in words_to_remove:
        content = content.replace(word, "")
    return content.strip()

# Funzione per pulire il contenuto della cella per il confronto
def clean_for_comparison(content):
    # Lista aggiornata di parole da rimuovere
    words_to_remove = [
        "soc", "semplice", "s.s.", "s.r.l.", "azienda", "wordpress",
        "c. s.s.", "c.s.s.", "c.s.", "srl", "snc", "sas", "spa", "s.a.", "s.a.s.",
        "s.a.p.a.", "s.a.p.", "s.a.p.a", "s.a.", "css", "agricola", "di", "e", "c s s", "s r l", "&", "c."
    ]
    # Rimuovi caratteri speciali
    content = re.sub(r"[&'.,-]", ' ', content)  # Sostituisce &, ', ., , - con spazi
    # Rimuovi ogni parola dalla lista
    for word in words_to_remove:
        content = re.sub(r'\b' + re.escape(word) + r'\b', '', content, flags=re.IGNORECASE)
    # Rimuovi spazi multipli
    content = re.sub(r"\s+", ' ', content).strip()  # Rimuove spazi multipli e spazi iniziali/finali
    return content.lower()  # Converte in minuscolo

# Funzione per verificare se il dominio è rilevante
def is_relevant_domain(domain, keywords):
    for keyword in keywords:
        if keyword in domain:
            return True
    return False

# Funzione per estrarre email e numeri di telefono da una pagina web
def format_phone_number(phone):
    """
    Formatta il numero di telefono nel formato xxxx xxxxxx o +39 xxxx xxxxxx se non è internazionale.
    """
    # Rimuovi tutto ciò che non è un numero, inclusi spazi, parentesi e altri caratteri
    phone_digits = re.sub(r'\D', '', phone)
    
    # Aggiungi il prefisso +39 solo se il numero non inizia con un + o 00 (per numeri esteri)
    if not phone_digits.startswith(('39', '00', '+')):
        phone_digits = '39' + phone_digits
    
    # Format del numero: +39 xxxx xxxxxx
    formatted_phone = f"+{phone_digits[:2]} {phone_digits[2:6]} {phone_digits[6:]}"

    return formatted_phone

def extract_contact_info(driver):
    page_source = driver.page_source
    
    # Estrae le email
    emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", page_source)
    
    # Estrae i numeri di telefono, considerando le condizioni specifiche
    phones = re.findall(r"(?:tel\.|Tel|Telefono|\+39|0\d{2,4})[\s:;,\-\/]*\(?\d{2,4}\)?[\s:;,\-\/]*\d{6,10}", page_source)
    
    # Filtra e formatta i numeri di telefono, mantenendo solo quelli con almeno 10 cifre
    phones = [format_phone_number(phone) for phone in phones if len(re.sub(r'\D', '', phone)) >= 10]
    
    # Rimuove duplicati
    emails = list(set(emails))
    phones = list(set(phones))

    return emails, phones

# Funzione per estrarre email da una pagina web
def extract_emails_from_page(driver):
    page_source = driver.page_source
    emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", page_source)
    return list(set(emails))  # Rimuove duplicati

# Blacklist dei domini da ignorare
blacklist = ["informazione-aziende.it", "empresite.it", "ufficiocamerale.it", "italy.globaldatabase.com", "fiscoetasse.com", "regione.fvg.it", "dnb.com", "reteimprese.it", "companyreports.it", "visurissima.it", "aziendeeasy.it", "fatturatoitalia.it", "reportaziende.it", "paginegialle.it", "reportazienda.it", "coobiz.it", "aziende.virgilio.it", "cylex-italia.it", "registroaziende.it", "bilancioaziende.com", "atoka.io", "facebook.com", "paginebianche.it"]















def enhanced_similarity_ratio(domain, company_name, description=""):
    # Costanti e set
    SECTOR_TLDS = {'wine', 'vin', 'vino', 'agriculture', 'farm'}
    NEGATIVE_KEYWORDS = {'pentole', 'cybersecurity', 'abbigliamento', 'arredamento', 'elettrodomestici'}
    SECTOR_KEYWORDS = {'vino', 'cantina', 'vitigno', 'uvaggio', 'botte', 'vendemmia', 'azienda', 'agricola'}

    domain_lower = domain.lower()
    desc_lower = description.lower()

    # 1. Esclusione per keyword negative
    if any(nk in domain_lower or nk in desc_lower for nk in NEGATIVE_KEYWORDS):
        return 0.0

    # 2. TLD boost (finto, simulato: lo puoi passare a parte se vuoi)
    tld_bonus = 0.3 if domain.split('.')[-1] in SECTOR_TLDS else 0

    # 3. Normalizza e calcola match stringa
    clean_name = re.sub(r'\W+', '', company_name.lower())
    clean_domain = re.sub(r'\W+', '', domain_lower)
    
    partial = fuzz.partial_ratio(clean_name, clean_domain) / 100
    token_sort = fuzz.token_sort_ratio(clean_name, clean_domain) / 100
    combined_fuzz = (0.6 * partial + 0.4 * token_sort)

    # 4. Match settore nella descrizione
    sector_match = sum(kw in desc_lower for kw in SECTOR_KEYWORDS)
    has_sector_words = sector_match >= 2

    # 5. Score grezzo
    score = (
        0.6 * combined_fuzz +
        0.2 * has_sector_words +
        tld_bonus
    )

    # Penalità se molto poco match
    if combined_fuzz < 0.3:
        score *= 0.5

    return round(max(0.0, min(1.0, score)), 3)









'''
def enhanced_similarity_ratio(domain, company_name, description=""):
    # Configurazioni
    SECTOR_TLDS = {'wine', 'vin', 'vino', 'agriculture', 'farm'}
    NEGATIVE_KEYWORDS = {'pentole', 'cybersecurity', 'abbigliamento', 'arredamento', 'elettrodomestici'}
    SECTOR_KEYWORDS = {'vino', 'cantina', 'vitigno', 'uvaggio', 'botte', 'vendemmia'}
    
    # 1. Controllo eliminazioni immediate
    domain_lower = domain.lower()
    if any(nk in domain_lower or nk in description.lower() for nk in NEGATIVE_KEYWORDS):
        return 0.0
    
    # 2. Analisi TLD
    tld = domain.split('.')[-1].lower()
    tld_bonus = 0.3 if tld in SECTOR_TLDS else (-0.1 if tld == 'com' else 0)
    
    # 3. Match esatto o parziale
    exact_match = 1.0 if company_name == domain else 0
    partial_ratio = fuzz.partial_ratio(company_name, domain) / 100
    
    # 4. Contenuto settoriale nella descrizione
    desc_words = description.lower().split()
    sector_match = sum(1 for kw in SECTOR_KEYWORDS if kw in desc_words)
    sector_density = sector_match / (len(desc_words) + 1e-6)  # Evita divisione per zero
    
    # 5. Similarità semantica solo se necessario
    semantic_sim = 0
    if partial_ratio > 0.4 or exact_match:
        emb_company = model.encode(company_name, convert_to_tensor=True)
        emb_domain = model.encode(domain, convert_to_tensor=True)
        semantic_sim = util.cos_sim(emb_company, emb_domain).item()
    
    # 6. Calcolo finale
    score = (
        0.4 * exact_match +
        0.3 * partial_ratio +
        0.2 * semantic_sim +
        0.1 * min(1.0, sector_density * 5) +
        tld_bonus
    )
    
    # 7. Penalità finale per domini non settoriali
    if sector_density < 0.05 and tld not in SECTOR_TLDS:
        score *= 0.5
        
    return max(0.0, min(1.0, score))
'''







'''
Funziona meglio della precedente ma è molto più lenta. Evita ancora molti link uguali e tiene poco conto della descrizione sopratutto quando il sito non è per niente
pertinente con l'attività che sto cercando.


Azienda: SOCIETA'  AGRICOLA FRATELLI PIN
Dominio1: fratelliurbani.com   -> Similarità: 0.44              (giusto)
Dominio2: altalex.com   -> Similarità: 0.18
Dominio3: parmigianoreggiano.com   -> Similarità: 0.18


Azienda: SOCIETA' AGRICOLA AMC
Dominio1: amc.info   -> Similarità: 0.69                        (sbagliato)
Dominio2: it.amc.info   -> Similarità: 0.18
Dominio3: it.kompass.com   -> Similarità: 0.08
Dominio4: registroimprese.it   -> Similarità: 0.00
Dominio5: aziende.it   -> Similarità: 0.00


Azienda: SOCIETA' AGRICOLA BAZZO GIANLUCA & C.
Dominio1: bazzo.wine   -> Similarità: 0.59                      (giusto)    
Dominio2: tenutabazzo.it   -> Similarità: 0.35
Dominio3: viniaigiardini.com   -> Similarità: 0.34


Azienda: SOCIETA' AGRICOLA RIVE COL DE FER -
Dominio1: rivecoldefer.com   -> Similarità: 0.43                (evitato)
Dominio2: trova-aperto.it   -> Similarità: 0.29
Dominio3: somewherefvg.it   -> Similarità: 0.26
Dominio4: vinievino.it   -> Similarità: 0.24
Dominio5: turismofvg.it   -> Similarità: 0.00


Azienda: ARCA24 SOCIETA'  AGRICOLA
Dominio1: arca24.com   -> Similarità: 0.75                      (sbagliato)   
Dominio2: arcafondi.it   -> Similarità: 0.48
Dominio3: portale-arca.it   -> Similarità: 0.41
Dominio4: www2.arca24.com   -> Similarità: 0.25
Dominio5: crm.arca24.careers   -> Similarità: 0.24


Azienda: AGRICOLA ROSA LORIS DI ROSA SONNY
Dominio1: agricoladirosa.it   -> Similarità: 0.24               (evitato)
Dominio2: aziendagricolarosapepe.com   -> Similarità: 0.21
Dominio3: asprom.it   -> Similarità: 0.16
Dominio4: l-agricola.com   -> Similarità: 0.16
Dominio5: visitsoglianoalrubicone.it   -> Similarità: 0.12
Dominio6: regione.lombardia.it   -> Similarità: 0.11
Dominio7: agricolashop.it   -> Similarità: 0.00


Azienda: DORIGO ROLANDO SOCIETA' AGRICOLA
Dominio1: dorigowines.com   -> Similarità: 0.46                 (evitato)
Dominio2: darolando.it   -> Similarità: 0.46
Dominio3: opencorpdata.com   -> Similarità: 0.26


Azienda: FANTIN GIANNI E DIEGO
Dominio1: fantin.com   -> Similarità: 0.48                      (giusto)            
Dominio2: fantinargenti.it   -> Similarità: 0.42
Dominio3: greenpea.com   -> Similarità: 0.21


def enhanced_similarity_ratio(domain, company_name, description=""):
    # Modello più adatto per confronti frase-breve
    model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
    
    # Liste di esclusione per domini generici
    generic_domain_parts = ['shop', 'aziende', 'registroimprese', 'turismofvg']
    
    # Parole da rimuovere dal nome azienda
    stop_words = {"societa'", "societa", "agricola", "srl", "ss", "di", "e", "&", "c.", "c"}
    
    # Pulizia avanzata del nome aziendale
    def clean_company_name(text):
        text = re.sub(r"[^a-z0-9&']", ' ', text.lower())
        words = [word for word in text.split() if word not in stop_words]
        return ' '.join(words)
    
    # Controllo dominio generico
    if any(part in domain for part in generic_domain_parts):
        return 0.0
    
    # Estrai componente principale del dominio
    domain_part = domain.split('.')[0]
    
    # Fuzzy match tra nome azienda e dominio
    clean_company = clean_company_name(company_name)
    name_ratio = fuzz.token_set_ratio(clean_company, domain_part) / 100
    
    # Similarità semantica con solo dominio
    emb_company = model.encode(clean_company, convert_to_tensor=True)
    emb_domain = model.encode(domain_part, convert_to_tensor=True)
    domain_sim = util.cos_sim(emb_company, emb_domain).item()
    
    # Combinazione ponderata
    semantic_score = 0.7 * domain_sim + 0.3 * name_ratio
    
    # Analisi descrizione (se presente)
    if description:
        # Similarità semantica con descrizione
        emb_desc = model.encode(description, convert_to_tensor=True)
        desc_sim = util.cos_sim(emb_company, emb_desc).item()
        
        # Controllo parole chiave settoriali
        settore_keywords = {"vino", "cantina", "vinificazione", "viticoltura"}
        found_keywords = len(settore_keywords & set(description.lower().split()))
        keyword_bonus = min(0.2, found_keywords * 0.05)
        
        # Peso complessivo
        final_score = 0.6 * semantic_score + 0.3 * desc_sim + keyword_bonus
    else:
        final_score = semantic_score
    
    return max(0.0, min(1.0, final_score))
    '''

















# Trova la riga di ripartenza se elenco_siti.csv contiene già dati
start_index = 0
last_company_name = None

if os.path.exists(output_csv_file_path) and os.stat(output_csv_file_path).st_size > 0:
    with open(output_csv_file_path, mode="r", encoding="utf-8") as outcsv:
        out_reader = list(csv.reader(outcsv, delimiter=';'))
        if len(out_reader) > 1:
            last_row = out_reader[-1]
            # Adatta l'indice qui se la colonna del nome azienda è diversa
            last_company_name = last_row[2].strip() if len(last_row) > 2 else None

if last_company_name:
    with open(csv_file_path, mode="r", encoding="utf-8") as incsv:
        in_reader = list(csv.reader(incsv, delimiter=';'))
        # Cerca la riga con il nome azienda uguale
        for idx, row in enumerate(in_reader):
            if len(row) > 2 and row[2].strip() == last_company_name:
                start_index = idx + 1  # Riparti dalla riga successiva
                break

# Apri il file CSV originale in lettura e il file di output in modalità append
with open(csv_file_path, newline='') as csvfile, \
     open(output_csv_file_path, 'a', newline='') as output_csvfile:  # 'a' per append

    reader = csv.reader(csvfile, delimiter=';')
    writer = csv.writer(output_csvfile, delimiter=';')

    # Salta la riga di intestazione
    header = next(reader, None)

    # Salta le righe già processate
    for _ in range(start_index - 1):  # -1 perché abbiamo già saltato l'header
        next(reader, None)

    # Mantieni un set per tracciare le righe già scritte
    written_rows = set()

    # Itera sulle righe del file elenco-completo.csv
    for row in reader:
        # Rimuovi eventuali spazi bianchi e controlla se la riga è vuota
        row = [cell.strip() for cell in row]
        if len(row) > 2 and row[2]:  # Assicurati che la riga abbia almeno tre colonne e che la colonna C non sia vuota
            cell_content = row[2]  # Colonna C (indice 2)
            cleaned_content = clean_cell_content(cell_content)
            comparison_content = clean_for_comparison(cell_content)

            # Crea la query di ricerca
            search_query = f"{cleaned_content} sito ufficiale"

            # Naviga su DuckDuckGo
            driver.get("https://www.duckduckgo.com")

            # Trova la barra di ricerca e inserisci il testo
            try:
                search_box = driver.find_element(By.NAME, "q")
                search_box.send_keys(search_query)
                search_box.send_keys(Keys.RETURN)
            except NoSuchElementException:
                print("Elemento di ricerca non trovato su DuckDuckGo.")
                row.append("NO")  # Aggiungi "NO" alla riga
                continue  # Passa alla prossima iterazione del ciclo

            # Attendi qualche secondo per vedere i risultati
            time.sleep(4)

            # Stampa il nome dell'azienda e i domini validi con la similarità
            print(f"\nAzienda: {cleaned_content}")

            # Estrai i link e le descrizioni dai risultati di ricerca
            links = driver.find_elements(By.CSS_SELECTOR, "a[data-testid='result-title-a']")
            # Modifica: seleziona le descrizioni usando il nuovo selettore
            descriptions = driver.find_elements(By.CSS_SELECTOR, "div[data-result='snippet'] span span")

            valid_links = []
            valid_descriptions = []
            seen_domains = set()  # Per tenere traccia dei domini già visti
            max_valid_links = 10  # Numero massimo di link validi da raccogliere

            for idx, link in enumerate(links):
                if len(valid_links) >= max_valid_links:
                    break  # Interrompi il ciclo se hai già trovato il numero massimo di link validi

                url = link.get_attribute("href")
                full_domain, clean_domain = extract_domain(url)  # Ottieni sia il dominio completo che quello pulito

                # Estrai la descrizione associata (se esiste)
                description = ""
                if idx < len(descriptions):
                    description = descriptions[idx].text.strip()

                # Controlla se il dominio è nella blacklist
                if full_domain and clean_domain and full_domain not in blacklist and clean_domain not in blacklist and clean_domain not in seen_domains:
                    seen_domains.add(clean_domain)  # Aggiungi il dominio pulito ai domini già visti
                    # Passa anche la descrizione a enhanced_similarity_ratio
                    similarity = enhanced_similarity_ratio(clean_domain, comparison_content, description)
                    valid_links.append((url, full_domain, similarity))
                    valid_descriptions.append(description)
                else:
                    continue

            # Ora valid_links[i] corrisponde a valid_descriptions[i] per ogni risultato valido

            # Ordina i link trovati in base alla similarità in ordine decrescente (e ordina anche le descrizioni di conseguenza)
            sorted_results = sorted(zip(valid_links, valid_descriptions), key=lambda x: x[0][2], reverse=True)
            valid_links = [item[0] for item in sorted_results]
            valid_descriptions = [item[1] for item in sorted_results]

            # Mostra i domini trovati, la similarità e la descrizione
            for i, ((url, full_domain, similarity), description) in enumerate(zip(valid_links, valid_descriptions), start=1):
                print(f"Dominio{i}: {full_domain}   -> Similarità: {similarity:.2f}")

            try:
                # Scrivi solo se si trova almeno una email
                email_found = False
                if valid_links and valid_links[0][2] >= 0.45:
                    best_link = valid_links[0][0]
                    try:
                        print(f"\nEntrando su: {best_link}\n")
                        driver.get(best_link)
                        time.sleep(4)
                        print("\nCercando email nella pagina principale...")
                        emails = extract_emails_from_page(driver)
                        if emails:
                            emails_to_write = ", ".join(emails[:4]) + " /////" if len(emails) > 4 else ", ".join(emails)
                            print(f"\nEmail trovate nella pagina principale: {emails_to_write}")
                            row.append(emails_to_write)
                            email_found = True
                        else:
                            print("Nessuna email trovata nella pagina principale.")
                            row.append("")

                        print("\nEntrando sui contatti...")
                        contact_links = driver.find_elements(By.TAG_NAME, "a")
                        contact_page_found = False
                        _, main_clean_domain = extract_domain(best_link)

                        for contact_link in contact_links:
                            contact_url = contact_link.get_attribute("href")
                            if contact_url and any(keyword in contact_url.lower() for keyword in ["contatti", "contattaci", "contact", "info", "about", "dove siamo", "dove"]):
                                _, contact_clean_domain = extract_domain(contact_url)
                                if contact_clean_domain and contact_clean_domain == main_clean_domain:
                                    print(f"Pagina dei contatti trovata: {contact_url}")
                                    try:
                                        driver.get(contact_url)
                                        time.sleep(4)
                                        emails = extract_emails_from_page(driver)
                                        if emails:
                                            emails_to_write = ", ".join(emails[:4]) + " /////" if len(emails) > 4 else ", ".join(emails)
                                            print(f"\nEmail trovate nella pagina dei contatti: {emails_to_write}")
                                            row.append(emails_to_write)
                                            email_found = True
                                        else:
                                            print("Nessuna email trovata nella pagina dei contatti.")
                                            row.append("")
                                        contact_page_found = True
                                        break
                                    except TimeoutException:
                                        print(f"Timeout durante il caricamento della pagina dei contatti per {cell_content}.")
                                        row.append("Errore durante la scansione")
                                else:
                                    print(f"Link contatti ignorato (dominio diverso): {contact_url}")
                        if not contact_page_found:
                            print("Nessuna pagina dei contatti trovata.")
                            row.append("")

                        # Scrivi la riga aggiornata nel file elenco_siti.csv solo se non è già stata scritta e c'è almeno una email
                        row_tuple = tuple(row + [best_link])
                        if email_found and row_tuple not in written_rows:
                            writer.writerow(row + [best_link])
                            written_rows.add(row_tuple)

                    except TimeoutException:
                        print(f"Timeout durante il caricamento del sito: {best_link}")
                    except Exception as e:
                        print(f"Errore generico durante l'accesso al sito: {e}")
                else:
                    print("\nNessun link valido trovato per questa azienda. Non verrà scritto nel file elenco_siti.csv.")

                # Scrivi la riga nel file di output solo se c'è almeno una email trovata
                if email_found:
                    writer.writerow(row)
            except TimeoutException:
                print(f"Timeout durante il caricamento del sito per {cell_content}.")
                row.append("Errore durante la scansione")
            except Exception as e:
                print(f"Errore generico: {e}")
                row.append("Errore generico")
            # Non scrivere la riga se non c'è email
        else:
            print("\nRiga non valida trovata e saltata:", row)
            row.append("NO")
        # Non scrivere la riga se non c'è email

# Chiudi il browser
driver.quit()

# Rimuovi i duplicati dal file di output basandoti sulla colonna 3 (indice 2)
with open(output_csv_file_path, mode="r", newline="", encoding="utf-8") as csvfile:
    reader = list(csv.reader(csvfile, delimiter=';'))
    header = reader[0]  # Intestazione
    rows = reader[1:]   # Dati

# Usa un set per tenere traccia dei valori unici nella colonna 3
unique_rows = []
seen_values = set()

for row in rows:
    if len(row) > 2 and any(cell.strip() for cell in row):  # Assicurati che la riga abbia almeno 3 colonne e non sia vuota
        value = row[2].strip()  # Colonna 3 (indice 2)
        if value not in seen_values:
            seen_values.add(value)
            unique_rows.append(row)

# Sovrascrivi il file con le righe uniche
with open(output_csv_file_path, mode="w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile, delimiter=';')
    writer.writerow(header)  # Scrivi l'intestazione
    writer.writerows(unique_rows)

print(f"Duplicati rimossi dal file: {output_csv_file_path}")

# Aggiungi una numerazione crescente nella prima colonna del file di output
with open(output_csv_file_path, mode="r", newline="", encoding="utf-8") as csvfile:
    reader = list(csv.reader(csvfile, delimiter=';'))
    header = reader[0]  # Intestazione
    rows = reader[1:]   # Dati

# Aggiungi numerazione crescente
with open(output_csv_file_path, mode="w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile, delimiter=';')
    writer.writerow(header)  # Scrivi l'intestazione
    for index, row in enumerate(rows, start=1):
        if any(cell.strip() for cell in row):  # Assicurati che la riga non sia vuota
            row[0] = index  # Sovrascrivi la prima colonna con il numero crescente
            writer.writerow(row)

print(f"Numerazione crescente aggiunta nella prima colonna del file: {output_csv_file_path}")