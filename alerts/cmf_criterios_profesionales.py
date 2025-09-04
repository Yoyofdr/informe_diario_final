"""
Criterios profesionales para análisis de hechos esenciales CMF
Basado en mejores prácticas de Bloomberg/Refinitiv
"""

# Empresas IPSA (actualizar semestralmente según cambios en el índice)
EMPRESAS_IPSA = {
    # Bancos
    "BANCO DE CHILE", "BANCO SANTANDER", "BANCO SANTANDER-CHILE", "BCI", "BANCO CREDITO", 
    "BANCO ITAU", "ITAU CORPBANCA", "SCOTIABANK",
    
    # Retail
    "CENCOSUD", "FALABELLA", "RIPLEY", "SMU", "FORUS",
    
    # Utilities
    "ENEL CHILE", "ENEL AMERICAS", "COLBUN", "ENGIE", "AGUAS ANDINAS",
    
    # Commodities y Materiales
    "SQM", "SQM-A", "SQM-B", "COPEC", "CMPC", "CAP", "MOLIBDENOS",
    
    # Inmobiliarias
    "PARQUE ARAUCO", "PLAZA", "MALL PLAZA", "CENCOSUD SHOPPING",
    
    # Telecomunicaciones
    "ENTEL", "WOM",
    
    # Transporte
    "VAPORES", "SONDA",
    
    # Otros
    "CCU", "EMBOTELLADORA ANDINA", "CONCHA Y TORO", "ILC", "SECURITY",
    "QUINENCO", "ORO BLANCO", "BESALCO"
}

# Mapeo manual temporal para casos conocidos donde materia es "Otros" pero sabemos el contenido real
CASOS_ESPECIALES_CMF = {
    "MASISA S.A.": ["búsqueda de inversionista", "proceso de venta"],
    "CLINICA LAS CONDES S.A.": ["aumento de capital"],
    "CLÍNICA LAS CONDES S.A.": ["aumento de capital"],  # Por si aparece con tilde
}

# Empresas estratégicas adicionales (no IPSA pero relevantes) - 500 empresas importantes de Chile
EMPRESAS_ESTRATEGICAS = {
    "LATAM AIRLINES", "SKY AIRLINE", "JETSMART", "ILC", "CONSORCIO FINANCIERO",
    "GRUPO SECURITY", "GRUPO PATIO", "GRUPO ANGELINI", "GRUPO LUKSIC", "HABITAT",
    "CUPRUM", "PROVIDA", "CAPITAL", "MODELO", "PLANVITAL", "UNO", "ENJOY",
    "DREAMS", "SUN MONTICELLO", "MARINA DEL SOL", "SALFACORP", "SOCOVESA",
    "INGEVEC", "ECHEVERRIA IZQUIERDO", "PAZ CORP", "MOLLER", "ENACO", "FUNDAMENTA",
    "ALMAGRO", "MANQUEHUE", "CRISTALES", "CAROZZI", "WATTS", "MULTIFOODS",
    "AGROSUPER", "ARIZTIA", "DON POLLO", "TRENDY", "TUCAPEL", "BLUMAR",
    "CAMANCHACA", "AUSTRALIS SEAFOODS", "MULTIEXPORT", "VENTISQUEROS",
    "SALMONES ANTARTICA", "AQUACHILE", "MASISA", "ARAUCO", "TRICOT", "HITES",
    "LA POLAR", "ABCDIN", "CORONA", "JOHNSON", "VTR", "MOVISTAR", "CLARO",
    "MUNDO", "GTDINTERNET", "CLINICA LAS CONDES", "CLINICA ALEMANA",
    "CLINICA SANTA MARIA", "CLINICA DAVILA", "REDSALUD", "BANMEDICA",
    "CRUZ BLANCA", "COLMENA", "MASVIDA", "VIDA TRES", "TRANSBANK", "REDBUS",
    "TURBUS", "PULLMAN", "SOTRASER", "PUERTO VENTANAS", "PUERTO LIRQUEN",
    "LAUREATE", "UNIVERSIDAD ANDRES BELLO", "UNIVERSIDAD LAS AMERICAS", "DUOC UC",
    "INACAP", "ACCIONA", "MAINSTREAM", "PATTERN ENERGY", "AELA ENERGIA",
    "FACTORING SECURITY", "TANNER SERVICIOS FINANCIEROS", "FORUM", "COOPEUCH",
    "CODELCO", "METRO", "EFE", "CORREOS DE CHILE", "EMPRESA NACIONAL DE MINERIA",
    "ENAMI", "CODELCO NORTE", "CODELCO ANDINA", "CODELCO EL TENIENTE",
    "CODELCO SALVADOR", "CODELCO VENTANAS", "MINERA ESCONDIDA", "MINERA COLLAHUASI",
    "MINERA LOS PELAMBRES", "MINERA CANDELARIA", "MINERA CERRO COLORADO",
    "MINERA SPENCE", "MINERA EL ABRA", "MINERA ZALDIVAR", "MINERA CENTINELA",
    "MINERA QUEBRADA BLANCA", "ANGLO AMERICAN CHILE", "BARRICK CHILE",
    "KINROSS CHILE", "TECK CHILE", "FREEPORT MCMORAN CHILE", "GLENCORE CHILE",
    "BHP CHILE", "RIO TINTO CHILE", "VALE CHILE", "COEUR MINING CHILE",
    "PAN AMERICAN SILVER CHILE", "YAMANA GOLD CHILE", "LUNDIN MINING CHILE",
    "CAPSTONE MINING CHILE", "FIRST QUANTUM MINERALS CHILE", "HUDBAY MINERALS CHILE",
    "MANTOS COPPER", "ANDES IRON", "MINERA VALLE CENTRAL", "CMP",
    "MINERA SANTA BARBARA", "MINERA LAS CENIZAS", "MINERA FLORIDA", "PUCOBRE",
    "ATACAMA KOZAN", "HALDEMAN MINING", "CEMIN", "MINERA TRES VALLES",
    "MINERA PUNTA DEL COBRE", "SOCIEDAD PUNTA DEL COBRE", "ENGIE ENERGIA CHILE",
    "AES ANDES", "COLBUN TRANSMISION", "TRANSELEC", "ISA INTERCHILE",
    "CELEO REDES", "AES GENER TRANSMISION", "SAESA", "FRONTEL", "LUZ OSORNO",
    "EDELAYSEN", "EDELMAG", "CHILQUINTA", "ENERGÍA LATINA", "LITORAL", "CONAFE",
    "CODINER", "COOPELAN", "CEC", "COELCHA", "COPELEC", "SOCOEPA", "COOPREL",
    "LUZ LINARES", "LUZ PARRAL", "ENGIE TRANSMISION", "POLPAICO", "CEMENTOS MELÓN",
    "CEMENTOS BSA", "READY MIX", "HORMIGONES TRANSEX", "PETREOS QUILIN",
    "ARIDOS SANTA GLORIA", "SITRANS", "CONSTRUCTORA CONPAX",
    "CONSTRUCTORA CLARO VICUÑA VALENZUELA", "CONSTRUCTORA TECSA",
    "CONSTRUCTORA BROTEC", "CONSTRUCTORA NOVATEC", "CONSTRUCTORA EBCO",
    "CONSTRUCTORA ICAFAL", "CONSTRUCTORA RVC", "CONSTRUCTORA CYPCO",
    "CONSTRUCTORA ECORA", "CONSTRUCTORA OVAL", "CONSTRUCTORA L Y D",
    "CONSTRUCTORA ACSA", "CONSTRUCTORA SICOMAQ", "CONSTRUCTORA RALEI",
    "CONSTRUCTORA DESCO", "CONSTRUCTORA MSH", "CONSTRUCTORA RECONSA",
    "CONSTRUCTORA NUEVA VIDA", "CONSTRUCTORA COSAL", "DRAGADOS", "SACYR CHILE",
    "FERROVIAL CHILE", "OHL CHILE", "ACCIONA CONSTRUCCION CHILE", "ACS CHILE",
    "FCC CONSTRUCCION CHILE", "VINCI CHILE", "BOUYGUES CHILE", "SKANSKA CHILE",
    "STRABAG CHILE", "WEBUILD CHILE", "CHINA RAILWAY CHILE", "CHINA HARBOUR CHILE",
    "SINOHYDRO CHILE", "POWER CHINA CHILE", "CRCC CHILE", "ASTALDI CHILE",
    "PIZZA HUT CHILE", "KFC CHILE", "STARBUCKS CHILE", "BURGER KING CHILE",
    "MCDONALDS CHILE", "SUBWAY CHILE", "DOMINOS PIZZA CHILE", "PAPA JOHNS CHILE",
    "DUNKIN DONUTS CHILE", "TIM HORTONS CHILE", "JUAN MAESTRO", "PEDRO JUAN Y DIEGO",
    "DOGGIS", "TOMMY BEANS", "MAMUT", "HOLY MOLY", "TARRAGONA", "IL TANO",
    "EMPORIO LA ROSA", "TELEPIZZA", "SUSHI BLUES", "OSAKA", "NOLITA", "LORENZINI",
    "LA PICCOLA ITALIA", "GIRATORIO", "BARANDIARAN", "FUENTE ALEMANA", "DOMINÓ",
    "UNCLE FLETCH", "GATSBY", "FLANNERYS", "CALIFORNIA CANTINA", "APPLEBEES CHILE",
    "CHILIS CHILE", "RUBY TUESDAY CHILE", "OUTBACK CHILE", "P.F. CHANGS CHILE",
    "OLIVE GARDEN CHILE", "RED LOBSTER CHILE", "HOOTERS CHILE", "HARD ROCK CAFE CHILE",
    "PLANET HOLLYWOOD CHILE", "RAINFOREST CAFE CHILE", "BUBBA GUMP CHILE",
    "MARGARITAVILLE CHILE", "WALMART CHILE", "PARIS", "EASY", "SODIMAC CONSTRUCTOR",
    "IMPERIAL", "HOMECENTER SODIMAC", "TOTTUS", "SANTA ISABEL", "CONSTRUMART",
    "MAYORISTA 10", "ALVI", "MERKAT", "SUPERMERCADOS MONTSERRAT", "SUPERMERCADOS BRYC",
    "SUPERMERCADOS ERBI", "SUPERMERCADOS KORLAET", "SUPERMERCADOS COUGIL",
    "SUPERMERCADOS EL TREBOL", "SUPERMERCADOS GARCIA", "SUPERMERCADOS LAS BRISAS",
    "SUPERMERCADOS PUERTO FRESCO", "SUPERMERCADOS SAN FRANCISCO",
    "SUPERMERCADOS ECONOMAX", "SUPERMERCADOS BIGGER", "SUPERMERCADOS FULLMARKET",
    "SUPERMERCADOS EL BARATILLO", "SUPERMERCADOS LA COLONIA", "SUPERMERCADOS BONANZA",
    "SUPERMERCADOS DIPAC", "SUPERMERCADOS KOSTO", "SUPERMERCADOS MONTECARLO",
    "SUPERMERCADOS YULUKA", "SUPERMERCADOS LAS PALMAS", "SUPERMERCADOS LOS ECONOMICOS",
    "OXXO CHILE", "OK MARKET", "PRONTO COPEC", "PUNTO COPEC", "ZERVO", "SPID35",
    "SELECT", "UP EXPRESS", "FRESH MARKET", "BIG JOHN", "MI CLUB", "MAXI AHORRO",
    "DIPROVENA", "DISTRIBUIDORA PRISA", "DISTRIBUIDORA LA PREFERIDA",
    "COMERCIAL RUTA NORTE", "DISTRIBUIDORA RABIE HERMANOS", "DISTRIBUIDORA DIMARSA",
    "DISTRIBUIDORA JB", "DISTRIBUIDORA GOMEZ Y GOMEZ", "DISTRIBUIDORA CIAL",
    "DISTRIBUIDORA DIMAK", "DISTRIBUIDORA DIPAR", "DISTRIBUIDORA DICOFAR",
    "DISTRIBUIDORA DINACAR", "DISTRIBUIDORA DISMAK", "DISTRIBUIDORA PUELCHE",
    "DISTRIBUIDORA ERA", "DISTRIBUIDORA MENDOZA", "DISTRIBUIDORA TGM",
    "DISTRIBUIDORA PUNTO AZUL", "DISTRIBUIDORA DIMEIGGS", "DISTRIBUIDORA DIMARCO",
    "DISTRIBUIDORA RDV", "DISTRIBUIDORA LOS JAZMINES", "DISTRIBUIDORA COPIHUE",
    "DISTRIBUIDORA RAYEN", "DISTRIBUIDORA EL SOL", "DISTRIBUIDORA FRUNA",
    "DISTRIBUIDORA DANONE", "DISTRIBUIDORA PEPSICO", "DISTRIBUIDORA NESTLE",
    "DISTRIBUIDORA UNILEVER", "DISTRIBUIDORA P&G", "DISTRIBUIDORA COLGATE",
    "DISTRIBUIDORA KIMBERLY CLARK", "DISTRIBUIDORA SC JOHNSON",
    "DISTRIBUIDORA RECKITT BENCKISER", "DISTRIBUIDORA HENKEL", "DISTRIBUIDORA BAYER",
    "DISTRIBUIDORA SANOFI", "DISTRIBUIDORA PFIZER", "DISTRIBUIDORA NOVARTIS",
    "DISTRIBUIDORA MERCK", "DISTRIBUIDORA GSK", "DISTRIBUIDORA ABBOTT",
    "DISTRIBUIDORA ROCHE", "DISTRIBUIDORA J&J", "FARMACIAS AHUMADA",
    "FARMACIAS CRUZ VERDE", "FARMACIAS SALCOBRAND", "FARMACIAS DR SIMI",
    "FARMACIAS REDFARMA", "FARMACIAS FARMACITY", "FARMACIAS FARMAPRONTO",
    "FARMACIAS FARMAVIDA", "FARMACIAS FARMAEXPRESS", "FARMACIAS FARMASALUD",
    "FARMACIAS ECONOMICAS", "FARMACIAS DEL DR AHORRO", "FARMACIAS SIMILARES",
    "FARMACIAS GENERICAS", "LABORATORIO CHILE", "LABORATORIO SAVAL",
    "LABORATORIO ANDROMACO", "LABORATORIO PASTEUR", "LABORATORIO MINTLAB",
    "LABORATORIO PHARMA INVESTI", "LABORATORIO BAGÓ", "LABORATORIO RIDER",
    "LABORATORIO SYNTHON", "LABORATORIO OPKO", "LABORATORIO KAMPAR",
    "LABORATORIO MEDIPHARM", "LABORATORIO TECNOFARMA", "LABORATORIO EUROFARMA",
    "LABORATORIO BIOSANO", "LABORATORIO GALENICUM", "LABORATORIO FARMINDUSTRIA",
    "LABORATORIO PHARMAVITA", "LABORATORIO PRATER", "LABORATORIO SILESIA",
    "IMPORTADORA CAFE DO BRASIL", "IMPORTADORA Y DISTRIBUIDORA ARKOS",
    "IMPORTADORA DIMERC", "IMPORTADORA FORUS", "IMPORTADORA MADECO",
    "IMPORTADORA RAAB", "IMPORTADORA MAR", "IMPORTADORA TRESMONTES",
    "IMPORTADORA SOPROLE", "IMPORTADORA SUAZO", "IMPORTADORA TATTERSALL",
    "IMPORTADORA INDUMOTORA", "IMPORTADORA GILDEMEISTER", "IMPORTADORA SKC",
    "IMPORTADORA SIGDOTEK", "IMPORTADORA AUTOMOTRIZ PORTILLO", "IMPORTADORA KAUFMANN",
    "IMPORTADORA DERCO", "IMPORTADORA SALINAS Y FABRES", "IMPORTADORA SALFA",
    "IMPORTADORA COSECHE", "IMPORTADORA AUTOMOTORES FRANCO CHILENA",
    "IMPORTADORA KOVACS", "IMPORTADORA PEUGEOT CHILE", "IMPORTADORA CITROEN CHILE",
    "IMPORTADORA MAZDA CHILE", "IMPORTADORA MITSUBISHI CHILE", "IMPORTADORA SUBARU CHILE",
    "IMPORTADORA HYUNDAI CHILE", "IMPORTADORA KIA CHILE", "IMPORTADORA NISSAN CHILE",
    "IMPORTADORA RENAULT CHILE", "IMPORTADORA SUZUKI CHILE", "IMPORTADORA SSANGYONG CHILE",
    "IMPORTADORA CHERY CHILE", "IMPORTADORA GREAT WALL CHILE", "IMPORTADORA JAC CHILE",
    "IMPORTADORA MG CHILE", "IMPORTADORA BAIC CHILE", "IMPORTADORA DFSK CHILE",
    "IMPORTADORA HAVAL CHILE", "IMPORTADORA MAXUS CHILE", "IMPORTADORA FOTON CHILE",
    "IMPORTADORA IVECO CHILE", "IMPORTADORA GOLDEN DRAGON CHILE", "IMPORTADORA HINO CHILE",
    "IMPORTADORA VOLKSWAGEN CHILE", "IMPORTADORA AUDI CHILE", "IMPORTADORA BMW CHILE",
    "IMPORTADORA MERCEDES BENZ CHILE", "IMPORTADORA PORSCHE CHILE",
    "IMPORTADORA FERRARI CHILE", "IMPORTADORA LAMBORGHINI CHILE",
    "IMPORTADORA MASERATI CHILE", "IMPORTADORA BENTLEY CHILE",
    "IMPORTADORA ROLLS ROYCE CHILE", "IMPORTADORA ASTON MARTIN CHILE",
    "IMPORTADORA LOTUS CHILE", "IMPORTADORA MCLAREN CHILE", "VIÑA CONCHA Y TORO",
    "VIÑA SAN PEDRO", "VIÑA SANTA RITA", "VIÑA UNDURRAGA", "VIÑA TARAPACA",
    "VIÑA SANTA CAROLINA", "VIÑA CONO SUR", "VIÑA CASILLERO DEL DIABLO",
    "VIÑA VENTISQUERO", "VIÑA MONTES", "VIÑA ERRAZURIZ", "VIÑA MIGUEL TORRES",
    "VIÑA MONTGRAS", "VIÑA LAPOSTOLLE", "VIÑA VIU MANENT", "VIÑA SANTA EMA",
    "VIÑA VERAMONTE", "VIÑA LOS VASCOS", "VIÑA COUSINO MACUL", "VIÑA VALDIVIESO",
    "VIÑA CALITERRA", "VIÑA CASA SILVA", "VIÑA EMILIANA", "VIÑA LUIS FELIPE EDWARDS",
    "VIÑA VON SIEBENTHAL", "VIÑA CLOS APALTA", "VIÑA ALMAVIVA", "VIÑA SENA",
    "VIÑA CHADWICK", "VIÑA DON MELCHOR", "VIÑA PURPLE ANGEL", "VIÑA CASA REAL",
    "VIÑA MARQUES DE CASA CONCHA", "VIÑA NEYEN", "VIÑA ANTIYAL", "VIÑA MATETIC",
    "VIÑA KINGSTON", "VIÑA GARAGE WINE", "VIÑA ARISTOS", "VIÑA QUEBRADA DE MACUL",
    "VIÑA PEREZ CRUZ", "VIÑA HARAS DE PIRQUE", "VIÑA ODFJELL", "VIÑA KOYLE",
    "VIÑA BOUCHON", "VIÑA J BOUCHON", "VIÑA MORANDE", "VIÑA MAQUIS", "VIÑA TAMAYA",
    "VIÑA TABALI", "PISCO CAPEL", "PISCO ALTO DEL CARMEN", "PISCO MISTRAL",
    "PISCO CONTROL", "PISCO CAMPANARIO", "PISCO ARTESANOS DEL COCHIGUAZ",
    "PISCO WAQAR", "PISCO MAL PASO", "PISCO HORCÓN QUEMADO", "PISCO MONTEGRANDE",
    "CERVECERIA KROSS", "CERVECERIA KUNTSMANN", "CERVECERIA AUSTRAL",
    "CERVECERIA SZOT", "CERVECERIA GUAYACAN", "CERVECERIA TUBINGER",
    "CERVECERIA ROTHHAMMER", "CERVECERIA MAHINA", "CERVECERIA CUELLO NEGRO",
    "CERVECERIA NOMADE", "CERVECERIA JESTER", "CERVECERIA TROPERA", "CERVECERIA CODA",
    "CERVECERIA CIUDAD VIEJA", "CERVECERIA MESTRA", "CERVECERIA GRANIZO",
    "CERVECERIA SPOH", "CERVECERIA KAISER", "CERVECERIA COSA NOSTRA",
    "CERVECERIA LAGER", "CERVECERIA BUNDOR", "CERVECERIA DOLBEK", "CERVECERIA TROG",
    "CERVECERIA DEL PUERTO", "CERVECERIA CRATER", "CERVECERIA BRUDER",
    "CERVECERIA ALTAMIRA", "CERVECERIA RAYEN", "CERVECERIA MALDITA", "ATACAMA SOLAR",
    "CERRO DOMINADOR", "ENEL GREEN POWER CHILE", "GRENERGY CHILE", "SOLVENTUS CHILE",
    "SUNPOWER CHILE", "FIRST SOLAR CHILE", "CANADIAN SOLAR CHILE", "JINKO SOLAR CHILE",
    "TRINA SOLAR CHILE", "X-ELIO CHILE", "SONNEDIX CHILE", "SOLARPACK CHILE",
    "FOTOWATIO CHILE", "IBERDROLA CHILE", "EDF RENEWABLES CHILE", "TOTAL EREN CHILE",
    "EDP RENEWABLES CHILE", "NATURGY RENOVABLES CHILE", "REPSOL RENOVABLES CHILE",
    "SHELL RENEWABLES CHILE", "BP RENEWABLES CHILE", "EQUINOR CHILE", "ORSTED CHILE",
    "NORTHLAND POWER CHILE", "INNERGEX CHILE", "BORALEX CHILE",
    "BROOKFIELD RENEWABLE CHILE", "SEMPRA CHILE", "AES RENEWABLE CHILE",
    "DUKE ENERGY CHILE", "NEXTERA CHILE", "INVENERGY CHILE", "COPEC SA",
    "PETROBRAS CHILE", "ESMAX", "LIPIGAS", "ABASTIBLE", "GASCO", "METROGAS",
    "GASVALPO", "INTERGAS", "GASUR", "ENAP REFINERIAS", "TERMINAL QUINTERO",
    "TERMINAL MEJILLONES", "OXIQUIM", "TERMINAL CORONEL", "TERMINAL SAN VICENTE",
    "TERMINAL PENCO LIRQUEN", "TERMINAL PUERTO MONTT", "TERMINAL CALBUCO", "ASMAR",
    "MAESTRANZA DIESEL", "SITECNA", "SOMARCO", "TECNAVAL", "MARCO CHILENA",
    "DETROIT CHILE", "VULCO", "PROMET", "STX CHILE",
    # Agregar variantes con tildes y sin S.A./SA
    "CLÍNICA LAS CONDES", "CLÍNICA ALEMANA", "CLÍNICA SANTA MARÍA", "CLÍNICA DÁVILA",
    "TANNER", "MASISA S.A.", "CLINICA LAS CONDES S.A.", "CLÍNICA LAS CONDES S.A.",
    # Nuevas empresas agregadas (200 empresas + bancos)
    "CONSORCIO SEGUROS", "VIDA SECURITY", "COMPAÑÍA DE SEGUROS CONFUTURO",
    "SEGUROS VIDA CORP", "BICE VIDA", "EUROAMERICA SEGUROS", "OHIO NATIONAL SEGUROS",
    "METLIFE CHILE", "PRINCIPAL SEGUROS", "ZURICH SANTANDER SEGUROS",
    "INMOBILIARIA ACONCAGUA", "INMOBILIARIA LAS VERBENAS", "INMOBILIARIA SIMONETTI",
    "INMOBILIARIA TITANIUM", "INMOBILIARIA PUERTO NUEVO", "CONSTRUCTORA SANTA BEATRIZ",
    "CONSTRUCTORA ALERCE", "CONSTRUCTORA NAHMIAS", "CONSTRUCTORA SAN JOSÉ",
    "DLP CONSTRUCTORA", "PC FACTORY", "CASA & IDEAS", "DECATHLON CHILE",
    "CASA ROYAL", "DVIGI", "MTS", "SUPERMERCADOS ACUENTA", "DIJON", "INFANTI",
    "BABY INFANTI", "SONDA", "APIUX", "COASIN", "QUINTEC", "EVERIS CHILE",
    "TATA CONSULTANCY CHILE", "ACCENTURE CHILE", "COGNIZANT CHILE", "GLOBANT CHILE",
    "THOUGHTWORKS CHILE", "LABORATORIO KNOP", "LABORATORIO GRÜNENTHAL",
    "LABORATORIO MAVER", "CLÍNICA UNIVERSIDAD DE LOS ANDES", "CLÍNICA BICENTENARIO",
    "CLÍNICA CIUDAD DEL MAR", "CLÍNICA REÑACA", "CLÍNICA TABANCURA", "INTEGRAMÉDICA",
    "MEGASALUD", "IDEAL S.A.", "EVERCRISP", "MARCO POLO", "BRESLER", "SAVORY",
    "TRENDY FOODS", "EMPRESAS IANSA", "SOPRODI", "EMPRESAS TUCAPEL", "WATT'S ALIMENTOS",
    "EMPRESA DE TRANSPORTE RURAL", "BUSES JAC", "BUSES FERNÁNDEZ", "TRANSPORTES CVU",
    "TRANSPORTES EUROBUS", "SAAM LOGISTICS", "ULTRAMAR", "NELTUME PORTS",
    "PUERTO CENTRAL", "SERVICIOS AEROPORTUARIOS AEROSAN", "UNIVERSIDAD DEL DESARROLLO",
    "UNIVERSIDAD MAYOR", "UNIVERSIDAD DIEGO PORTALES", "UNIVERSIDAD ALBERTO HURTADO",
    "UNIVERSIDAD SAN SEBASTIÁN", "UNIVERSIDAD VIÑA DEL MAR",
    "UNIVERSIDAD TÉCNICA FEDERICO SANTA MARÍA", "INSTITUTO PROFESIONAL AIEP",
    "INSTITUTO PROFESIONAL LOS LEONES", "CFT SANTO TOMÁS", "MINERA CAROLA",
    "MINERA ALTOS DE PUNITAQUI", "MINERA RAFAELA", "MINERA PULLALLI", "KOMATSU CHILE",
    "FINNING CHILE", "LIEBHERR CHILE", "ATLAS COPCO CHILE", "SANDVIK CHILE",
    "ORICA CHILE", "CGE DISTRIBUCIÓN", "ENEL DISTRIBUCIÓN", "GRUPO SAESA",
    "AGUAS ANDINAS", "AGUAS ARAUCANÍA", "AGUAS DEL VALLE", "AGUAS CHAÑAR",
    "AGUAS DÉCIMA", "AGUAS MAGALLANES", "AGUAS PATAGONIA", "BERETTA REPUESTOS",
    "CUMMINS CHILE", "VOLVO CHILE", "SCANIA CHILE", "MAN TRUCK & BUS CHILE",
    "ISUZU CHILE", "CHEVROLET CHILE", "FORD CHILE", "HONDA CHILE", "YAMAHA MOTOR CHILE",
    "EY CHILE", "PWC CHILE", "DELOITTE CHILE", "KPMG CHILE", "BDO CHILE",
    "GRANT THORNTON CHILE", "RSM CHILE", "BAKER TILLY CHILE", "CROWE CHILE",
    "NEXIA CHILE", "CANAL 13", "MEGA MEDIA", "TVN", "CHV", "RADIO BÍO BÍO",
    "RADIO COOPERATIVA", "EL MERCURIO S.A.P.", "LA TERCERA", "COPESA", "CINEMARK CHILE",
    "SPORTLIFE", "PACIFIC FITNESS", "ENERGY FITNESS", "O2 FIT",
    "CLUB DEPORTIVO UNIVERSIDAD CATÓLICA", "CLUB DEPORTIVO UNIVERSIDAD DE CHILE",
    "CLUB SOCIAL Y DEPORTIVO COLO-COLO", "ESTADIO ESPAÑOL", "CLUB DE GOLF LOS LEONES",
    "PRINCE OF WALES COUNTRY CLUB", "VULCO WEIR", "KAESER COMPRESORES", "COMASA",
    "LIPIGAS EMPRESAS", "AIR LIQUIDE CHILE", "PRAXAIR CHILE", "INDURA", "ENAEX",
    "FAMAE", "ASMAR MAGALLANES", "MERCADO PAGO CHILE", "KHIPU", "MULTICAJA",
    "FLOW CHILE", "WEBPAY PLUS", "KUSHKI CHILE", "PAYKU", "PAGO FÁCIL", "SERVIPAG",
    "SENCILLITO", "ULTRAMAR AGENCIA MARÍTIMA", "IAN TAYLOR CHILE",
    "MEDITERRANEAN SHIPPING CHILE", "HAPAG-LLOYD CHILE", "MAERSK CHILE",
    "EVERGREEN CHILE", "HAMBURG SÜD CHILE", "CMA CGM CHILE", "COSCO SHIPPING CHILE",
    "ONE LINE CHILE", "VEOLIA CHILE", "SUEZ CHILE", "STERICYCLE CHILE", "HIDRONOR",
    "BRAVO ENERGY", "RECYCLA CHILE", "TRICICLOS", "MIDAS CHILE", "RESITER", "DEGRAF",
    "CLUB HÍPICO DE SANTIAGO", "HIPÓDROMO CHILE", "VALPARAÍSO SPORTING CLUB",
    "BOLSA DE COMERCIO DE SANTIAGO", "BOLSA ELECTRÓNICA DE CHILE",
    "DEPÓSITO CENTRAL DE VALORES", "CÁMARA DE COMERCIO DE SANTIAGO",
    "ASOCIACIÓN DE AFP", "ASOCIACIÓN CHILENA DE ASEGURADORAS", "CASINO DE VIÑA DEL MAR",
    "LOTERÍA DE CONCEPCIÓN", "POLLA CHILENA DE BENEFICENCIA", "EMPRESAS LA FÁBRICA",
    "FÁBRICA DE PAPELES CORDILLERA", "CRISTORO", "INMOBILIARIA MIRADOR",
    "VIÑEDOS EMILIANA", "AGRÍCOLA SANTA MARTA", "PESQUERA IQUIQUE-GUANAYE",
    "SCHWAGER ENERGY", "BANCO DE CHILE", "BANCO SANTANDER CHILE", "BANCO ESTADO",
    "BANCO BCI", "BANCO ITAÚ CHILE", "BANCO SCOTIABANK CHILE", "BANCO SECURITY",
    "BANCO CONSORCIO", "BANCO INTERNACIONAL", "BANCO EDWARDS CITI", "BANCO FALABELLA",
    "BANCO BTG PACTUAL CHILE", "BANCO BICE", "JP MORGAN CHASE BANK", "BANK OF AMERICA",
    "THE BANK OF NEW YORK MELLON", "HSBC BANK CHILE", "BANCO DO BRASIL",
    "CHINA CONSTRUCTION BANK", "ORIENCOOP", "CAPUAL", "DETACOOP", "AHORROCOOP"
}

# Categorías de hechos esenciales y sus palabras clave
CATEGORIAS_HECHOS = {
    "CRITICO": {
        "peso": 9,
        "keywords": [
            # Cambios de control
            "toma de control", "cambio de control", "opa", "oferta publica de adquisicion",
            "venta de control", "controlador", "adquisicion de control",
            
            # M&A
            "fusion", "fusión", "adquisicion", "adquisición", "compra de empresa", "venta de filial", 
            "merger", "spin off", "division", "división", "escision", "escisión", 
            "venta de activos estrategicos", "venta de activos estratégicos",
            "constitución de sociedades", "constitucion de sociedades",
            
            # Profit warnings
            "profit warning", "advertencia de resultados", "deterioro significativo",
            "perdida significativa", "impacto negativo material", "revision a la baja",
            
            # Reestructuración financiera
            "reorganizacion judicial", "quiebra", "insolvencia", "default",
            "incumplimiento de covenant", "aceleracion de deuda", "cesacion de pagos",
            "reestructuracion de deuda", "reestructuracion financiera"
        ]
    },
    
    "IMPORTANTE": {
        "peso": 7.5,
        "keywords": [
            # Cambios en alta gerencia y administración (SIEMPRE incluir)
            "renuncia gerente general", "renuncia ceo", "cambio gerente general",
            "cambio ceo", "renuncia cfo", "cambio cfo", "renuncia presidente",
            "cambio presidente directorio", "cambio de administracion", "cambio de administración",
            "cambios en la administracion", "cambios en la administración",
            "nuevo gerente general", "nombra gerente general", "designa gerente general",
            "nombramiento gerente", "asume como gerente general",
            
            # Compra/venta de acciones (SIEMPRE incluir)
            "compra de acciones", "venta de acciones", "adquisicion de acciones",
            "adquisición de acciones", "enajenacion de acciones", "enajenación de acciones",
            "transaccion de acciones", "transacción de acciones", "compraventa de acciones",
            
            # Búsqueda de inversionistas (SIEMPRE incluir)
            "busqueda de inversionista", "búsqueda de inversionista",
            "busqueda de socio estrategico", "búsqueda de socio estratégico",
            "proceso de venta", "proceso de búsqueda", "inversionista estrategico",
            "inversionista estratégico", "socio estrategico", "socio estratégico",
            
            # Aumentos/disminuciones de capital (SIEMPRE incluir)
            "aumento de capital", "disminucion de capital", "disminución de capital",
            "reduccion de capital", "reducción de capital", "ampliacion de capital",
            "ampliación de capital",
            
            # Emisiones significativas (removidas colocaciones)
            "emisión de bonos", "emisión de acciones",
            "programa de emisión", "emisión de deuda",
            "oferta de bonos", "oferta pública de bonos",
            # Sin tildes para compatibilidad
            "emision de bonos", "emision de acciones",
            "programa de emision", "emision de deuda",
            
            # Contratos materiales
            "contrato material", "adjudicacion", "licitacion ganada",
            "joint venture", "alianza estrategica", "contrato significativo",
            "acuerdo comercial relevante", "contrato por usd", "contrato por uf",
            
            # Inversiones significativas
            "inversion significativa", "adquisicion de activos", "compra de propiedad",
            "proyecto de expansion", "nueva planta", "ampliacion de capacidad"
        ]
    },
    
    "MODERADO": {
        "peso": 5.5,
        "keywords": [
            # Resultados y juntas
            "fecu", "resultados trimestrales", "estados financieros",
            "junta de accionistas", "junta extraordinaria", "citacion a junta",
            "dividendo", "reparto de utilidades", "politica de dividendos",
            
            # Cambios menores
            "cambio de director", "renuncia de director", "nombramiento director",
            "cambio de ejecutivo", "modificacion estatutos", "reforma estatutos"
        ]
    },
    
    "RUTINARIO": {
        "peso": 2,
        "keywords": [
            # Procedimientos administrativos
            "cambio de domicilio", "cambio de direccion", "actualizacion de registro",
            "certificado", "inscripcion", "comunicacion de hecho", "fe de erratas",
            "rectificacion", "complemento", "aclaracion"
        ]
    }
}

def es_empresa_ipsa(nombre_empresa):
    """Verifica si la empresa pertenece al IPSA"""
    nombre_upper = nombre_empresa.upper().strip()
    for empresa_ipsa in EMPRESAS_IPSA:
        if empresa_ipsa in nombre_upper or nombre_upper in empresa_ipsa:
            return True
    return False

def es_empresa_estrategica(nombre_empresa):
    """Verifica si la empresa es estratégica (IPSA o adicional)"""
    if es_empresa_ipsa(nombre_empresa):
        return True
    
    nombre_upper = nombre_empresa.upper().strip()
    for empresa in EMPRESAS_ESTRATEGICAS:
        if empresa in nombre_upper or nombre_upper in empresa:
            return True
    return False

def evaluar_criticidad_hecho(titulo, materia, entidad, resumen=""):
    """
    Evalúa la criticidad de un hecho esencial basado en criterios profesionales
    
    Returns:
        tuple: (categoria, peso_base, es_prioritaria)
    """
    # Incluir resumen en la evaluación para capturar contenido real cuando materia es "Otros"
    texto_completo = f"{titulo} {materia} {resumen}".lower()
    es_prioritaria = es_empresa_estrategica(entidad)
    
    # Evaluar cada categoría
    for categoria, info in CATEGORIAS_HECHOS.items():
        for keyword in info["keywords"]:
            if keyword in texto_completo:
                return categoria, info["peso"], es_prioritaria
    
    # Por defecto es rutinario
    return "RUTINARIO", CATEGORIAS_HECHOS["RUTINARIO"]["peso"], es_prioritaria

def es_empresa_prioritaria(nombre_empresa):
    """
    Verifica si la empresa es prioritaria (IPSA o de las 500 empresas importantes)
    Estas empresas siempre tendrán sus hechos incluidos
    """
    # Primero verificar si es IPSA
    if es_empresa_ipsa(nombre_empresa):
        return True
    
    # Luego verificar si está en las empresas estratégicas originales
    if es_empresa_estrategica(nombre_empresa):
        return True
    
    # Las 500 empresas importantes se verifican en es_empresa_estrategica
    return False

def calcular_relevancia_profesional(titulo, materia, entidad, contexto_adicional=""):
    """
    Calcula la relevancia final usando criterios profesionales
    
    Args:
        titulo: Título del hecho esencial
        materia: Materia del hecho
        entidad: Nombre de la empresa
        contexto_adicional: Información adicional (montos, impactos, resumen, etc)
    
    Returns:
        tuple: (relevancia_final, categoria, es_ipsa)
    """
    # Pasar contexto adicional como resumen para evaluar contenido real
    categoria, peso_base, es_prioritaria = evaluar_criticidad_hecho(titulo, materia, entidad, contexto_adicional)
    es_ipsa = es_empresa_ipsa(entidad)
    
    # Relevancia base según categoría
    relevancia = peso_base
    
    # Empresas prioritarias (IPSA + 500 importantes) siempre se incluyen con relevancia alta
    if es_ipsa or es_prioritaria:
        # Garantizar mínimo de 7.0 para empresas prioritarias (siempre se incluyen)
        relevancia = max(relevancia + 2.5, 7.0)
    
    # Factores adicionales del contexto
    contexto_lower = contexto_adicional.lower()
    
    # Bonus por montos significativos
    if any(word in contexto_lower for word in ["millon", "billion", "significativo"]):
        if "usd" in contexto_lower or "dolares" in contexto_lower:
            relevancia += 0.5
    
    # Bonus por impacto en resultados
    if any(word in contexto_lower for word in ["ebitda", "utilidad", "margen"]):
        if any(word in contexto_lower for word in ["10%", "20%", "30%", "40%", "50%"]):
            relevancia += 0.5
    
    # Cap máximo de 10
    relevancia = min(relevancia, 10)
    
    return relevancia, categoria, es_ipsa

def obtener_prompt_profesional(titulo, materia, entidad, contenido, categoria, es_ipsa):
    """
    Genera un prompt especializado según la categoría del hecho y si es IPSA
    """
    tipo_empresa = "[Empresa IPSA]" if es_ipsa else ""
    
    prompt_base = f"""
    Analiza el siguiente Hecho Esencial de {entidad} {tipo_empresa}.
    
    CATEGORÍA DETECTADA: {categoria}
    
    Tu tarea es crear un resumen ejecutivo profesional considerando:
    
    1. RESUMEN CONCISO (2-4 frases):
       - Primera frase: El hecho principal y su impacto
       - Siguientes frases: Detalles clave, montos, plazos
       - Enfoque en lo que importa a inversionistas institucionales
    
    2. DATOS CLAVE A EXTRAER:
    """
    
    if categoria == "CRITICO":
        prompt_base += """
       - Tipo de transacción (OPA, fusión, venta, etc.)
       - Contrapartes involucradas
       - Valorización o precio si está disponible
       - Impacto esperado en la empresa
       - Timeline de la operación
       - Condiciones precedentes importantes
    """
    elif categoria == "IMPORTANTE":
        prompt_base += """
       - Cargo específico del cambio gerencial (si aplica)
       - Monto de la emisión (si aplica)
       - Uso de los fondos (si aplica)
       - Términos clave del contrato (si aplica)
       - Impacto esperado en operaciones
    """
    elif categoria == "MODERADO":
        prompt_base += """
       - Métricas financieras clave (ingresos, EBITDA, utilidad)
       - Variaciones respecto al período anterior
       - Fecha y tipo de junta (si aplica)
       - Monto de dividendo por acción (si aplica)
    """
    
    prompt_base += f"""
    
    3. RELEVANCIA PARA EL MERCADO:
       - Impacto esperado en el precio de la acción
       - Importancia para el sector
       - Precedentes o comparables si son relevantes
    
    FORMATO DE RESPUESTA:
    {{
        "resumen": "Resumen ejecutivo claro y profesional",
        "relevancia": número entre 1-10 (ya calculado: {categoria}),
        "datos_clave": {{
            "monto": "si aplica",
            "plazo": "si aplica",
            "impacto": "descripción del impacto"
        }}
    }}
    
    Título: {titulo}
    Materia: {materia}
    
    Contenido del documento:
    {contenido[:3000]}
    """
    
    return prompt_base

def get_icono_categoria(categoria):
    """Retorna el ícono según la categoría"""
    iconos = {
        "CRITICO": "🔴",
        "IMPORTANTE": "🟡", 
        "MODERADO": "🟢",
        "RUTINARIO": "⚪"
    }
    return iconos.get(categoria, "⚪")

def filtrar_hechos_profesional(hechos, max_hechos=12):
    """
    Filtra hechos esenciales según criterios profesionales
    Máximo 12 hechos, priorizando por relevancia
    
    Reglas de filtrado actualizadas:
    - Máximo 12 hechos
    - Incluir SIEMPRE (relevancia >= 7):
      * Todas las empresas IPSA (sin importar la materia)
      * Todas las empresas de la lista de 500 empresas importantes (sin importar la materia)
      * Cambios en la administración
      * Compra/venta de acciones
      * División, fusión o constitución de sociedades
      * Búsqueda de inversionistas o socios estratégicos
      * Aumentos o disminuciones de capital
    - EXCLUIR siempre:
      * Todos los fondos de inversión
      * Colocación de valores (bonos, acciones, etc.)
      * Todas las compañías de seguros
      * Hechos con relevancia < 7
    """
    # Primero, filtrar hechos relacionados con fondos, colocación de valores y compañías de seguros
    hechos_filtrados = []
    for hecho in hechos:
        titulo = hecho.get('titulo', '').lower()
        materia = hecho.get('materia', '').lower()
        entidad = hecho.get('entidad', '').lower()
        resumen = hecho.get('resumen', '').lower()
        
        # Excluir si contiene palabras relacionadas con fondos
        es_fondo = any(palabra in titulo or palabra in materia or palabra in entidad 
                      for palabra in ['fondo', 'fondos', 'fund', 'funds', 'fip', 'fia', 
                                     'fondo de inversion', 'fondo mutuo', 'mutual fund',
                                     'investment fund', 'fondo inmobiliario'])
        
        # Excluir si es colocación de valores
        es_colocacion = any(palabra in titulo or palabra in materia or palabra in resumen
                           for palabra in ['colocación de valores', 'colocacion de valores',
                                          'colocación de bonos', 'colocacion de bonos',
                                          'colocación exitosa', 'colocacion exitosa',
                                          'colocación de acciones', 'colocacion de acciones',
                                          'colocación en el mercado', 'colocacion en el mercado',
                                          'colocación internacional', 'colocacion internacional'])
        
        # Excluir si es compañía de seguros
        es_seguro = any(palabra in entidad 
                       for palabra in ['seguro', 'seguros', 'aseguradora', 'aseguradoras',
                                      'insurance', 'vida security', 'metlife', 'consorcio seguros',
                                      'bice vida', 'euroamerica', 'ohio national', 'principal seguros',
                                      'zurich santander', 'confuturo', 'chilena consolidada',
                                      'sura', 'mapfre', 'liberty', 'rsa', 'hdi', 'bci seguros',
                                      'santander seguros', 'compañía de seguros', 'compania de seguros',
                                      'cia de seguros', 'cia. de seguros', 'cía de seguros',
                                      'cía. de seguros', 'rigel', 'reale chile'])
        
        # También excluir si la materia menciona seguros específicamente
        es_materia_seguros = any(palabra in materia 
                                for palabra in ['poliza', 'póliza', 'siniestro', 'prima', 'reaseguro',
                                              'cobertura de seguro', 'contrato de seguro'])
        
        if not es_fondo and not es_colocacion and not es_seguro and not es_materia_seguros:
            hechos_filtrados.append(hecho)
        else:
            if es_fondo:
                print(f"  → Excluido (es fondo): {hecho.get('entidad', '')} - {hecho.get('titulo', '')[:50]}...")
            elif es_colocacion:
                print(f"  → Excluido (colocación de valores): {hecho.get('entidad', '')} - {hecho.get('titulo', '')[:50]}...")
            elif es_seguro or es_materia_seguros:
                print(f"  → Excluido (compañía de seguros): {hecho.get('entidad', '')} - {hecho.get('titulo', '')[:50]}...")
    
    # Calcular relevancia para cada hecho que no es fondo ni colocación
    hechos_evaluados = []
    
    for hecho in hechos_filtrados:
        titulo = hecho.get('titulo', '')
        materia = hecho.get('materia', '')
        entidad = hecho.get('entidad', '')
        resumen = hecho.get('resumen', '')
        
        # Calcular relevancia usando la función existente
        # Pasar resumen como contexto para detectar contenido real cuando materia es "Otros"
        relevancia, categoria, es_ipsa = calcular_relevancia_profesional(
            titulo, materia, entidad, resumen
        )
        
        # Agregar información de relevancia al hecho
        hecho_evaluado = hecho.copy()
        hecho_evaluado['relevancia_calculada'] = relevancia
        hecho_evaluado['categoria_relevancia'] = categoria
        hecho_evaluado['es_ipsa'] = es_ipsa
        
        hechos_evaluados.append(hecho_evaluado)
    
    # Con los nuevos criterios, solo incluimos hechos con relevancia >= 7
    # Esto incluye automáticamente:
    # - Todas las empresas IPSA (mínimo 7.0)
    # - Cambios en administración (7.5)
    # - Compra/venta de acciones (7.5)
    # - Fusiones/divisiones (9.0)
    # - Búsqueda de inversionistas (7.5)
    # - Aumentos/disminuciones de capital (7.5)
    
    hechos_relevantes = [h for h in hechos_evaluados if h['relevancia_calculada'] >= 7]
    
    # Ordenar por relevancia descendente
    hechos_finales = sorted(hechos_relevantes, key=lambda x: x['relevancia_calculada'], reverse=True)
    
    # Asegurar que no excedemos el máximo
    hechos_finales = hechos_finales[:max_hechos]
    
    # Log de filtrado para transparencia
    print(f"\n=== Filtrado Profesional CMF ===")
    print(f"Total hechos originales: {len(hechos)}")
    print(f"- Excluidos (fondos + colocaciones + seguros): {len(hechos) - len(hechos_filtrados)}")
    print(f"- Hechos con relevancia >= 7 (incluidos): {len(hechos_relevantes)}")
    print(f"- Hechos con relevancia < 7 (excluidos): {len(hechos_evaluados) - len(hechos_relevantes)}")
    print(f"Total hechos seleccionados: {len(hechos_finales)}")
    print(f"\nCriterios aplicados:")
    print(f"- Empresas IPSA: SIEMPRE incluidas (relevancia mínima 7.0)")
    print(f"- 500 empresas importantes: SIEMPRE incluidas (relevancia mínima 7.0)")
    print(f"- Cambios en administración: SIEMPRE incluidos")
    print(f"- Compra/venta de acciones: SIEMPRE incluidos")
    print(f"- Fusiones/divisiones: SIEMPRE incluidos")
    print(f"- Búsqueda inversionistas: SIEMPRE incluidos")
    print(f"- Aumentos/disminuciones capital: SIEMPRE incluidos")
    print(f"- Colocación de valores: SIEMPRE EXCLUIDOS")
    print(f"- Compañías de seguros: SIEMPRE EXCLUIDAS")
    print(f"================================\n")
    
    return hechos_finales

def aplicar_regla_dorada(hecho):
    """
    Aplica la regla dorada: "¿Le importaría esto a un inversionista institucional?"
    """
    relevancia = hecho.get('relevancia_calculada', 0)
    es_ipsa = hecho.get('es_ipsa', False)
    categoria = hecho.get('categoria_relevancia', 'RUTINARIO')
    
    # Un inversionista institucional se interesa en:
    # 1. Cualquier hecho crítico o importante (relevancia >= 7)
    # 2. Hechos moderados solo si son de empresas IPSA
    # 3. Nunca en hechos rutinarios
    
    if relevancia >= 7:
        return True
    elif relevancia >= 5 and es_ipsa:
        return True
    else:
        return False