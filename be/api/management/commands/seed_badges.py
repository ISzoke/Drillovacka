from django.core.management.base import BaseCommand
from api.models import Badge


BADGES = [
    # ── Aktivita ──────────────────────────────────────────────────────────────
    dict(key='first_correct',        name='Prvý gól',          description='Prvý správne vypočítaný príklad',                     icon='star',     category='activity',  xp_reward=15),
    dict(key='ten_correct',          name='Rozbehnutý',        description='25 správnych odpovedí',                               icon='ten',      category='activity',  xp_reward=30),
    dict(key='hundred_correct',      name='Stovkár',           description='100 správnych odpovedí',                              icon='hundred',  category='activity',  xp_reward=80),
    dict(key='three_hundred_correct',name='Výpočtový stroj',   description='300 správnych odpovedí',                              icon='rocket',   category='activity',  xp_reward=180),
    dict(key='five_hundred_correct', name='Päťstovkár',        description='500 správnych odpovedí',                              icon='crown',    category='activity',  xp_reward=300),
    dict(key='thousand_correct',     name='Tisícnik',          description='1000 správnych odpovedí',                             icon='gem',      category='activity',  xp_reward=600),
    dict(key='five_skills',          name='Zvedavec',          description='Precvičoval si 5 rôznych tém',                        icon='map',      category='activity',  xp_reward=35),
    dict(key='ten_skills',           name='Všestranný',        description='Precvičoval si 10 rôznych tém',                       icon='compass',  category='activity',  xp_reward=70),
    dict(key='twenty_skills',        name='Encyklopédia',      description='Precvičoval si 20 rôznych tém',                       icon='books',    category='activity',  xp_reward=150),

    # ── Presnosť ──────────────────────────────────────────────────────────────
    dict(key='comeback',             name='Tvrdohlavý',        description='Správna odpoveď po 3 chybách na tom istom príklade',  icon='muscle',   category='accuracy',  xp_reward=25),
    dict(key='ten_in_a_row',         name='Bez zakopnutia',    description='10 správnych za sebou bez jedinej chyby',             icon='bolt',     category='accuracy',  xp_reward=45),
    dict(key='twenty_five_in_a_row', name='Neomylný',          description='25 správnych za sebou bez jedinej chyby',             icon='bow',      category='accuracy',  xp_reward=100),
    dict(key='perfect_session',      name='Čistý štít',        description='Všetky príklady za deň správne (aspoň 10)',           icon='target',   category='accuracy',  xp_reward=55),
    dict(key='accuracy_master',      name='Ostreľovač',        description='90 % a viac správnych pri aspoň 100 pokusoch',        icon='grad',     category='accuracy',  xp_reward=90),
    dict(key='accuracy_legend',      name='Snajper',           description='95 % a viac správnych pri aspoň 250 pokusoch',        icon='medal',    category='accuracy',  xp_reward=200),
    dict(key='mastery_skill',        name='Zvládnuté!',        description='Zvládni akúkoľvek tému aspoň na 85 %',                icon='star2',    category='accuracy',  xp_reward=80),

    # ── Rýchlosť ──────────────────────────────────────────────────────────────
    dict(key='fast_answer',          name='Rýchlik',           description='10-krát odpoveď do 5 sekúnd',                         icon='wind',     category='speed',     xp_reward=35),
    dict(key='lightning',            name='Bleskovka',         description='10-krát odpoveď do 3 sekúnd',                         icon='car',      category='speed',     xp_reward=65),
    dict(key='speed_demon',          name='Šíp',               description='25-krát odpoveď do 3 sekúnd',                         icon='bolt',     category='speed',     xp_reward=130),
    dict(key='speed_session',        name='Na plné obrátky',   description='10 príkladov za menej ako 90 sekúnd',                 icon='wind',     category='speed',     xp_reward=50),

    # ── Séria dní ─────────────────────────────────────────────────────────────
    dict(key='streak_3',             name='Tri dni v rade',    description='Cvičil si 3 dni po sebe',                             icon='fire',     category='streak',    xp_reward=20),
    dict(key='streak_7',             name='Celý týždeň',       description='Cvičil si 7 dní po sebe',                             icon='fire',     category='streak',    xp_reward=55),
    dict(key='streak_14',            name='Dvojtýždenník',     description='Cvičil si 14 dní po sebe',                            icon='calendar', category='streak',    xp_reward=120),
    dict(key='streak_30',            name='Mesiac v rade',     description='Cvičil si 30 dní po sebe',                            icon='trophy',   category='streak',    xp_reward=280),

    # ── Hlas (voice) ─────────────────────────────────────────────────────────
    dict(key='voice_first',          name='Prvý hlas',         description='Prvá správna odpoveď hlasom',                         icon='mic',      category='voice',     xp_reward=15),
    dict(key='voice_10',             name='Hlasitý žiak',      description='10 správnych odpovedí hlasom',                        icon='mic',      category='voice',     xp_reward=35),
    dict(key='voice_50',             name='Rečník',            description='50 správnych odpovedí hlasom',                        icon='mic',      category='voice',     xp_reward=90),
    dict(key='voice_100',            name='Hlasový majster',   description='100 správnych odpovedí hlasom',                       icon='mic',      category='voice',     xp_reward=200),
    dict(key='voice_250',            name='Virtuóz reči',      description='250 správnych odpovedí hlasom',                       icon='mic',      category='voice',     xp_reward=450),

    # ── Míľniky ───────────────────────────────────────────────────────────────
    dict(key='level_5',              name='Level 5',           description='Dosiahol si level 5',                                 icon='star2',    category='milestone', xp_reward=40),
    dict(key='level_10',             name='Dvojciferný',       description='Dosiahol si level 10',                                icon='crown',    category='milestone', xp_reward=120),
    dict(key='level_20',             name='Veterán',           description='Dosiahol si level 20',                                icon='gem',      category='milestone', xp_reward=300),
    dict(key='top10_leaderboard',    name='Top 10',            description='Umiestnil si sa v prvej desiatke rebríčka',           icon='medal',    category='milestone', xp_reward=70),
    dict(key='top3_leaderboard',     name='Stupne víťazov',    description='Umiestnil si sa v prvej trojke rebríčka',             icon='trophy',   category='milestone', xp_reward=160),
]


class Command(BaseCommand):
    help = 'Seeds all gamification badges into the database'

    def handle(self, *args, **kwargs):
        created_count = 0
        for data in BADGES:
            badge, created = Badge.objects.update_or_create(
                key=data['key'],
                defaults={k: v for k, v in data.items() if k != 'key'},
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  Created: {badge.key}'))
            else:
                self.stdout.write(f'  Updated: {badge.key}')

        self.stdout.write(self.style.SUCCESS(
            f'\nHotovo — {created_count} nových, {len(BADGES) - created_count} aktualizovaných.'
        ))
