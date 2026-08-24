# Euskal Toponimia Generator

Generador experimental de toponimia vasca, histórica y proto-vasca.

## Qué hace

El proyecto separa cuatro capas:

1. **léxico**: raíces y formantes;
2. **morfología**: patrones y restricciones de combinación;
3. **composición**: alternancias morfofonológicas;
4. **evolución histórica/experimental**: variantes opcionales.

Incluye un catálogo inicial de **120 entradas** con forma, significado, categoría, tipo, posición, variantes, productividad, antigüedad y restricciones.

> Una forma generada no equivale a un topónimo históricamente atestiguado.

## Modos

- `documental`: selección conservadora.
- `vasco`: generación productiva de formas plausibles.
- `historico`: añade variantes históricas opcionales.
- `proto`: modo experimental; no debe interpretarse como reconstrucción lingüística certificada.

## Uso

Requiere Python 3.10+ y no necesita dependencias externas.

```bash
python generator.py -n 20 -m vasco
python generator.py -n 20 -m historico
python generator.py -n 20 -m proto --seed 42
```

## Estructura

```text
.
├── generator.py
├── data/
│   ├── elements.json
│   ├── patterns.json
│   └── rules.json
├── tests/
│   └── test_generator.py
├── README.md
├── LICENSE
└── .gitignore
```

## Modelo de datos

Cada elemento registra:

- `form`: forma de salida;
- `meaning`: significado operativo;
- `category`: relieve, agua, vegetación, fauna, asentamiento, etc.;
- `kind`: lexema, formante o sufijo;
- `positions`: posición permitida;
- `variants`: variantes;
- `productivity`: peso de selección del generador;
- `antiquity`: clasificación operativa;
- `combination_tags`: categorías que permiten reglas de combinación;
- `restrictions`: restricciones legibles.

La productividad **no es una frecuencia estadística**.

## Reglas

La implementación separa reglas de composición de reglas históricas.

Entre las reglas de composición se modelan de forma conservadora:

- `-di/-gi > -t` en determinados primeros miembros;
- `e/o/u > a` en determinados primeros miembros;
- `n > r` en determinados compuestos;
- `ra/re/ri > l` en determinados compuestos.

`-aga` y `-eta` reciben tratamiento especial: son sufijos terminales y bloquean las alternancias vocálicas ordinarias del primer miembro en este modelo.

El modo histórico/proto es deliberadamente conservador. Las transformaciones experimentales están marcadas en `rules.json`.

## Desarrollo futuro

1. Añadir fuente bibliográfica a cada entrada.
2. Añadir primera atestiguación y fecha.
3. Separar dialectos.
4. Añadir `-ain`, `-egi`, `-oz`, `-iz`, `-ain`, etc. con reglas específicas y documentación.
5. Ampliar patrones reales de composición.
6. Añadir un analizador inverso de topónimos.
7. Crear una interfaz web.
8. Añadir un modo de exportación CSV/JSON.
