job_pipeline/
│
├── model/                          # Capa de datos
│   ├── database/
│   │   ├── schema.sql              # DDL: tabla jobs, índices
│   │   ├── migrations/             # Cambios de schema versionados
│   │   └── db_connection.py        # Singleton de conexión PostgreSQL
│   ├── connectors/
│   │   ├── base_connector.py       # Clase abstracta con fetch/normalize
│   │   ├── jobbank.py              # API REST oficial gobierno Canada
│   │   ├── adzuna.py               # API con key
│   │   ├── jooble.py               # API con key
│   │   ├── remoteok.py             # API pública JSON sin key
│   │   ├── linkedin.py             # jobspy
│   │   └── indeed.py               # jobspy
│   ├── job.py                      # Dataclass Job — schema normalizado
│   ├── job_repository.py           # CRUD contra PostgreSQL
│   └── deduplicator.py             # Hash + fuzzy match entre fuentes
│
├── controller/                     # Lógica de negocio
│   ├── pipeline.py                 # Orquestador: corre las 6 fuentes en paralelo
│   ├── scoring_engine.py           # TF-IDF + cosine similarity contra perfil
│   ├── nlp_processor.py            # spaCy: extrae skills, detecta francés, seniority
│   └── job_service.py              # Interfaz entre controller y view
│
├── view/                           # Streamlit UI
│   ├── app.py                      # Entry point y routing de páginas
│   ├── pages/
│   │   ├── dashboard.py            # Tabla principal con scores y filtros
│   │   ├── job_detail.py           # Vista completa del JD + score breakdown
│   │   ├── analytics.py            # Trending skills, demanda por ciudad
│   │   └── profile_config.py       # Editor del profile.yaml desde la UI
│   └── components/
│       ├── job_card.py             # Card individual reutilizable
│       ├── score_bar.py            # Barra de relevancia con breakdown
│       └── filter_panel.py         # Sidebar de filtros
│
├── config/
│   ├── profile.yaml                # Tu perfil: skills, títulos, pesos
│   ├── settings.yaml               # Fuentes activas, threshold, schedule
│   └── .env                        # API keys — gitignored
│
├── tests/
│   ├── test_scoring.py
│   ├── test_connectors.py
│   └── fixtures/
│       └── sample_jobs.json        # Respuestas mock para tests
│
├── requirements.txt
├── Makefile                        # make run · make test · make dashboard
├── .gitignore
└── README.md                       # Portfolio showcase con screenshots



Resumen de donde estamos — Sprint 0:
✅ Estructura MVC creada
✅ Git + GitHub conectados
✅ Todos los paquetes instalados
✅ spaCy model descargado
✅ .env protegido del repo

⬜ schema.sql — siguiente paso
⬜ db_connection.py
⬜ job.py (dataclass)
⬜ base_connector.py
⬜ Job Bank connector
Siguiente — crear la base de datos en MySQL.
Primero conéctate a MySQL: