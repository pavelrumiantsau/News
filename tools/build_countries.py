#!/usr/bin/env python3
"""Generates config/countries.json from the compact table below.

Edit TABLE, re-run `python3 tools/build_countries.py`, commit the JSON.

Columns, pipe-separated:
    iso2 | name | capital | demonym | bloc | extra search terms (semicolon-separated)

`bloc` selects which regional publisher set gets added to that country's
allowlist (see config/sources.json -> bloc_domains).

The extra terms matter a lot: they are what lets the relevance filter accept a
headline that names a city or a conflict zone but never the country itself
("Strike on Odesa port" is Ukraine news; "Fighting in Goma" is DR Congo news).
"""

import json
import os

TABLE = """
# ---------------------------------------------------------------- AFRICA
DZ|Algeria|Algiers|Algerian|africa_n|
AO|Angola|Luanda|Angolan|africa_s|
BJ|Benin|Porto-Novo|Beninese|africa_w|Cotonou
BW|Botswana|Gaborone|Motswana|africa_s|Batswana
BF|Burkina Faso|Ouagadougou|Burkinabe|africa_w|Burkinabè
BI|Burundi|Gitega|Burundian|africa_e|Bujumbura
CV|Cabo Verde|Praia|Cape Verdean|africa_w|Cape Verde
CM|Cameroon|Yaounde|Cameroonian|africa_w|Yaoundé;Douala;Ambazonia
CF|Central African Republic|Bangui|Central African|africa_w|
TD|Chad|N'Djamena|Chadian|africa_w|Ndjamena
KM|Comoros|Moroni|Comorian|africa_e|
CG|Republic of the Congo|Brazzaville|Congolese|africa_w|Congo-Brazzaville
CD|DR Congo|Kinshasa|Congolese|africa_e|DRC;Democratic Republic of the Congo;Goma;Kivu;M23
CI|Ivory Coast|Yamoussoukro|Ivorian|africa_w|Côte d'Ivoire;Cote d'Ivoire;Abidjan
DJ|Djibouti|Djibouti|Djiboutian|africa_e|
EG|Egypt|Cairo|Egyptian|africa_n|Sisi
GQ|Equatorial Guinea|Malabo|Equatoguinean|africa_w|
ER|Eritrea|Asmara|Eritrean|africa_e|
SZ|Eswatini|Mbabane|Swazi|africa_s|Swaziland
ET|Ethiopia|Addis Ababa|Ethiopian|africa_e|Tigray;Amhara;Oromia
GA|Gabon|Libreville|Gabonese|africa_w|
GM|Gambia|Banjul|Gambian|africa_w|
GH|Ghana|Accra|Ghanaian|africa_w|
GN|Guinea|Conakry|Guinean|africa_w|
GW|Guinea-Bissau|Bissau|Bissau-Guinean|africa_w|
KE|Kenya|Nairobi|Kenyan|africa_e|Ruto
LS|Lesotho|Maseru|Basotho|africa_s|Lesotho
LR|Liberia|Monrovia|Liberian|africa_w|
LY|Libya|Tripoli|Libyan|africa_n|Benghazi;Haftar
MG|Madagascar|Antananarivo|Malagasy|africa_e|
MW|Malawi|Lilongwe|Malawian|africa_s|
ML|Mali|Bamako|Malian|africa_w|Azawad
MR|Mauritania|Nouakchott|Mauritanian|africa_w|
MU|Mauritius|Port Louis|Mauritian|africa_e|
MA|Morocco|Rabat|Moroccan|africa_n|Casablanca;Western Sahara
MZ|Mozambique|Maputo|Mozambican|africa_s|Cabo Delgado
NA|Namibia|Windhoek|Namibian|africa_s|
NE|Niger|Niamey|Nigerien|africa_w|
NG|Nigeria|Abuja|Nigerian|africa_w|Lagos;Boko Haram;Tinubu
RW|Rwanda|Kigali|Rwandan|africa_e|Kagame
ST|Sao Tome and Principe|Sao Tome|Santomean|africa_w|São Tomé
SN|Senegal|Dakar|Senegalese|africa_w|
SC|Seychelles|Victoria|Seychellois|africa_e|
SL|Sierra Leone|Freetown|Sierra Leonean|africa_w|
SO|Somalia|Mogadishu|Somali|africa_e|Somaliland;Puntland;Al-Shabab
ZA|South Africa|Pretoria|South African|africa_s|Johannesburg;Cape Town;Ramaphosa
SS|South Sudan|Juba|South Sudanese|africa_e|
SD|Sudan|Khartoum|Sudanese|africa_e|Darfur;RSF;El Fasher
TZ|Tanzania|Dodoma|Tanzanian|africa_e|Dar es Salaam;Zanzibar
TG|Togo|Lome|Togolese|africa_w|Lomé
TN|Tunisia|Tunis|Tunisian|africa_n|Saied
UG|Uganda|Kampala|Ugandan|africa_e|Museveni
ZM|Zambia|Lusaka|Zambian|africa_s|
ZW|Zimbabwe|Harare|Zimbabwean|africa_s|Mnangagwa
# ---------------------------------------------------------------- AMERICAS
AG|Antigua and Barbuda|St John's|Antiguan|caribbean|Antigua;Barbuda
AR|Argentina|Buenos Aires|Argentine|latam|Argentinian;Milei
BS|Bahamas|Nassau|Bahamian|caribbean|
BB|Barbados|Bridgetown|Barbadian|caribbean|Bajan
BZ|Belize|Belmopan|Belizean|caribbean|
BO|Bolivia|La Paz|Bolivian|latam|Sucre
BR|Brazil|Brasilia|Brazilian|latam|Brasília;Rio de Janeiro;Sao Paulo;São Paulo;Lula
CA|Canada|Ottawa|Canadian|northam|Toronto;Quebec;Carney
CL|Chile|Santiago|Chilean|latam|
CO|Colombia|Bogota|Colombian|latam|Bogotá;Petro
CR|Costa Rica|San Jose|Costa Rican|latam|San José
CU|Cuba|Havana|Cuban|caribbean|
DM|Dominica|Roseau|Dominican|caribbean|
DO|Dominican Republic|Santo Domingo|Dominican Republic|caribbean|
EC|Ecuador|Quito|Ecuadorian|latam|Guayaquil;Noboa
SV|El Salvador|San Salvador|Salvadoran|latam|Bukele
GD|Grenada|St George's|Grenadian|caribbean|
GT|Guatemala|Guatemala City|Guatemalan|latam|
GY|Guyana|Georgetown|Guyanese|caribbean|Essequibo
HT|Haiti|Port-au-Prince|Haitian|caribbean|
HN|Honduras|Tegucigalpa|Honduran|latam|
JM|Jamaica|Kingston|Jamaican|caribbean|
MX|Mexico|Mexico City|Mexican|latam|Sheinbaum;Sinaloa
NI|Nicaragua|Managua|Nicaraguan|latam|Ortega
PA|Panama|Panama City|Panamanian|latam|Panama Canal
PY|Paraguay|Asuncion|Paraguayan|latam|Asunción
PE|Peru|Lima|Peruvian|latam|
KN|Saint Kitts and Nevis|Basseterre|Kittitian|caribbean|St Kitts;St. Kitts
LC|Saint Lucia|Castries|Saint Lucian|caribbean|St Lucia;St. Lucia
VC|Saint Vincent and the Grenadines|Kingstown|Vincentian|caribbean|St Vincent;St. Vincent
SR|Suriname|Paramaribo|Surinamese|caribbean|
TT|Trinidad and Tobago|Port of Spain|Trinidadian|caribbean|Trinidad;Tobago
US|United States|Washington|American|northam|U.S.;USA;White House;Trump;Congress
UY|Uruguay|Montevideo|Uruguayan|latam|
VE|Venezuela|Caracas|Venezuelan|latam|Maduro
# ---------------------------------------------------------------- ASIA
AF|Afghanistan|Kabul|Afghan|sasia|Taliban
AM|Armenia|Yerevan|Armenian|caucasus|
AZ|Azerbaijan|Baku|Azerbaijani|caucasus|Azeri;Nagorno-Karabakh
BH|Bahrain|Manama|Bahraini|mena|
BD|Bangladesh|Dhaka|Bangladeshi|sasia|Yunus
BT|Bhutan|Thimphu|Bhutanese|sasia|
BN|Brunei|Bandar Seri Begawan|Bruneian|seasia|
KH|Cambodia|Phnom Penh|Cambodian|seasia|Hun Manet
CN|China|Beijing|Chinese|easia|Shanghai;Xinjiang;Hong Kong;Xi Jinping
CY|Cyprus|Nicosia|Cypriot|mena|
GE|Georgia|Tbilisi|Georgian|caucasus|Abkhazia;South Ossetia;Georgian Dream
IN|India|New Delhi|Indian|sasia|Delhi;Mumbai;Kashmir;Modi
ID|Indonesia|Jakarta|Indonesian|seasia|Papua;Prabowo
IR|Iran|Tehran|Iranian|mena|IRGC;Khamenei
IQ|Iraq|Baghdad|Iraqi|mena|Kurdistan;Erbil;Mosul
IL|Israel|Jerusalem|Israeli|mena|Tel Aviv;Netanyahu;IDF
JP|Japan|Tokyo|Japanese|easia|Osaka
JO|Jordan|Amman|Jordanian|mena|
KZ|Kazakhstan|Astana|Kazakh|casia|Almaty;Tokayev
KW|Kuwait|Kuwait City|Kuwaiti|mena|
KG|Kyrgyzstan|Bishkek|Kyrgyz|casia|
LA|Laos|Vientiane|Laotian|seasia|Lao PDR
LB|Lebanon|Beirut|Lebanese|mena|Hezbollah
MY|Malaysia|Kuala Lumpur|Malaysian|seasia|Anwar
MV|Maldives|Male|Maldivian|sasia|Malé
MN|Mongolia|Ulaanbaatar|Mongolian|easia|
MM|Myanmar|Naypyidaw|Burmese|seasia|Burma;Yangon;Rakhine;Arakan
NP|Nepal|Kathmandu|Nepali|sasia|Nepalese
KP|North Korea|Pyongyang|North Korean|easia|DPRK;Kim Jong Un
OM|Oman|Muscat|Omani|mena|
PK|Pakistan|Islamabad|Pakistani|sasia|Karachi;Lahore;Balochistan
PS|Palestine|Ramallah|Palestinian|mena|Gaza;West Bank;Hamas
PH|Philippines|Manila|Filipino|seasia|Philippine;Marcos
QA|Qatar|Doha|Qatari|mena|
SA|Saudi Arabia|Riyadh|Saudi|mena|Jeddah;MBS;bin Salman
SG|Singapore|Singapore|Singaporean|seasia|
KR|South Korea|Seoul|South Korean|easia|
LK|Sri Lanka|Colombo|Sri Lankan|sasia|Dissanayake
SY|Syria|Damascus|Syrian|mena|Aleppo;al-Sharaa
TW|Taiwan|Taipei|Taiwanese|easia|Taiwan Strait
TJ|Tajikistan|Dushanbe|Tajik|casia|
TH|Thailand|Bangkok|Thai|seasia|
TL|Timor-Leste|Dili|Timorese|seasia|East Timor
TR|Turkiye|Ankara|Turkish|mena|Turkey;Türkiye;Istanbul;Erdogan
TM|Turkmenistan|Ashgabat|Turkmen|casia|
AE|United Arab Emirates|Abu Dhabi|Emirati|mena|UAE;Dubai
UZ|Uzbekistan|Tashkent|Uzbek|casia|Mirziyoyev
VN|Vietnam|Hanoi|Vietnamese|seasia|Ho Chi Minh City
YE|Yemen|Sanaa|Yemeni|mena|Houthi;Aden
# ---------------------------------------------------------------- EUROPE
AL|Albania|Tirana|Albanian|balkans|Rama
AD|Andorra|Andorra la Vella|Andorran|europe_w|
AT|Austria|Vienna|Austrian|europe_w|
BY|Belarus|Minsk|Belarusian|europe_e|Lukashenko
BE|Belgium|Brussels|Belgian|europe_w|
BA|Bosnia and Herzegovina|Sarajevo|Bosnian|balkans|Republika Srpska;Dodik;Bosnia
BG|Bulgaria|Sofia|Bulgarian|balkans|
HR|Croatia|Zagreb|Croatian|balkans|
CZ|Czechia|Prague|Czech|europe_e|Czech Republic
DK|Denmark|Copenhagen|Danish|nordic|Greenland;Faroe
EE|Estonia|Tallinn|Estonian|nordic|
FI|Finland|Helsinki|Finnish|nordic|
FR|France|Paris|French|europe_w|Macron
DE|Germany|Berlin|German|europe_w|Merz;Bundestag
GR|Greece|Athens|Greek|balkans|
HU|Hungary|Budapest|Hungarian|europe_e|Orban;Orbán
IS|Iceland|Reykjavik|Icelandic|nordic|
IE|Ireland|Dublin|Irish|europe_w|
IT|Italy|Rome|Italian|europe_w|Meloni
XK|Kosovo|Pristina|Kosovar|balkans|Kosovan;Prishtina
LV|Latvia|Riga|Latvian|nordic|
LI|Liechtenstein|Vaduz|Liechtenstein|europe_w|
LT|Lithuania|Vilnius|Lithuanian|nordic|
LU|Luxembourg|Luxembourg City|Luxembourgish|europe_w|
MT|Malta|Valletta|Maltese|europe_w|
MD|Moldova|Chisinau|Moldovan|europe_e|Transnistria;Sandu
MC|Monaco|Monaco|Monegasque|europe_w|
ME|Montenegro|Podgorica|Montenegrin|balkans|
NL|Netherlands|Amsterdam|Dutch|europe_w|The Hague
MK|North Macedonia|Skopje|Macedonian|balkans|
NO|Norway|Oslo|Norwegian|nordic|
PL|Poland|Warsaw|Polish|europe_e|Tusk;Nawrocki
PT|Portugal|Lisbon|Portuguese|europe_w|
RO|Romania|Bucharest|Romanian|balkans|
RU|Russia|Moscow|Russian|europe_e|Kremlin;Putin
SM|San Marino|San Marino|Sammarinese|europe_w|
RS|Serbia|Belgrade|Serbian|balkans|Vucic;Vučić
SK|Slovakia|Bratislava|Slovak|europe_e|Fico
SI|Slovenia|Ljubljana|Slovenian|balkans|Slovene
ES|Spain|Madrid|Spanish|europe_w|Catalonia;Barcelona;Sanchez
SE|Sweden|Stockholm|Swedish|nordic|
CH|Switzerland|Bern|Swiss|europe_w|Geneva;Zurich
UA|Ukraine|Kyiv|Ukrainian|europe_e|Kiev;Odesa;Kharkiv;Donbas;Zelensky;Zelenskyy
GB|United Kingdom|London|British|europe_w|UK;Britain;Scotland;Wales;Northern Ireland;Starmer;Westminster
VA|Vatican City|Vatican City|Vatican|europe_w|Holy See;Pope Leo
# ---------------------------------------------------------------- OCEANIA
AU|Australia|Canberra|Australian|pacific|Sydney;Melbourne;Albanese
FJ|Fiji|Suva|Fijian|pacific|
KI|Kiribati|Tarawa|I-Kiribati|pacific|
MH|Marshall Islands|Majuro|Marshallese|pacific|
FM|Micronesia|Palikir|Micronesian|pacific|Federated States of Micronesia;Pohnpei;Chuuk
NR|Nauru|Yaren|Nauruan|pacific|Naoero
NZ|New Zealand|Wellington|New Zealander|pacific|Aotearoa;Auckland;Luxon
PW|Palau|Ngerulmud|Palauan|pacific|Koror
PG|Papua New Guinea|Port Moresby|Papua New Guinean|pacific|PNG;Bougainville
WS|Samoa|Apia|Samoan|pacific|
SB|Solomon Islands|Honiara|Solomon Islander|pacific|
TO|Tonga|Nuku'alofa|Tongan|pacific|Nukualofa
TV|Tuvalu|Funafuti|Tuvaluan|pacific|
VU|Vanuatu|Port Vila|Ni-Vanuatu|pacific|Vanuatuan
"""

# bloc -> the continent bucket used for grouping in the UI
BLOC_REGION = {
    "africa_n": "Africa", "africa_w": "Africa", "africa_e": "Africa", "africa_s": "Africa",
    "caribbean": "Americas", "latam": "Americas", "northam": "Americas",
    "mena": "Middle East", "casia": "Asia", "sasia": "Asia", "seasia": "Asia",
    "easia": "Asia", "caucasus": "Asia",
    "europe_w": "Europe", "europe_e": "Europe", "balkans": "Europe", "nordic": "Europe",
    "pacific": "Oceania",
}

# Countries where a Google News national edition exists and is worth a second,
# native-language pass. (hl, gl, ceid)
EDITIONS = {
    "UA": ("uk", "UA", "UA:uk"), "RU": ("ru", "RU", "RU:ru"), "BY": ("ru", "BY", "RU:ru"),
    "KZ": ("ru", "KZ", "KZ:ru"), "FR": ("fr", "FR", "FR:fr"), "DE": ("de", "DE", "DE:de"),
    "ES": ("es", "ES", "ES:es"), "IT": ("it", "IT", "IT:it"), "PT": ("pt", "PT", "PT-PT:pt"),
    "BR": ("pt", "BR", "BR:pt-419"), "PL": ("pl", "PL", "PL:pl"), "NL": ("nl", "NL", "NL:nl"),
    "TR": ("tr", "TR", "TR:tr"), "GR": ("el", "GR", "GR:el"), "CZ": ("cs", "CZ", "CZ:cs"),
    "HU": ("hu", "HU", "HU:hu"), "RO": ("ro", "RO", "RO:ro"), "BG": ("bg", "BG", "BG:bg"),
    "RS": ("sr", "RS", "RS:sr"), "HR": ("hr", "HR", "HR:hr"), "SK": ("sk", "SK", "SK:sk"),
    "SI": ("sl", "SI", "SI:sl"), "SE": ("sv", "SE", "SE:sv"), "NO": ("no", "NO", "NO:no"),
    "DK": ("da", "DK", "DK:da"), "FI": ("fi", "FI", "FI:fi"), "LT": ("lt", "LT", "LT:lt"),
    "LV": ("lv", "LV", "LV:lv"), "EE": ("et", "EE", "EE:et"), "IL": ("he", "IL", "IL:he"),
    "JP": ("ja", "JP", "JP:ja"), "KR": ("ko", "KR", "KR:ko"), "CN": ("zh-CN", "CN", "CN:zh-Hans"),
    "TW": ("zh-TW", "TW", "TW:zh-Hant"), "TH": ("th", "TH", "TH:th"), "VN": ("vi", "VN", "VN:vi"),
    "ID": ("id", "ID", "ID:id"), "IN": ("en", "IN", "IN:en"), "PK": ("en", "PK", "PK:en"),
    "BD": ("bn", "BD", "BD:bn"), "EG": ("ar", "EG", "EG:ar"), "SA": ("ar", "SA", "SA:ar"),
    "AE": ("ar", "AE", "AE:ar"), "LB": ("ar", "LB", "LB:ar"), "MA": ("ar", "MA", "MA:ar"),
    "NG": ("en", "NG", "NG:en"), "KE": ("en", "KE", "KE:en"), "ZA": ("en", "ZA", "ZA:en"),
    "GH": ("en", "GH", "GH:en"), "ET": ("en", "ET", "ET:en"), "UG": ("en", "UG", "UG:en"),
    "TZ": ("en", "TZ", "TZ:en"), "SN": ("fr", "SN", "SN:fr"), "CI": ("fr", "CI", "CI:fr"),
    "CM": ("fr", "CM", "CM:fr"), "MX": ("es", "MX", "MX:es"), "AR": ("es", "AR", "AR:es"),
    "CL": ("es", "CL", "CL:es"), "CO": ("es", "CO", "CO:es"), "PE": ("es", "PE", "PE:es"),
    "VE": ("es", "VE", "VE:es"), "CU": ("es", "CU", "CU:es"), "US": ("en", "US", "US:en"),
    "GB": ("en", "GB", "GB:en"), "CA": ("en", "CA", "CA:en"), "AU": ("en", "AU", "AU:en"),
    "NZ": ("en", "NZ", "NZ:en"), "IE": ("en", "IE", "IE:en"), "PH": ("en", "PH", "PH:en"),
    "MY": ("ms", "MY", "MY:ms"), "SG": ("en", "SG", "SG:en"), "CH": ("de", "CH", "CH:de"),
    "AT": ("de", "AT", "AT:de"), "BE": ("fr", "BE", "BE:fr"),
}


def main():
    out = []
    for raw in TABLE.strip().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        iso, name, capital, demonym, bloc = (p.strip() for p in parts[:5])
        extra = parts[5].strip() if len(parts) > 5 else ""
        terms = [name, capital, demonym]
        terms += [t.strip() for t in extra.split(";") if t.strip()]
        # de-dupe, keep order, drop terms that are substrings of nothing useful
        seen, clean = set(), []
        for t in terms:
            k = t.lower()
            if k and k not in seen:
                seen.add(k)
                clean.append(t)
        rec = {
            "iso": iso,
            "name": name,
            "capital": capital,
            "demonym": demonym,
            "bloc": bloc,
            "region": BLOC_REGION[bloc],
            "terms": clean,
        }
        if iso in EDITIONS:
            hl, gl, ceid = EDITIONS[iso]
            rec["edition"] = {"hl": hl, "gl": gl, "ceid": ceid}
        out.append(rec)

    out.sort(key=lambda c: c["name"])
    path = os.path.join(os.path.dirname(__file__), "..", "config", "countries.json")
    with open(os.path.abspath(path), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    by_region = {}
    for c in out:
        by_region[c["region"]] = by_region.get(c["region"], 0) + 1
    print(f"wrote {len(out)} countries -> config/countries.json")
    for r, n in sorted(by_region.items()):
        print(f"  {r:14s} {n}")
    print(f"  with national Google News edition: {sum(1 for c in out if 'edition' in c)}")


if __name__ == "__main__":
    main()
