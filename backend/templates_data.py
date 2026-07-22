"""
Base d'exercices classés par groupe musculaire, et programmes prédéfinis.

Prescriptions sets/reps basées sur des recommandations générales pour l'hypertrophie :
- Exercices composés (poly-articulaires) : 3-4 séries, 6-12 reps
- Exercices d'isolation : 3 séries, 12-15 reps
- Cible hebdomadaire générale : ~10 séries par groupe musculaire minimum (ACSM 2026)
- Fréquence 2x/semaine par groupe généralement supérieure à 1x/semaine pour l'hypertrophie
"""

MUSCLE_GROUPS = {
    "pectoraux": "Pectoraux",
    "dos": "Dos",
    "epaules": "Épaules",
    "biceps": "Biceps",
    "triceps": "Triceps",
    "quadriceps": "Quadriceps",
    "ischios": "Ischio-jambiers",
    "fessiers": "Fessiers",
    "mollets": "Mollets",
    "abdos": "Abdominaux",
}

# type: "compound" (poly-articulaire) ou "isolation"
EXERCISES = {
    "pectoraux": [
        {"name": "Développé couché", "type": "compound", "sets": 4, "reps": 8},
        {"name": "Développé incliné haltères", "type": "compound", "sets": 3, "reps": 10},
        {"name": "Dips", "type": "compound", "sets": 3, "reps": 10},
        {"name": "Écarté couché haltères", "type": "isolation", "sets": 3, "reps": 12},
        {"name": "Écarté à la poulie", "type": "isolation", "sets": 3, "reps": 15},
    ],
    "dos": [
        {"name": "Tractions", "type": "compound", "sets": 4, "reps": 8},
        {"name": "Rowing barre", "type": "compound", "sets": 4, "reps": 10},
        {"name": "Soulevé de terre", "type": "compound", "sets": 3, "reps": 6},
        {"name": "Rowing haltère unilatéral", "type": "compound", "sets": 3, "reps": 10},
        {"name": "Tirage vertical", "type": "compound", "sets": 3, "reps": 12},
        {"name": "Face pull", "type": "isolation", "sets": 3, "reps": 15},
    ],
    "epaules": [
        {"name": "Développé militaire", "type": "compound", "sets": 4, "reps": 8},
        {"name": "Développé Arnold", "type": "compound", "sets": 3, "reps": 10},
        {"name": "Élévations latérales", "type": "isolation", "sets": 3, "reps": 15},
        {"name": "Oiseau (élévations arrière)", "type": "isolation", "sets": 3, "reps": 15},
    ],
    "biceps": [
        {"name": "Curl biceps barre", "type": "isolation", "sets": 3, "reps": 12},
        {"name": "Curl marteau", "type": "isolation", "sets": 3, "reps": 12},
        {"name": "Curl incliné haltères", "type": "isolation", "sets": 3, "reps": 12},
    ],
    "triceps": [
        {"name": "Extensions triceps poulie", "type": "isolation", "sets": 3, "reps": 12},
        {"name": "Barre au front (skullcrusher)", "type": "isolation", "sets": 3, "reps": 12},
        {"name": "Dips triceps (prise serrée)", "type": "compound", "sets": 3, "reps": 10},
    ],
    "quadriceps": [
        {"name": "Squat", "type": "compound", "sets": 4, "reps": 8},
        {"name": "Presse à cuisses", "type": "compound", "sets": 3, "reps": 10},
        {"name": "Fentes", "type": "compound", "sets": 3, "reps": 12},
        {"name": "Leg extension", "type": "isolation", "sets": 3, "reps": 15},
    ],
    "ischios": [
        {"name": "Soulevé de terre roumain", "type": "compound", "sets": 3, "reps": 10},
        {"name": "Leg curl", "type": "isolation", "sets": 3, "reps": 12},
        {"name": "Good morning", "type": "compound", "sets": 3, "reps": 10},
    ],
    "fessiers": [
        {"name": "Hip thrust", "type": "compound", "sets": 4, "reps": 10},
        {"name": "Fentes bulgares", "type": "compound", "sets": 3, "reps": 12},
    ],
    "mollets": [
        {"name": "Mollets debout", "type": "isolation", "sets": 4, "reps": 15},
        {"name": "Mollets assis", "type": "isolation", "sets": 3, "reps": 15},
    ],
    "abdos": [
        {"name": "Crunch lesté", "type": "isolation", "sets": 3, "reps": 15},
        {"name": "Planche", "type": "isolation", "sets": 3, "reps": 1},
        {"name": "Relevé de jambes suspendu", "type": "isolation", "sets": 3, "reps": 12},
    ],
}


def build_day(name, groups):
    """Construit un jour d'entraînement en piochant les exercices des groupes musculaires donnés."""
    n_groups = len(groups)
    n_per_group = max(1, min(4, 6 // n_groups))
    exercises = []
    for g in groups:
        exercises.extend(EXERCISES[g][:n_per_group])
    return {"name": name, "muscle_groups": groups, "exercises": [
        {"name": e["name"], "sets": e["sets"], "reps": e["reps"]} for e in exercises
    ]}


TEMPLATES = {
    "full_body": {
        "id": "full_body",
        "name": "Full Body",
        "description": "3x/semaine, corps entier — idéal pour débuter",
        "days": [build_day("Full Body", ["quadriceps", "pectoraux", "dos", "epaules", "ischios"])],
    },
    "upper_lower": {
        "id": "upper_lower",
        "name": "Upper / Lower (PHUL)",
        "description": "4x/semaine, chaque groupe travaillé 2x — bon compromis force/hypertrophie",
        "days": [
            build_day("Upper", ["pectoraux", "dos", "epaules", "biceps", "triceps"]),
            build_day("Lower", ["quadriceps", "ischios", "fessiers", "mollets"]),
        ],
    },
    "ppl": {
        "id": "ppl",
        "name": "Push / Pull / Legs",
        "description": "3x/semaine, split classique par mouvement",
        "days": [
            build_day("Push", ["pectoraux", "epaules", "triceps"]),
            build_day("Pull", ["dos", "biceps"]),
            build_day("Legs", ["quadriceps", "ischios", "fessiers", "mollets"]),
        ],
    },
    "ppl_6day": {
        "id": "ppl_6day",
        "name": "PPL x2 (avancé)",
        "description": "6x/semaine, chaque groupe travaillé 2x/semaine — fréquence élevée",
        "days": [
            build_day("Push A", ["pectoraux", "epaules", "triceps"]),
            build_day("Pull A", ["dos", "biceps"]),
            build_day("Legs A", ["quadriceps", "ischios", "fessiers"]),
            build_day("Push B", ["epaules", "pectoraux", "triceps"]),
            build_day("Pull B", ["dos", "biceps"]),
            build_day("Legs B", ["ischios", "quadriceps", "mollets"]),
        ],
    },
    "arnold_split": {
        "id": "arnold_split",
        "name": "Split Arnold",
        "description": "6x/semaine — pecs+dos / épaules+bras / jambes, chaque groupe 2x/semaine",
        "days": [
            build_day("Pecs + Dos", ["pectoraux", "dos"]),
            build_day("Épaules + Bras", ["epaules", "biceps", "triceps"]),
            build_day("Jambes", ["quadriceps", "ischios", "fessiers", "mollets"]),
            build_day("Pecs + Dos (2)", ["pectoraux", "dos"]),
            build_day("Épaules + Bras (2)", ["epaules", "biceps", "triceps"]),
            build_day("Jambes (2)", ["quadriceps", "ischios", "fessiers", "mollets"]),
        ],
    },
    "bro_split": {
        "id": "bro_split",
        "name": "Bro Split",
        "description": "5x/semaine, un groupe musculaire par jour — volume élevé par séance",
        "days": [
            build_day("Pectoraux", ["pectoraux"]),
            build_day("Dos", ["dos"]),
            build_day("Jambes", ["quadriceps", "ischios", "fessiers", "mollets"]),
            build_day("Épaules", ["epaules", "abdos"]),
            build_day("Bras", ["biceps", "triceps"]),
        ],
    },
}
