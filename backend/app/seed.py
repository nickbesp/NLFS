"""Hand-written sample content for the prototype. Seeded once into an empty database."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models

TOPICS = [
    {
        "level": "A1",
        "title": "Ser vs Estar",
        "content": """\
Spanish has two verbs for *to be*.

## Ser — what something **is**
Identity, origin, profession, time, and where an **event** takes place.

- *Soy estudiante.* — I am a student.
- *Es de México.* — He/She is from Mexico.
- *La fiesta es en mi casa.* — The party is at my house.

## Estar — how or where something **is right now**
States, feelings, and the location of people and things.

- *Estoy cansado.* — I am tired.
- *Estamos en Madrid.* — We are in Madrid.
- *El café está frío.* — The coffee is cold.

> Tip: ask yourself *"Is this a characteristic, or a condition?"*
""",
        "cards": [
            ("Soy estudiante", "I am a student"),
            ("Estoy cansado", "I am tired"),
            ("Es de México", "He is from Mexico"),
            ("La fiesta es en mi casa", "The party is at my house"),
            ("Estamos en Madrid", "We are in Madrid"),
            ("El café está frío", "The coffee is cold"),
        ],
    },
    {
        "level": "A1",
        "title": "Artículos y género",
        "content": """\
Every noun is **masculine** or **feminine**, and the article agrees with it.

| | Singular | Plural |
|---|---|---|
| Masculine | el | los |
| Feminine | la | las |

- Most nouns ending in **-o** are masculine: *el libro*.
- Most nouns ending in **-a** are feminine: *la casa*.
- Watch the exceptions: *el problema*, *la mano*.
- Feminine nouns starting with a stressed **a-** take *el* in the singular: *el agua*.
- Nouns ending in **-dad / -ción** are feminine: *las ciudades*.
""",
        "cards": [
            ("el libro", "the book"),
            ("la casa", "the house"),
            ("el problema", "the problem"),
            ("la mano", "the hand"),
            ("el agua", "the water"),
            ("las ciudades", "the cities"),
        ],
    },
    {
        "level": "A1",
        "title": "Presente regular",
        "content": """\
Regular verbs drop **-ar / -er / -ir** and add the present endings.

| | hablar | comer | vivir |
|---|---|---|---|
| yo | habl**o** | com**o** | viv**o** |
| tú | habl**as** | com**es** | viv**es** |
| él/ella | habl**a** | com**e** | viv**e** |
| nosotros | habl**amos** | com**emos** | viv**imos** |
| vosotros | habl**áis** | com**éis** | viv**ís** |
| ellos | habl**an** | com**en** | viv**en** |

- *Trabajo en una oficina.* — I work in an office.
- *Escribimos un correo.* — We write an email.
""",
        "cards": [
            ("hablar", "to speak"),
            ("comer", "to eat"),
            ("vivir", "to live"),
            ("trabajo", "I work"),
            ("escribimos", "we write"),
            ("aprenden", "they learn"),
        ],
    },
    {
        "level": "B1",
        "title": "Presente de subjuntivo",
        "content": """\
The subjunctive expresses **wishes, doubts, emotions and the not-yet-real**.
It usually appears after *que* when the main clause has a different subject.

## Formation
Take the *yo* form of the present, drop the **-o**, and swap the vowel:
**-ar → -e**, **-er/-ir → -a**. *hablo → hable*, *tengo → tenga*.

## Common triggers
- Wishes: *Quiero que vengas.*
- Hope: *Espero que tengas suerte.*
- Judgements: *Es importante que estudies.*
- Doubt: *Dudo que llueva.*
- *Ojalá*: *Ojalá haga sol.*
- Future time with *cuando*: *Cuando llegues, llámame.*
""",
        "cards": [
            ("Quiero que vengas", "I want you to come"),
            ("Espero que tengas suerte", "I hope you get lucky"),
            ("Es importante que estudies", "It is important that you study"),
            ("Dudo que llueva", "I doubt it will rain"),
            ("Ojalá haga sol", "Hopefully it will be sunny"),
            ("Cuando llegues, llámame", "When you arrive, call me"),
        ],
    },
    {
        "level": "B1",
        "title": "Por vs Para",
        "content": """\
Both can mean *for*, but they look in different directions.

## Para — destination and purpose (→)
- Recipient: *Este regalo es para ti.*
- Destination: *Salgo para Madrid.*
- Purpose (*in order to*): *Estudio para aprender.*

## Por — cause, exchange and route (←)
- Reason / gratitude: *Gracias por todo.*
- Movement through: *Paseamos por el parque.*
- Exchange / price: *Lo compré por diez euros.*
""",
        "cards": [
            ("Gracias por todo", "Thanks for everything"),
            ("Este regalo es para ti", "This gift is for you"),
            ("Salgo para Madrid", "I am leaving for Madrid"),
            ("Paseamos por el parque", "We walk through the park"),
            ("Estudio para aprender", "I study in order to learn"),
            ("Lo compré por diez euros", "I bought it for ten euros"),
        ],
    },
]


def seed_if_empty(db: Session) -> bool:
    """Insert the sample topics and cards if there are no topics yet. Returns True if seeded."""
    if db.scalar(select(models.TheoryTopic.id).limit(1)) is not None:
        return False

    order_by_level: dict[str, int] = {}
    for t in TOPICS:
        order_by_level[t["level"]] = order_by_level.get(t["level"], 0) + 1
        topic = models.TheoryTopic(
            level=t["level"], title=t["title"], content=t["content"], order_index=order_by_level[t["level"]]
        )
        topic.cards = [
            models.Flashcard(spanish=es, english=en, category=t["title"], srs=models.SrsState()) for es, en in t["cards"]
        ]
        db.add(topic)
    db.commit()
    return True
