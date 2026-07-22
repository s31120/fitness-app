"""Programmes d'entraînement prédéfinis (templates)."""

TEMPLATES = {
    "ppl": {
        "id": "ppl",
        "name": "Push / Pull / Legs",
        "description": "3 séances par semaine, split classique",
        "days": [
            {
                "name": "Push",
                "exercises": [
                    {"name": "Développé couché", "sets": 4, "reps": 8},
                    {"name": "Développé militaire", "sets": 3, "reps": 10},
                    {"name": "Dips", "sets": 3, "reps": 12},
                    {"name": "Extensions triceps", "sets": 3, "reps": 12},
                ],
            },
            {
                "name": "Pull",
                "exercises": [
                    {"name": "Tractions", "sets": 4, "reps": 8},
                    {"name": "Rowing barre", "sets": 4, "reps": 10},
                    {"name": "Curl biceps", "sets": 3, "reps": 12},
                    {"name": "Face pull", "sets": 3, "reps": 15},
                ],
            },
            {
                "name": "Legs",
                "exercises": [
                    {"name": "Squat", "sets": 4, "reps": 8},
                    {"name": "Soulevé de terre roumain", "sets": 3, "reps": 10},
                    {"name": "Fentes", "sets": 3, "reps": 12},
                    {"name": "Mollets", "sets": 4, "reps": 15},
                ],
            },
        ],
    },
    "upper_lower": {
        "id": "upper_lower",
        "name": "Upper / Lower",
        "description": "2 séances par semaine, haut/bas du corps",
        "days": [
            {
                "name": "Upper",
                "exercises": [
                    {"name": "Développé couché", "sets": 4, "reps": 8},
                    {"name": "Rowing barre", "sets": 4, "reps": 10},
                    {"name": "Développé militaire", "sets": 3, "reps": 10},
                    {"name": "Curl biceps", "sets": 3, "reps": 12},
                ],
            },
            {
                "name": "Lower",
                "exercises": [
                    {"name": "Squat", "sets": 4, "reps": 8},
                    {"name": "Soulevé de terre", "sets": 3, "reps": 6},
                    {"name": "Fentes", "sets": 3, "reps": 12},
                    {"name": "Mollets", "sets": 4, "reps": 15},
                ],
            },
        ],
    },
    "full_body": {
        "id": "full_body",
        "name": "Full Body",
        "description": "3 séances par semaine, corps entier à chaque fois",
        "days": [
            {
                "name": "Full Body",
                "exercises": [
                    {"name": "Squat", "sets": 3, "reps": 8},
                    {"name": "Développé couché", "sets": 3, "reps": 8},
                    {"name": "Rowing barre", "sets": 3, "reps": 10},
                    {"name": "Développé militaire", "sets": 3, "reps": 10},
                    {"name": "Soulevé de terre roumain", "sets": 3, "reps": 10},
                ],
            },
        ],
    },
}
