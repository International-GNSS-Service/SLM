"""The standard enum type for ISO 3166-1 common countrys"""

from django.utils.translation import gettext_lazy as _
from django_enum import TextChoices
from enum_properties import p, s


class ISOCountry(
    TextChoices,
    s("numeric"),  # type: ignore
    s("alpha3", case_fold=True),  # type: ignore
    p("independent"),  # type: ignore
    s("short_name", case_fold=True),  # type: ignore
    s("full_name", case_fold=True),  # type: ignore
):
    """
    An enumeration for ISO 3166-1 Country codes.
    """

    _symmetric_builtins_ = [s("name", case_fold=True), s("ascii", case_fold=True)]

    AD = "AD", _("Andorra"), 20, "AND", True, "Andorra", "the Principality of Andorra"
    AE = (
        "AE",
        _("United Arab Emirates (the)"),
        784,
        "ARE",
        True,
        "United Arab Emirates (the)",
        "the United Arab Emirates",
    )
    AF = (
        "AF",
        _("Afghanistan"),
        4,
        "AFG",
        True,
        "Afghanistan",
        "the Islamic Republic of Afghanistan",
    )
    AG = (
        "AG",
        _("Antigua and Barbuda"),
        28,
        "ATG",
        True,
        "Antigua and Barbuda",
        "Antigua and Barbuda",
    )
    AI = "AI", _("Anguilla"), 660, "AIA", False, "Anguilla", "Anguilla"
    AL = "AL", _("Albania"), 8, "ALB", True, "Albania", "the Republic of Albania"
    AM = "AM", _("Armenia"), 51, "ARM", True, "Armenia", "the Republic of Armenia"
    AO = "AO", _("Angola"), 24, "AGO", True, "Angola", "the Republic of Angola"
    AQ = "AQ", _("Antarctica"), 10, "ATA", False, "Antarctica", "Antarctica"
    AR = "AR", _("Argentina"), 32, "ARG", True, "Argentina", "the Argentine Republic"
    AS = "AS", _("American Samoa"), 16, "ASM", False, "American Samoa", "American Samoa"
    AT = "AT", _("Austria"), 40, "AUT", True, "Austria", "the Republic of Austria"
    AU = "AU", _("Australia"), 36, "AUS", True, "Australia", "Australia"
    AW = "AW", _("Aruba"), 533, "ABW", False, "Aruba", "Aruba"
    AX = "AX", _("Åland Islands"), 248, "ALA", False, "Åland Islands", "Åland Islands"
    AZ = (
        "AZ",
        _("Azerbaijan"),
        31,
        "AZE",
        True,
        "Azerbaijan",
        "the Republic of Azerbaijan",
    )
    BA = (
        "BA",
        _("Bosnia and Herzegovina"),
        70,
        "BIH",
        True,
        "Bosnia and Herzegovina",
        "Bosnia and Herzegovina",
    )
    BB = "BB", _("Barbados"), 52, "BRB", True, "Barbados", "Barbados"
    BD = (
        "BD",
        _("Bangladesh"),
        50,
        "BGD",
        True,
        "Bangladesh",
        "the People's Republic of Bangladesh",
    )
    BE = "BE", _("Belgium"), 56, "BEL", True, "Belgium", "the Kingdom of Belgium"
    BF = "BF", _("Burkina Faso"), 854, "BFA", True, "Burkina Faso", "Burkina Faso"
    BG = "BG", _("Bulgaria"), 100, "BGR", True, "Bulgaria", "the Republic of Bulgaria"
    BH = "BH", _("Bahrain"), 48, "BHR", True, "Bahrain", "the Kingdom of Bahrain"
    BI = "BI", _("Burundi"), 108, "BDI", True, "Burundi", "the Republic of Burundi"
    BJ = "BJ", _("Benin"), 204, "BEN", True, "Benin", "the Republic of Benin"
    BL = (
        "BL",
        _("Saint Barthélemy"),
        652,
        "BLM",
        False,
        "Saint Barthélemy",
        "Saint Barthélemy",
    )
    BM = "BM", _("Bermuda"), 60, "BMU", False, "Bermuda", "Bermuda"
    BN = (
        "BN",
        _("Brunei Darussalam"),
        96,
        "BRN",
        True,
        "Brunei Darussalam",
        "Brunei Darussalam",
    )
    BO = (
        "BO",
        _("Bolivia (Plurinational State of)"),
        68,
        "BOL",
        True,
        "Bolivia (Plurinational State of)",
        "the Plurinational State of Bolivia",
    )
    BQ = (
        "BQ",
        _("Bonaire, Sint Eustatius and Saba"),
        535,
        "BES",
        False,
        "Bonaire, Sint Eustatius and Saba",
        "Bonaire, Sint Eustatius and Saba",
    )
    BR = (
        "BR",
        _("Brazil"),
        76,
        "BRA",
        True,
        "Brazil",
        "the Federative Republic of Brazil",
    )
    BS = (
        "BS",
        _("Bahamas (the)"),
        44,
        "BHS",
        True,
        "Bahamas (the)",
        "the Commonwealth of the Bahamas",
    )
    BT = "BT", _("Bhutan"), 64, "BTN", True, "Bhutan", "the Kingdom of Bhutan"
    BV = "BV", _("Bouvet Island"), 74, "BVT", False, "Bouvet Island", "Bouvet Island"
    BW = "BW", _("Botswana"), 72, "BWA", True, "Botswana", "the Republic of Botswana"
    BY = "BY", _("Belarus"), 112, "BLR", True, "Belarus", "the Republic of Belarus"
    BZ = "BZ", _("Belize"), 84, "BLZ", True, "Belize", "Belize"
    CA = "CA", _("Canada"), 124, "CAN", True, "Canada", "Canada"
    CC = (
        "CC",
        _("Cocos (Keeling) Islands (the)"),
        166,
        "CCK",
        False,
        "Cocos (Keeling) Islands (the)",
        "Cocos (Keeling) Islands (the)",
    )
    CD = (
        "CD",
        _("Congo (the Democratic Republic of the)"),
        180,
        "COD",
        True,
        "Congo (the Democratic Republic of the)",
        "the Democratic Republic of the Congo",
    )
    CF = (
        "CF",
        _("Central African Republic (the)"),
        140,
        "CAF",
        True,
        "Central African Republic (the)",
        "the Central African Republic",
    )
    CG = (
        "CG",
        _("Congo (the)"),
        178,
        "COG",
        True,
        "Congo (the)",
        "the Republic of the Congo",
    )
    CH = (
        "CH",
        _("Switzerland"),
        756,
        "CHE",
        True,
        "Switzerland",
        "the Swiss Confederation",
    )
    CI = (
        "CI",
        _("Côte d'Ivoire"),
        384,
        "CIV",
        True,
        "Côte d'Ivoire",
        "the Republic of Côte d'Ivoire",
    )
    CK = (
        "CK",
        _("Cook Islands (the)"),
        184,
        "COK",
        False,
        "Cook Islands (the)",
        "Cook Islands (the)",
    )
    CL = "CL", _("Chile"), 152, "CHL", True, "Chile", "the Republic of Chile"
    CM = "CM", _("Cameroon"), 120, "CMR", True, "Cameroon", "the Republic of Cameroon"
    CN = "CN", _("China"), 156, "CHN", True, "China", "the People's Republic of China"
    CO = "CO", _("Colombia"), 170, "COL", True, "Colombia", "the Republic of Colombia"
    CR = (
        "CR",
        _("Costa Rica"),
        188,
        "CRI",
        True,
        "Costa Rica",
        "the Republic of Costa Rica",
    )
    CU = "CU", _("Cuba"), 192, "CUB", True, "Cuba", "the Republic of Cuba"
    CV = (
        "CV",
        _("Cabo Verde"),
        132,
        "CPV",
        True,
        "Cabo Verde",
        "the Republic of Cabo Verde",
    )
    CW = "CW", _("Curaçao"), 531, "CUW", False, "Curaçao", "Curaçao"
    CX = (
        "CX",
        _("Christmas Island"),
        162,
        "CXR",
        False,
        "Christmas Island",
        "Christmas Island",
    )
    CY = "CY", _("Cyprus"), 196, "CYP", True, "Cyprus", "the Republic of Cyprus"
    CZ = "CZ", _("Czechia"), 203, "CZE", True, "Czechia", "the Czech Republic"
    DE = (
        "DE",
        _("Germany"),
        276,
        "DEU",
        True,
        "Germany",
        "the Federal Republic of Germany",
    )
    DJ = "DJ", _("Djibouti"), 262, "DJI", True, "Djibouti", "the Republic of Djibouti"
    DK = "DK", _("Denmark"), 208, "DNK", True, "Denmark", "the Kingdom of Denmark"
    DM = (
        "DM",
        _("Dominica"),
        212,
        "DMA",
        True,
        "Dominica",
        "the Commonwealth of Dominica",
    )
    DO = (
        "DO",
        _("Dominican Republic (the)"),
        214,
        "DOM",
        True,
        "Dominican Republic (the)",
        "the Dominican Republic",
    )
    DZ = (
        "DZ",
        _("Algeria"),
        12,
        "DZA",
        True,
        "Algeria",
        "the People's Democratic Republic of Algeria",
    )
    EC = "EC", _("Ecuador"), 218, "ECU", True, "Ecuador", "the Republic of Ecuador"
    EE = "EE", _("Estonia"), 233, "EST", True, "Estonia", "the Republic of Estonia"
    EG = "EG", _("Egypt"), 818, "EGY", True, "Egypt", "the Arab Republic of Egypt"
    EH = (
        "EH",
        _("Western Sahara*"),
        732,
        "ESH",
        False,
        "Western Sahara*",
        "Western Sahara*",
    )
    ER = "ER", _("Eritrea"), 232, "ERI", True, "Eritrea", "the State of Eritrea"
    ES = "ES", _("Spain"), 724, "ESP", True, "Spain", "the Kingdom of Spain"
    ET = (
        "ET",
        _("Ethiopia"),
        231,
        "ETH",
        True,
        "Ethiopia",
        "the Federal Democratic Republic of Ethiopia",
    )
    FI = "FI", _("Finland"), 246, "FIN", True, "Finland", "the Republic of Finland"
    FJ = "FJ", _("Fiji"), 242, "FJI", True, "Fiji", "the Republic of Fiji"
    FK = (
        "FK",
        _("Falkland Islands (the) [Malvinas]"),
        238,
        "FLK",
        False,
        "Falkland Islands (the) [Malvinas]",
        "Falkland Islands (the) [Malvinas]",
    )
    FM = (
        "FM",
        _("Micronesia (Federated States of)"),
        583,
        "FSM",
        True,
        "Micronesia (Federated States of)",
        "the Federated States of Micronesia",
    )
    FO = (
        "FO",
        _("Faroe Islands (the)"),
        234,
        "FRO",
        False,
        "Faroe Islands (the)",
        "Faroe Islands (the)",
    )
    FR = "FR", _("France"), 250, "FRA", True, "France", "the French Republic"
    GA = "GA", _("Gabon"), 266, "GAB", True, "Gabon", "the Gabonese Republic"
    GB = (
        "GB",
        _("United Kingdom of Great Britain and Northern Ireland (the)"),
        826,
        "GBR",
        True,
        "United Kingdom of Great Britain and Northern Ireland (the)",
        "the United Kingdom of Great Britain and Northern Ireland",
    )
    GD = "GD", _("Grenada"), 308, "GRD", True, "Grenada", "Grenada"
    GE = "GE", _("Georgia"), 268, "GEO", True, "Georgia", "Georgia"
    GF = "GF", _("French Guiana"), 254, "GUF", False, "French Guiana", "French Guiana"
    GG = "GG", _("Guernsey"), 831, "GGY", False, "Guernsey", "Guernsey"
    GH = "GH", _("Ghana"), 288, "GHA", True, "Ghana", "the Republic of Ghana"
    GI = "GI", _("Gibraltar"), 292, "GIB", False, "Gibraltar", "Gibraltar"
    GL = "GL", _("Greenland"), 304, "GRL", False, "Greenland", "Greenland"
    GM = (
        "GM",
        _("Gambia (the)"),
        270,
        "GMB",
        True,
        "Gambia (the)",
        "the Republic of the Gambia",
    )
    GN = "GN", _("Guinea"), 324, "GIN", True, "Guinea", "the Republic of Guinea"
    GP = "GP", _("Guadeloupe"), 312, "GLP", False, "Guadeloupe", "Guadeloupe"
    GQ = (
        "GQ",
        _("Equatorial Guinea"),
        226,
        "GNQ",
        True,
        "Equatorial Guinea",
        "the Republic of Equatorial Guinea",
    )
    GR = "GR", _("Greece"), 300, "GRC", True, "Greece", "the Hellenic Republic"
    GS = (
        "GS",
        _("South Georgia and the South Sandwich Islands"),
        239,
        "SGS",
        False,
        "South Georgia and the South Sandwich Islands",
        "South Georgia and the South Sandwich Islands",
    )
    GT = (
        "GT",
        _("Guatemala"),
        320,
        "GTM",
        True,
        "Guatemala",
        "the Republic of Guatemala",
    )
    GU = "GU", _("Guam"), 316, "GUM", False, "Guam", "Guam"
    GW = (
        "GW",
        _("Guinea-Bissau"),
        624,
        "GNB",
        True,
        "Guinea-Bissau",
        "the Republic of Guinea-Bissau",
    )
    GY = (
        "GY",
        _("Guyana"),
        328,
        "GUY",
        True,
        "Guyana",
        "the Co-operative Republic of Guyana",
    )
    HK = (
        "HK",
        _("Hong Kong"),
        344,
        "HKG",
        False,
        "Hong Kong",
        "the Hong Kong Special Administrative Region of China",
    )
    HM = (
        "HM",
        _("Heard Island and McDonald Islands"),
        334,
        "HMD",
        False,
        "Heard Island and McDonald Islands",
        "Heard Island and McDonald Islands",
    )
    HN = "HN", _("Honduras"), 340, "HND", True, "Honduras", "the Republic of Honduras"
    HR = "HR", _("Croatia"), 191, "HRV", True, "Croatia", "the Republic of Croatia"
    HT = "HT", _("Haiti"), 332, "HTI", True, "Haiti", "the Republic of Haiti"
    HU = "HU", _("Hungary"), 348, "HUN", True, "Hungary", "Hungary"
    ID = (
        "ID",
        _("Indonesia"),
        360,
        "IDN",
        True,
        "Indonesia",
        "the Republic of Indonesia",
    )
    IE = "IE", _("Ireland"), 372, "IRL", True, "Ireland", "Ireland"
    IL = "IL", _("Israel"), 376, "ISR", True, "Israel", "the State of Israel"
    IM = "IM", _("Isle of Man"), 833, "IMN", False, "Isle of Man", "Isle of Man"
    IN = "IN", _("India"), 356, "IND", True, "India", "the Republic of India"
    IO = (
        "IO",
        _("British Indian Ocean Territory (the)"),
        86,
        "IOT",
        False,
        "British Indian Ocean Territory (the)",
        "British Indian Ocean Territory (the)",
    )
    IQ = "IQ", _("Iraq"), 368, "IRQ", True, "Iraq", "the Republic of Iraq"
    IR = (
        "IR",
        _("Iran (Islamic Republic of)"),
        364,
        "IRN",
        True,
        "Iran (Islamic Republic of)",
        "the Islamic Republic of Iran",
    )
    IS = "IS", _("Iceland"), 352, "ISL", True, "Iceland", "the Republic of Iceland"
    IT = "IT", _("Italy"), 380, "ITA", True, "Italy", "the Republic of Italy"
    JE = "JE", _("Jersey"), 832, "JEY", False, "Jersey", "Jersey"
    JM = "JM", _("Jamaica"), 388, "JAM", True, "Jamaica", "Jamaica"
    JO = (
        "JO",
        _("Jordan"),
        400,
        "JOR",
        True,
        "Jordan",
        "the Hashemite Kingdom of Jordan",
    )
    JP = "JP", _("Japan"), 392, "JPN", True, "Japan", "Japan"
    KE = "KE", _("Kenya"), 404, "KEN", True, "Kenya", "the Republic of Kenya"
    KG = "KG", _("Kyrgyzstan"), 417, "KGZ", True, "Kyrgyzstan", "the Kyrgyz Republic"
    KH = "KH", _("Cambodia"), 116, "KHM", True, "Cambodia", "the Kingdom of Cambodia"
    KI = "KI", _("Kiribati"), 296, "KIR", True, "Kiribati", "the Republic of Kiribati"
    KM = (
        "KM",
        _("Comoros (the)"),
        174,
        "COM",
        True,
        "Comoros (the)",
        "the Union of the Comoros",
    )
    KN = (
        "KN",
        _("Saint Kitts and Nevis"),
        659,
        "KNA",
        True,
        "Saint Kitts and Nevis",
        "Saint Kitts and Nevis",
    )
    KP = (
        "KP",
        _("Korea (the Democratic People's Republic of)"),
        408,
        "PRK",
        True,
        "Korea (the Democratic People's Republic of)",
        "the Democratic People's Republic of Korea",
    )
    KR = (
        "KR",
        _("Korea (the Republic of)"),
        410,
        "KOR",
        True,
        "Korea (the Republic of)",
        "the Republic of Korea",
    )
    KW = "KW", _("Kuwait"), 414, "KWT", True, "Kuwait", "the State of Kuwait"
    KY = (
        "KY",
        _("Cayman Islands (the)"),
        136,
        "CYM",
        False,
        "Cayman Islands (the)",
        "Cayman Islands (the)",
    )
    KZ = (
        "KZ",
        _("Kazakhstan"),
        398,
        "KAZ",
        True,
        "Kazakhstan",
        "the Republic of Kazakhstan",
    )
    LA = (
        "LA",
        _("Lao People's Democratic Republic (the)"),
        418,
        "LAO",
        True,
        "Lao People's Democratic Republic (the)",
        "the Lao People's Democratic Republic",
    )
    LB = "LB", _("Lebanon"), 422, "LBN", True, "Lebanon", "the Lebanese Republic"
    LC = "LC", _("Saint Lucia"), 662, "LCA", True, "Saint Lucia", "Saint Lucia"
    LI = (
        "LI",
        _("Liechtenstein"),
        438,
        "LIE",
        True,
        "Liechtenstein",
        "the Principality of Liechtenstein",
    )
    LK = (
        "LK",
        _("Sri Lanka"),
        144,
        "LKA",
        True,
        "Sri Lanka",
        "the Democratic Socialist Republic of Sri Lanka",
    )
    LR = "LR", _("Liberia"), 430, "LBR", True, "Liberia", "the Republic of Liberia"
    LS = "LS", _("Lesotho"), 426, "LSO", True, "Lesotho", "the Kingdom of Lesotho"
    LT = (
        "LT",
        _("Lithuania"),
        440,
        "LTU",
        True,
        "Lithuania",
        "the Republic of Lithuania",
    )
    LU = (
        "LU",
        _("Luxembourg"),
        442,
        "LUX",
        True,
        "Luxembourg",
        "the Grand Duchy of Luxembourg",
    )
    LV = "LV", _("Latvia"), 428, "LVA", True, "Latvia", "the Republic of Latvia"
    LY = "LY", _("Libya"), 434, "LBY", True, "Libya", "the State of Libya"
    MA = "MA", _("Morocco"), 504, "MAR", True, "Morocco", "the Kingdom of Morocco"
    MC = "MC", _("Monaco"), 492, "MCO", True, "Monaco", "the Principality of Monaco"
    MD = (
        "MD",
        _("Moldova (the Republic of)"),
        498,
        "MDA",
        True,
        "Moldova (the Republic of)",
        "the Republic of Moldova",
    )
    ME = "ME", _("Montenegro"), 499, "MNE", True, "Montenegro", "Montenegro"
    MF = (
        "MF",
        _("Saint Martin (French part)"),
        663,
        "MAF",
        False,
        "Saint Martin (French part)",
        "Saint Martin (French part)",
    )
    MG = (
        "MG",
        _("Madagascar"),
        450,
        "MDG",
        True,
        "Madagascar",
        "the Republic of Madagascar",
    )
    MH = (
        "MH",
        _("Marshall Islands (the)"),
        584,
        "MHL",
        True,
        "Marshall Islands (the)",
        "the Republic of the Marshall Islands",
    )
    MK = (
        "MK",
        _("North Macedonia"),
        807,
        "MKD",
        True,
        "North Macedonia",
        "the Republic of North Macedonia",
    )
    ML = "ML", _("Mali"), 466, "MLI", True, "Mali", "the Republic of Mali"
    MM = (
        "MM",
        _("Myanmar"),
        104,
        "MMR",
        True,
        "Myanmar",
        "the Republic of the Union of Myanmar",
    )
    MN = "MN", _("Mongolia"), 496, "MNG", True, "Mongolia", "Mongolia"
    MO = (
        "MO",
        _("Macao"),
        446,
        "MAC",
        False,
        "Macao",
        "Macao Special Administrative Region of China",
    )
    MP = (
        "MP",
        _("Northern Mariana Islands (the)"),
        580,
        "MNP",
        False,
        "Northern Mariana Islands (the)",
        "the Commonwealth of the Northern Mariana Islands",
    )
    MQ = "MQ", _("Martinique"), 474, "MTQ", False, "Martinique", "Martinique"
    MR = (
        "MR",
        _("Mauritania"),
        478,
        "MRT",
        True,
        "Mauritania",
        "the Islamic Republic of Mauritania",
    )
    MS = "MS", _("Montserrat"), 500, "MSR", False, "Montserrat", "Montserrat"
    MT = "MT", _("Malta"), 470, "MLT", True, "Malta", "the Republic of Malta"
    MU = (
        "MU",
        _("Mauritius"),
        480,
        "MUS",
        True,
        "Mauritius",
        "the Republic of Mauritius",
    )
    MV = "MV", _("Maldives"), 462, "MDV", True, "Maldives", "the Republic of Maldives"
    MW = "MW", _("Malawi"), 454, "MWI", True, "Malawi", "the Republic of Malawi"
    MX = "MX", _("Mexico"), 484, "MEX", True, "Mexico", "the United Mexican States"
    MY = "MY", _("Malaysia"), 458, "MYS", True, "Malaysia", "Malaysia"
    MZ = (
        "MZ",
        _("Mozambique"),
        508,
        "MOZ",
        True,
        "Mozambique",
        "the Republic of Mozambique",
    )
    NA = "NA", _("Namibia"), 516, "NAM", True, "Namibia", "the Republic of Namibia"
    NC = "NC", _("New Caledonia"), 540, "NCL", False, "New Caledonia", "New Caledonia"
    NE = (
        "NE",
        _("Niger (the)"),
        562,
        "NER",
        True,
        "Niger (the)",
        "the Republic of the Niger",
    )
    NF = (
        "NF",
        _("Norfolk Island"),
        574,
        "NFK",
        False,
        "Norfolk Island",
        "Norfolk Island",
    )
    NG = (
        "NG",
        _("Nigeria"),
        566,
        "NGA",
        True,
        "Nigeria",
        "the Federal Republic of Nigeria",
    )
    NI = (
        "NI",
        _("Nicaragua"),
        558,
        "NIC",
        True,
        "Nicaragua",
        "the Republic of Nicaragua",
    )
    NL = (
        "NL",
        _("Netherlands (the)"),
        528,
        "NLD",
        True,
        "Netherlands (the)",
        "the Kingdom of the Netherlands",
    )
    NO = "NO", _("Norway"), 578, "NOR", True, "Norway", "the Kingdom of Norway"
    NP = "NP", _("Nepal"), 524, "NPL", True, "Nepal", "Nepal"
    NR = "NR", _("Nauru"), 520, "NRU", True, "Nauru", "the Republic of Nauru"
    NU = "NU", _("Niue"), 570, "NIU", False, "Niue", "Niue"
    NZ = "NZ", _("New Zealand"), 554, "NZL", True, "New Zealand", "New Zealand"
    OM = "OM", _("Oman"), 512, "OMN", True, "Oman", "the Sultanate of Oman"
    PA = "PA", _("Panama"), 591, "PAN", True, "Panama", "the Republic of Panama"
    PE = "PE", _("Peru"), 604, "PER", True, "Peru", "the Republic of Peru"
    PF = (
        "PF",
        _("French Polynesia"),
        258,
        "PYF",
        False,
        "French Polynesia",
        "French Polynesia",
    )
    PG = (
        "PG",
        _("Papua New Guinea"),
        598,
        "PNG",
        True,
        "Papua New Guinea",
        "the Independent State of Papua New Guinea",
    )
    PH = (
        "PH",
        _("Philippines (the)"),
        608,
        "PHL",
        True,
        "Philippines (the)",
        "the Republic of the Philippines",
    )
    PK = (
        "PK",
        _("Pakistan"),
        586,
        "PAK",
        True,
        "Pakistan",
        "the Islamic Republic of Pakistan",
    )
    PL = "PL", _("Poland"), 616, "POL", True, "Poland", "the Republic of Poland"
    PM = (
        "PM",
        _("Saint Pierre and Miquelon"),
        666,
        "SPM",
        False,
        "Saint Pierre and Miquelon",
        "Saint Pierre and Miquelon",
    )
    PN = "PN", _("Pitcairn"), 612, "PCN", False, "Pitcairn", "Pitcairn"
    PR = "PR", _("Puerto Rico"), 630, "PRI", False, "Puerto Rico", "Puerto Rico"
    PS = (
        "PS",
        _("Palestine, State of"),
        275,
        "PSE",
        False,
        "Palestine, State of",
        "the State of Palestine",
    )
    PT = "PT", _("Portugal"), 620, "PRT", True, "Portugal", "the Portuguese Republic"
    PW = "PW", _("Palau"), 585, "PLW", True, "Palau", "the Republic of Palau"
    PY = "PY", _("Paraguay"), 600, "PRY", True, "Paraguay", "the Republic of Paraguay"
    QA = "QA", _("Qatar"), 634, "QAT", True, "Qatar", "the State of Qatar"
    RE = "RE", _("Réunion"), 638, "REU", False, "Réunion", "Réunion"
    RO = "RO", _("Romania"), 642, "ROU", True, "Romania", "Romania"
    RS = "RS", _("Serbia"), 688, "SRB", True, "Serbia", "the Republic of Serbia"
    RU = (
        "RU",
        _("Russian Federation (the)"),
        643,
        "RUS",
        True,
        "Russian Federation (the)",
        "the Russian Federation",
    )
    RW = "RW", _("Rwanda"), 646, "RWA", True, "Rwanda", "the Republic of Rwanda"
    SA = (
        "SA",
        _("Saudi Arabia"),
        682,
        "SAU",
        True,
        "Saudi Arabia",
        "the Kingdom of Saudi Arabia",
    )
    SB = (
        "SB",
        _("Solomon Islands"),
        90,
        "SLB",
        True,
        "Solomon Islands",
        "Solomon Islands",
    )
    SC = (
        "SC",
        _("Seychelles"),
        690,
        "SYC",
        True,
        "Seychelles",
        "the Republic of Seychelles",
    )
    SD = (
        "SD",
        _("Sudan (the)"),
        729,
        "SDN",
        True,
        "Sudan (the)",
        "the Republic of the Sudan",
    )
    SE = "SE", _("Sweden"), 752, "SWE", True, "Sweden", "the Kingdom of Sweden"
    SG = (
        "SG",
        _("Singapore"),
        702,
        "SGP",
        True,
        "Singapore",
        "the Republic of Singapore",
    )
    SH = (
        "SH",
        _("Saint Helena, Ascension and Tristan da Cunha"),
        654,
        "SHN",
        False,
        "Saint Helena, Ascension and Tristan da Cunha",
        "Saint Helena, Ascension and Tristan da Cunha",
    )
    SI = "SI", _("Slovenia"), 705, "SVN", True, "Slovenia", "the Republic of Slovenia"
    SJ = (
        "SJ",
        _("Svalbard and Jan Mayen"),
        744,
        "SJM",
        False,
        "Svalbard and Jan Mayen",
        "Svalbard and Jan Mayen",
    )
    SK = "SK", _("Slovakia"), 703, "SVK", True, "Slovakia", "the Slovak Republic"
    SL = (
        "SL",
        _("Sierra Leone"),
        694,
        "SLE",
        True,
        "Sierra Leone",
        "the Republic of Sierra Leone",
    )
    SM = (
        "SM",
        _("San Marino"),
        674,
        "SMR",
        True,
        "San Marino",
        "the Republic of San Marino",
    )
    SN = "SN", _("Senegal"), 686, "SEN", True, "Senegal", "the Republic of Senegal"
    SO = (
        "SO",
        _("Somalia"),
        706,
        "SOM",
        True,
        "Somalia",
        "the Federal Republic of Somalia",
    )
    SR = "SR", _("Suriname"), 740, "SUR", True, "Suriname", "the Republic of Suriname"
    SS = (
        "SS",
        _("South Sudan"),
        728,
        "SSD",
        True,
        "South Sudan",
        "the Republic of South Sudan",
    )
    ST = (
        "ST",
        _("Sao Tome and Principe"),
        678,
        "STP",
        True,
        "Sao Tome and Principe",
        "the Democratic Republic of Sao Tome and Principe",
    )
    SV = (
        "SV",
        _("El Salvador"),
        222,
        "SLV",
        True,
        "El Salvador",
        "the Republic of El Salvador",
    )
    SX = (
        "SX",
        _("Sint Maarten (Dutch part)"),
        534,
        "SXM",
        False,
        "Sint Maarten (Dutch part)",
        "Sint Maarten (Dutch part)",
    )
    SY = (
        "SY",
        _("Syrian Arab Republic (the)"),
        760,
        "SYR",
        True,
        "Syrian Arab Republic (the)",
        "the Syrian Arab Republic",
    )
    SZ = "SZ", _("Eswatini"), 748, "SWZ", True, "Eswatini", "the Kingdom of Eswatini"
    TC = (
        "TC",
        _("Turks and Caicos Islands (the)"),
        796,
        "TCA",
        False,
        "Turks and Caicos Islands (the)",
        "Turks and Caicos Islands (the)",
    )
    TD = "TD", _("Chad"), 148, "TCD", True, "Chad", "the Republic of Chad"
    TF = (
        "TF",
        _("French Southern Territories (the)"),
        260,
        "ATF",
        False,
        "French Southern Territories (the)",
        "French Southern Territories (the)",
    )
    TG = "TG", _("Togo"), 768, "TGO", True, "Togo", "the Togolese Republic"
    TH = "TH", _("Thailand"), 764, "THA", True, "Thailand", "the Kingdom of Thailand"
    TJ = (
        "TJ",
        _("Tajikistan"),
        762,
        "TJK",
        True,
        "Tajikistan",
        "the Republic of Tajikistan",
    )
    TK = "TK", _("Tokelau"), 772, "TKL", False, "Tokelau", "Tokelau"
    TL = (
        "TL",
        _("Timor-Leste"),
        626,
        "TLS",
        True,
        "Timor-Leste",
        "the Democratic Republic of Timor-Leste",
    )
    TM = "TM", _("Turkmenistan"), 795, "TKM", True, "Turkmenistan", "Turkmenistan"
    TN = "TN", _("Tunisia"), 788, "TUN", True, "Tunisia", "the Republic of Tunisia"
    TO = "TO", _("Tonga"), 776, "TON", True, "Tonga", "the Kingdom of Tonga"
    TR = "TR", _("Türkiye"), 792, "TUR", True, "Türkiye", "the Republic of Türkiye"
    TT = (
        "TT",
        _("Trinidad and Tobago"),
        780,
        "TTO",
        True,
        "Trinidad and Tobago",
        "the Republic of Trinidad and Tobago",
    )
    TV = "TV", _("Tuvalu"), 798, "TUV", True, "Tuvalu", "Tuvalu"
    TW = "TW", _("Taiwan"), 158, "TWN", False, "Taiwan", "Taiwan (Province of China)"
    TZ = (
        "TZ",
        _("Tanzania, the United Republic of"),
        834,
        "TZA",
        True,
        "Tanzania, the United Republic of",
        "the United Republic of Tanzania",
    )
    UA = "UA", _("Ukraine"), 804, "UKR", True, "Ukraine", "Ukraine"
    UG = "UG", _("Uganda"), 800, "UGA", True, "Uganda", "the Republic of Uganda"
    UM = (
        "UM",
        _("United States Minor Outlying Islands (the)"),
        581,
        "UMI",
        False,
        "United States Minor Outlying Islands (the)",
        "United States Minor Outlying Islands (the)",
    )
    US = (
        "US",
        _("United States of America (the)"),
        840,
        "USA",
        True,
        "United States of America (the)",
        "the United States of America",
    )
    UY = (
        "UY",
        _("Uruguay"),
        858,
        "URY",
        True,
        "Uruguay",
        "the Eastern Republic of Uruguay",
    )
    UZ = (
        "UZ",
        _("Uzbekistan"),
        860,
        "UZB",
        True,
        "Uzbekistan",
        "the Republic of Uzbekistan",
    )
    VA = "VA", _("Holy See (the)"), 336, "VAT", True, "Holy See (the)", "Holy See (the)"
    VC = (
        "VC",
        _("Saint Vincent and the Grenadines"),
        670,
        "VCT",
        True,
        "Saint Vincent and the Grenadines",
        "Saint Vincent and the Grenadines",
    )
    VE = (
        "VE",
        _("Venezuela (Bolivarian Republic of)"),
        862,
        "VEN",
        True,
        "Venezuela (Bolivarian Republic of)",
        "the Bolivarian Republic of Venezuela",
    )
    VG = (
        "VG",
        _("Virgin Islands (British)"),
        92,
        "VGB",
        False,
        "Virgin Islands (British)",
        "British Virgin Islands (the)",
    )
    VI = (
        "VI",
        _("Virgin Islands (U.S.)"),
        850,
        "VIR",
        False,
        "Virgin Islands (U.S.)",
        "the Virgin Islands of the United States",
    )
    VN = (
        "VN",
        _("Viet Nam"),
        704,
        "VNM",
        True,
        "Viet Nam",
        "the Socialist Republic of Viet Nam",
    )
    VU = "VU", _("Vanuatu"), 548, "VUT", True, "Vanuatu", "the Republic of Vanuatu"
    WF = (
        "WF",
        _("Wallis and Futuna"),
        876,
        "WLF",
        False,
        "Wallis and Futuna",
        "Wallis and Futuna Islands",
    )
    WS = "WS", _("Samoa"), 882, "WSM", True, "Samoa", "the Independent State of Samoa"
    YE = "YE", _("Yemen"), 887, "YEM", True, "Yemen", "the Republic of Yemen"
    YT = "YT", _("Mayotte"), 175, "MYT", False, "Mayotte", "Mayotte"
    ZA = (
        "ZA",
        _("South Africa"),
        710,
        "ZAF",
        True,
        "South Africa",
        "the Republic of South Africa",
    )
    ZM = "ZM", _("Zambia"), 894, "ZMB", True, "Zambia", "the Republic of Zambia"
    ZW = "ZW", _("Zimbabwe"), 716, "ZWE", True, "Zimbabwe", "the Republic of Zimbabwe"
    # pylint: disable=C0303

    @property
    def ascii(self):
        ascii_name = self.short_name
        for utf16, char in [("é", "e"), ("ç", "c"), ("ü", "u"), ("ô", "o"), ("Å", "A")]:
            ascii_name = ascii_name.replace(utf16, char)
        return ascii_name

    @property
    def alpha2(self):
        return self.value

    def __str__(self):
        """
        The string representation of this enum is its alpha-2 country code
        """
        return str(self.value)

    @classmethod
    def with_stations(cls, objects=None):
        """
        Get the list of countries that have ever had stations sited within.
        The result of this function is should not be read until after
        Django is initialized.

        :param objects: The model manage for the model with the country field.
        """
        if objects is None:
            from slm.models import SiteLocation

            objects = SiteLocation.objects

        return list(
            set(
                [
                    country
                    for country in objects.values_list("country", flat=True)
                    .distinct()
                    .order_by("country")
                    if isinstance(country, cls)
                ]
            )
        )
