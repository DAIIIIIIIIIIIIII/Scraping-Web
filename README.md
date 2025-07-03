This is a smart Python-based tool that automates the process of finding company websites and extracting key business information — starting from a simple CSV file.
🔍 How it works

Just feed the program a CSV file containing company names or product categories. It will:

    Parse the file row-by-row to read company names.

    Launch a browser session using Selenium and ChromeDriver.

    Automatically perform web searches for each company.

    Match and identify the most relevant official website using a custom-built filtering and matching system.

    (Optional) Extract useful data from the found websites.

🤖 Key Features

    Fully automated search and data gathering

    Intelligent matching algorithm to reduce false positives

    Easy CSV input/output

    Modular and customizable architecture

🚀 Ideal for:

    Market research

    Lead generation

    Business intelligence

    Sourcing and supplier discovery

The input CSV must follow a strict format, with ; as the delimiter. Each line represents one company and should look like:

    76;SEDE;SOCIETA' AGRICOLA AMC S.R.L.;VIA GIUSEPPE GARIBALDI 12; ;33070;CANEVA - PN; ;

With the following header:

    N:;SEDE;Nome legale;Via;CAP;Comune;Frazione;;Sito web

If you're using an official registry file (e.g. legally purchased from a chamber of commerce), just specify the correct CSV file using the optional input parameter — the tool will handle the rest.
