"""
================================================================================
 Module: seed_grade7_drill_examples.py
 Description:
        Seeds grade 7 drill examples:
        - Pomery
        - Priama umernost
        - Nepriama umernost
        - Zlomky - pokrocile operacie
        - Plosne, kubicke a litrove prevody
        - Jednoducha praca s neznamou

        Safe to run multiple times (idempotent per task+example text).
================================================================================
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Answer, Example, ExampleSkill, Skill, Task


class Command(BaseCommand):
    help = "Create grade 7 drill examples grouped by grade 7 skills."

    WORD_PROBLEM_SKILLS = {
        "Pomery",
        "Priama umernost",
        "Nepriama umernost",
        "Jednoducha praca s neznamou",
    }

    SKILL_TO_TASK = {
        "Pomery": "G7 Drill: Pomery",
        "Priama umernost": "G7 Drill: Priama umernost",
        "Nepriama umernost": "G7 Drill: Nepriama umernost",
        "Zlomky - pokrocile operacie": "G7 Drill: Zlomky pokrocile",
        "Plosne, kubicke a litrove prevody": "G7 Drill: Plosne kubicke litre",
        "Jednoducha praca s neznamou": "G7 Drill: Neznama",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes. Without this flag, dry-run only.",
        )

    def _frac_op(self, a, b, c, d, rn, rd, op):
        op_text = "+" if op == "+" else "-" if op == "-" else "\\cdot" if op == "*" else ":"
        return {
            "example_text": f"\\frac{{{a}}}{{{b}}} {op_text} \\frac{{{c}}}{{{d}}}",
            "answer_text": f"\\frac{{{rn}}}{{{rd}}}",
            "input_type": "FRAC",
        }

    def _inline_latex_example(self, example_text, answer_text, legacy_texts=None, input_type="INLINE"):
        return {
            "example_text": example_text,
            "answer_text": answer_text,
            "input_type": input_type,
            "legacy_texts": legacy_texts or [],
        }

    def _ratio_to_latex(self, text):
        if " skrat na najjednoduchsi tvar " in text:
            ratio = text.split(" ")[1]
            return f"{ratio}\\;\\text{{ skrat na najjednoduchsi tvar }}(a:b)"

        if " rozsir na menovatel " in text:
            ratio = text.split(" ")[1]
            target = text.split(" menovatel ")[1].split(" ")[0]
            return f"{ratio}\\;\\text{{ rozsir na menovatel }}\\;{target}\\;\\text{{ (a:b) }}"

        if " je vacsi ako " in text:
            left = text.split(" ")[1]
            right = text.split(" je vacsi ako ")[1].split(" ")[0]
            return f"{left}\\;\\text{{ je vacsi ako }}\\;{right}\\;\\text{{ (1/0) }}"

        return f"\\text{{{text}}}"

    def _sentence_to_latex(self, text):
        return text

    def _ratio_examples(self):
        plain = [
            ("Pomer chlapcov a dievcat v triede je 3:2. Ak je celkovo 15 ziakov, kolko je chlapcov?", "9"),
            ("Dvaja bratia si rozdelili 120 eur v pomere 5:3. Kolko dostal mladsi brat?", "45"),
            ("Pomer stran obdlznika je 4:5. Ak je dlhsia strana 20 cm, aka dlha je kratsia strana?", "16"),
            ("V miske je 24 bonbonov, pomarancovych a citronovych v pomere 1:3. Kolko je citronovych bonbonov?", "18"),
            ("Pomer veku matky a dcery je 7:2. Ak ma matka 35 rokov, kolko rokov ma dcera?", "10"),
            ("Traja kamarati si rozdelili 90 jablk v pomere 2:3:4. Kolko jablk dostal prvy?", "20"),
            ("Pomer cervenych a modrych aut v garazi je 5:4. Ak je celkovo 18 aut, kolko je modrych?", "8"),
            ("Dva timy maju hracov v pomere 3:5. Ak ma vacsi tim 15 hracov, kolko ma mensi tim?", "9"),
            ("Pomer stran trojuholnika je 2:3:4. Ak je obvod 36 cm, aka dlha je najkratsia strana?", "8"),
            ("V kniznici je 50 knih, romanov a basni v pomere 3:2. Kolko je romanov?", "30"),
            ("Pomer rychlosti dvoch aut je 4:3. Ak rychlejsie auto ide 80 km/h, ako rychlo ide pomalsie?", "60"),
            ("Dvaja priatelia si rozdelili 200 eur v pomere 7:3. Kolko dostal ten, kto ma viac?", "140"),
            ("Pomer poctu psov a maciek v utulku je 5:6. Ak je celkovo 22 zvierat, kolko je maciek?", "12"),
            ("Pomer dlzok dvoch lan je 2:5. Ak je dlhsie lano 25 m, ake dlhe je kratsie?", "10"),
            ("Tri sestry maju vek v pomere 1:2:3. Ak je najmladsia 8 rokov, kolko rokov ma najstarsia?", "24"),
            ("Pomer poctu stoliciek a stolov je 4:1. Ak je 20 stoliciek, kolko je stolov?", "5"),
            ("Dvaja bratranci si rozdelili 60 hraciek v pomere 2:3. Kolko dostal ten, kto ma menej?", "24"),
            ("Pomer poctu jablk a hrusiek je 3:7. Ak je celkovo 20 kusov ovocia, kolko je hrusiek?", "14"),
            ("Pomer hmotnosti dvoch balikov je 5:2. Ak tazsi balik vazi 15 kg, kolko vazi lahsi?", "6"),
            ("V pomere 3:4 je rozdelenych 28 bonbonov. Kolko bonbonov dostane vacsia cast?", "16"),
            ("Pomer poctu ceruziek a pier je 2:5. Ak je 14 ceruziek, kolko je pier?", "35"),
            ("Dvaja susedia pestuju kvety v pomere 6:4. Ak ma jeden 24 kvetov, kolko ma druhy?", "16"),
            ("Pomer dlzok dvoch ciest je 3:8. Ak je kratsia cesta 12 km, aka dlha je dlhsia?", "32"),
            ("Pomer poctu slovenskych a anglickych knih je 5:3. Ak je 40 knih, kolko je slovenskych?", "25"),
            ("Traja kamarati si rozdelili 45 eur v pomere 1:2:6. Kolko dostal ten, kto ma najviac?", "30"),
        ]
        return [
            self._inline_latex_example(
                self._sentence_to_latex(text),
                answer,
                legacy_texts=[text],
                input_type="WORD",
            )
            for text, answer in plain
        ]

    def _direct_proportion_examples(self):
        plain = [
            {
                "example_text": self._sentence_to_latex("3 zosity stoja 6 eur. Kolko stoji 5 zositov"),
                "answer_text": "10",
                "input_type": "WORD",
                "legacy_texts": [
                    "3 zosity stoja 6 eur. Kolko stoji 5 zositov",
                    "3 zosity stoja 6 eur. Kolko stoji 5 zosito",
                    "\\text{3 zosity stoja 6 eur. Kolko stoji 5 zosito}",
                ],
            },
            ("4 kg jablk stoja 8 eur. Kolko stoji 10 kg", "20"),
            ("2 litre dzusu stoja 3 eur. Kolko stoji 8 litrov", "12"),
            ("5 ceruziek stoji 4 eur. Kolko stoji 15 ceruziek", "12"),
            ("6 rozkov stoji 3 eur. Kolko stoji 14 rozkov", "7"),
            ("7 km taxikom stoji 14 eur. Kolko stoji 12 km", "24"),
            ("9 listkov stoji 18 eur. Kolko stoji 20 listkov", "40"),
            ("8 m latky stoji 24 eur. Kolko stoji 5 m", "15"),
            ("3 kg syra stoja 21 eur. Kolko stoji 11 kg", "77"),
            ("4 knihy stoja 28 eur. Kolko stoji 9 knih", "63"),
            ("2 hodiny parkovania stoja 5 eur. Kolko stoji 7 hodin", "17.5"),
            ("10 ks balonov stoji 6 eur. Kolko stoji 25 ks", "15"),
            ("12 m kabla stoji 18 eur. Kolko stoji 20 m", "30"),
            ("5 kg pomarancov stoji 15 eur. Kolko stoji 14 kg", "42"),
            {
                "example_text": self._sentence_to_latex("6 zositov stoji 9 eur. Kolko stoji 4 zosity"),
                "answer_text": "6",
                "input_type": "WORD",
                "legacy_texts": [
                    "6 zositov stoji 9 eur. Kolko stoji 4 zosity",
                    "6 zozitov stoji 9 eur. Kolko stoji 4 zosity",
                    "\\text{6 zozitov stoji 9 eur. Kolko stoji 4 zosity}",
                ],
            },
            ("7 litrov farby stoji 35 eur. Kolko stoji 3 litre", "15"),
            ("9 porcii jedla stoji 54 eur. Kolko stoji 5 porcii", "30"),
            ("11 m pletiva stoji 22 eur. Kolko stoji 18 m", "36"),
            ("13 kusov ovocia stoji 26 eur. Kolko stoji 40 kusov", "80"),
            ("15 km autobusom stoji 12 eur. Kolko stoji 25 km", "20"),
        ]
        output = []
        for item in plain:
            if isinstance(item, dict):
                output.append(item)
            else:
                text, answer = item
                output.append(
                    self._inline_latex_example(
                        self._sentence_to_latex(text),
                        answer,
                        legacy_texts=[text],
                        input_type="WORD",
                    )
                )
        return output

    def _inverse_proportion_examples(self):
        plain = [
            ("4 robotnici postavia plot za 6 dni. Kolko dni potrebuje 8 robotnikov", "3"),
            ("3 robotnici urobia pracu za 12 dni. Kolko dni potrebuje 6 robotnikov", "6"),
            ("5 strojov vyrobi seriu za 10 hodin. Kolko hodin potrebuje 10 strojov", "5"),
            ("8 robotnikov postavi mur za 15 dni. Kolko dni potrebuje 12 robotnikov", "10"),
            ("6 cerpadiel vypumpuje nadrz za 9 hodin. Kolko hodin potrebuje 3 cerpadla", "18"),
            ("9 ludi prenesie naklad za 4 hodiny. Kolko hodin potrebuje 6 ludi", "6"),
            ("12 robotnikov polozi dlazbu za 14 dni. Kolko dni potrebuje 21 robotnikov", "8"),
            ("7 traktorov poorie pole za 16 hodin. Kolko hodin potrebuje 14 traktorov", "8"),
            ("10 aut odvezie material za 6 hodin. Kolko hodin potrebuje 15 aut", "4"),
            ("16 robotnikov zmontuje halu za 18 dni. Kolko dni potrebuje 24 robotnikov", "12"),
            ("20 pracovnikov nalozi tovar za 9 hodin. Kolko hodin potrebuje 12 pracovnikov", "15"),
            ("18 murarov postavi stenu za 20 dni. Kolko dni potrebuje 30 murarov", "12"),
            ("14 strojov vyrobi diely za 21 hodin. Kolko hodin potrebuje 6 strojov", "49"),
            ("15 ludi uprace park za 8 hodin. Kolko hodin potrebuje 10 ludi", "12"),
            ("24 robotnikov vykope jamu za 5 dni. Kolko dni potrebuje 12 robotnikov", "10"),
        ]
        return [
            self._inline_latex_example(
                self._sentence_to_latex(text),
                answer,
                legacy_texts=[text],
                input_type="WORD",
            )
            for text, answer in plain
        ]

    def _fraction_advanced_examples(self):
        return [
            self._frac_op(3, 5, 1, 5, 4, 5, "+"),
            self._frac_op(7, 8, 3, 8, 4, 8, "-"),
            self._frac_op(2, 3, 3, 4, 1, 2, "*"),
            self._frac_op(5, 6, 1, 3, 5, 2, ":"),
            self._frac_op(4, 7, 2, 7, 6, 7, "+"),
            self._frac_op(9, 10, 1, 10, 8, 10, "-"),
            self._frac_op(3, 4, 2, 5, 3, 10, "*"),
            self._frac_op(7, 9, 7, 18, 2, 1, ":"),
            self._frac_op(11, 12, 1, 12, 12, 12, "+"),
            self._frac_op(13, 14, 5, 14, 8, 14, "-"),
            self._frac_op(5, 8, 4, 15, 1, 6, "*"),
            self._frac_op(8, 15, 4, 5, 2, 3, ":"),
            self._frac_op(2, 9, 4, 9, 6, 9, "+"),
            self._frac_op(10, 11, 3, 11, 7, 11, "-"),
            self._frac_op(7, 10, 5, 14, 1, 4, "*"),
            self._frac_op(9, 16, 3, 8, 3, 2, ":"),
            self._frac_op(1, 6, 2, 6, 3, 6, "+"),
            self._frac_op(11, 15, 4, 15, 7, 15, "-"),
            self._frac_op(6, 13, 3, 26, 9, 338, "*"),
            self._frac_op(3, 11, 9, 22, 2, 3, ":"),
            self._frac_op(5, 12, 7, 12, 12, 12, "+"),
            self._frac_op(9, 20, 3, 20, 6, 20, "-"),
            self._frac_op(4, 9, 3, 8, 1, 6, "*"),
            self._frac_op(7, 18, 7, 36, 2, 1, ":"),
            self._frac_op(8, 21, 5, 21, 13, 21, "+"),
            self._frac_op(15, 16, 7, 16, 8, 16, "-"),
            self._frac_op(2, 5, 10, 21, 4, 21, "*"),
            self._frac_op(5, 14, 15, 28, 2, 3, ":"),
            self._frac_op(3, 13, 4, 13, 7, 13, "+"),
            self._frac_op(12, 17, 5, 17, 7, 17, "-"),
        ]

    def _area_volume_liter_examples(self):
        plain = [
            ("1 m^2 = ? dm^2", "100"),
            ("3 m^2 = ? dm^2", "300"),
            ("7 m^2 = ? cm^2", "70000"),
            ("4500 cm^2 = ? dm^2", "45"),
            ("2 ha = ? m^2", "20000"),
            ("35000 m^2 = ? ha", "3.5"),
            ("1 dm^3 = ? cm^3", "1000"),
            ("4 m^3 = ? dm^3", "4000"),
            ("2.5 m^3 = ? l", "2500"),
            ("750 l = ? m^3", "0.75"),
            ("1 l = ? ml", "1000"),
            ("3.2 l = ? ml", "3200"),
            ("4500 ml = ? l", "4.5"),
            ("1 cm^3 = ? ml", "1"),
            ("250 cm^3 = ? ml", "250"),
            ("5 dm^3 = ? l", "5"),
            ("18 l = ? dm^3", "18"),
            ("0.6 m^3 = ? l", "600"),
            ("1200 l = ? m^3", "1.2"),
            ("1 m^3 = ? cm^3", "1000000"),
            ("2 m^3 = ? cm^3", "2000000"),
            ("360000 cm^3 = ? m^3", "0.36"),
            ("15 a = ? m^2", "1500"),
            ("2400 m^2 = ? a", "24"),
            ("0.25 ha = ? m^2", "2500"),
            ("6400 m^2 = ? ha", "0.64"),
            ("12 dm^2 = ? cm^2", "1200"),
            ("900 cm^2 = ? dm^2", "9"),
            ("8 dm^3 = ? cm^3", "8000"),
            ("12500 cm^3 = ? dm^3", "12.5"),
        ]
        return [
            self._inline_latex_example(text, answer, legacy_texts=[text], input_type="INLINE")
            for text, answer in plain
        ]

    def _simple_unknown_examples(self):
        plain = [
            ("3a + 5, kde a = 4", "17"),
            ("2x + 3x, kde x = 6", "30"),
            ("7y - 9, kde y = 5", "26"),
            ("4b + 11, kde b = 8", "43"),
            ("9k - 4k, kde k = 7", "35"),
            ("6m + 2m + 1, kde m = 3", "25"),
            ("5p - 3, kde p = 9", "42"),
            ("8r + 12, kde r = 4", "44"),
            ("10t - 2t, kde t = 11", "88"),
            ("3n + 4n - 5, kde n = 6", "37"),
            ("x + 5 = 12, x = ?", "7"),
            ("2x = 18, x = ?", "9"),
            ("3x + 2 = 20, x = ?", "6"),
            ("4x - 7 = 21, x = ?", "7"),
            ("5x + 5 = 40, x = ?", "7"),
            ("6x - 6 = 30, x = ?", "6"),
            ("7x + 1 = 29, x = ?", "4"),
            ("8x - 8 = 40, x = ?", "6"),
            ("9x + 3 = 48, x = ?", "5"),
            ("10x - 20 = 30, x = ?", "5"),
            ("2a + 5, kde a = 10", "25"),
            ("3b + 7, kde b = 9", "34"),
            ("4c - 6, kde c = 8", "26"),
            ("5d + 5d, kde d = 4", "40"),
            ("6e - 2e + 3, kde e = 7", "31"),
        ]
        return [
            self._inline_latex_example(
                self._sentence_to_latex(text),
                answer,
                legacy_texts=[text],
                input_type="WORD",
            )
            for text, answer in plain
        ]

    def _build_dataset(self):
        return {
            "Pomery": self._ratio_examples(),
            "Priama umernost": self._direct_proportion_examples(),
            "Nepriama umernost": self._inverse_proportion_examples(),
            "Zlomky - pokrocile operacie": self._fraction_advanced_examples(),
            "Plosne, kubicke a litrove prevody": self._area_volume_liter_examples(),
            "Jednoducha praca s neznamou": self._simple_unknown_examples(),
        }

    def _upsert_example(self, task, skill, example_text, answer_text, input_type="INLINE", legacy_texts=None):
        candidate_texts = [example_text]
        if legacy_texts:
            candidate_texts.extend(legacy_texts)

        matches = list(Example.objects.filter(task=task, example__in=candidate_texts).order_by("id"))
        example = matches[0] if matches else None

        # Keep only one canonical record when historical seed variants created duplicates.
        if len(matches) > 1:
            Example.objects.filter(id__in=[item.id for item in matches[1:]]).delete()

        if not example:
            example = Example.objects.create(
                task=task,
                example=example_text,
                input_type=input_type,
            )
        else:
            update_fields = []
            if example.example != example_text:
                example.example = example_text
                update_fields.append("example")
            if example.input_type != input_type:
                example.input_type = input_type
                update_fields.append("input_type")
            if update_fields:
                example.save(update_fields=update_fields)

        ans = Answer.objects.filter(example=example).first()
        if not ans:
            Answer.objects.create(example=example, answer=answer_text)
        elif ans.answer != answer_text:
            ans.answer = answer_text
            ans.save(update_fields=["answer"])

        ExampleSkill.objects.get_or_create(example=example, skill=skill)

    def handle(self, *args, **options):
        apply_changes = options["apply"]

        dataset = self._build_dataset()
        self.stdout.write("=== Grade 7 drill seed preview ===")

        for skill_name, pairs in dataset.items():
            self.stdout.write(f"- {skill_name}: {len(pairs)} examples")
            for preview in pairs[:3]:
                if isinstance(preview, dict):
                    self.stdout.write(f"    {preview['example_text']} = {preview['answer_text']}")
                else:
                    self.stdout.write(f"    {preview[0]} = {preview[1]}")

        if not apply_changes:
            self.stdout.write("\nDry-run only. Re-run with --apply to create/update examples.")
            return

        created_or_updated = 0
        with transaction.atomic():
            for skill_name, pairs in dataset.items():
                skill = Skill.objects.filter(name=skill_name, deleted=False).first()
                if not skill:
                    self.stdout.write(self.style.WARNING(f"Skill not found, skipping: {skill_name}"))
                    continue

                task_name = self.SKILL_TO_TASK[skill_name]
                desired_form = "word-problem" if skill_name in self.WORD_PROBLEM_SKILLS else "classic"
                task, _ = Task.objects.get_or_create(name=task_name, defaults={"form": desired_form})
                if task.form != desired_form:
                    task.form = desired_form
                    task.save(update_fields=["form"])
                task.skills.add(skill)

                # Keep task examples in sync with current seed set.
                expected_texts = set()
                for pair in pairs:
                    if isinstance(pair, dict):
                        expected_texts.add(pair["example_text"])
                    else:
                        expected_texts.add(pair[0])

                Example.objects.filter(task=task).exclude(example__in=expected_texts).delete()

                for pair in pairs:
                    if isinstance(pair, dict):
                        self._upsert_example(
                            task,
                            skill,
                            pair["example_text"],
                            pair["answer_text"],
                            input_type=pair.get("input_type", "INLINE"),
                            legacy_texts=pair.get("legacy_texts"),
                        )
                    else:
                        example_text, answer_text = pair
                        self._upsert_example(task, skill, example_text, answer_text)
                    created_or_updated += 1

        self.stdout.write(self.style.SUCCESS(f"\n✓ Grade 7 drill seed applied. Processed {created_or_updated} examples."))
