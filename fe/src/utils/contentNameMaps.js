/**
 * File: contentNameMaps.js
 * Description:
 *       Translates database content (skill/task names) between cs/sk/en.
 *       Unrelated to static UI strings, which live in @/i18n.
 */

/**
 * Translates a skill name from Czech to English depending on the selected language.
 * 
 * @param {string} czechName - name of the skill in Czech
 * @param {string} lang - language code ('cs' or 'en' or 'sk')
 * @returns {string} translated skill name
 */
export const getSkillName = (czechName, lang) => {
    const mapEn = {
        "Sčítání": "Addition",
        "Odčítání": "Subtraction",
        "Násobení": "Multiplication",
        "Dělení": "Division",
        "Druhá mocnina": "Square",
        "Druhá odmocnina": "Square Root",
        "Krácení": "Simplification",
        "Celá čísla": "Integers",
        "Desetinná čísla": "Decimal Numbers",
        "Zlomky": "Fractions",
        "Pythagorova věta": "Pythagorean Theorem",
        "Rovnice": "Equations",
        "Do 20": "Up to 20",
        "Přes 20": "Over 20",
        "Do 100": "Up to 100",
        "Nad 100": "Over 100",
        "Do 50": "Up to 50",
        "Přes 10": "Over 10",
        "Do 10": "Up to 10",
        "Desetiny": "Decimals",
        "Poměry": "Ratio"
    };

    const mapSk = {
        "Sčítání": "Sčítanie",
        "Odčítání": "Odčítanie",
        "Násobení": "Násobenie",
        "Dělení": "Delenie",
        "Druhá mocnina": "Druhá mocnina",
        "Druhá odmocnina": "Druhá odmocnina",
        "Krácení": "Krátenie",
        "Celá čísla": "Celé čísla",
        "Desetinná čísla": "Desatinné čísla",
        "Zlomky": "Zlomky",
        "Pythagorova věta": "Pytagorova veta",
        "Rovnice": "Rovnice",
        "Do 20": "Do 20",
        "Přes 20": "Nad 20",
        "Do 100": "Do 100",
        "Nad 100": "Nad 100",
        "Do 50": "Do 50",
        "Přes 10": "Nad 10",
        "Do 10": "Do 10",
        "Desetiny": "Desatiny",
        "Poměry": "Pomery"
    };

    if (lang === "en") return mapEn[czechName] || czechName;
    if (lang === "sk") return mapSk[czechName] || czechName;
    return czechName; // cs
};

/**
 * Translates a task name (as stored in DB) to the requested language.
 * Falls back to the original DB name if no translation is found.
 *
 * @param {string} dbName - exact task name from the database
 * @param {string} lang - 'sk' | 'cs' | 'en'
 * @returns {string}
 */
const _taskNameMap = {
    "7. ročník slovné úlohy":                    { sk: "7. ročník – slovné úlohy",                        cs: "7. ročník – slovní úlohy",                          en: "Grade 7 – Word Problems" },
    "Dělení celá čísla do 100":                  { sk: "Delenie – celé čísla do 100",                     cs: "Dělení – celá čísla do 100",                        en: "Division – Integers up to 100" },
    "Dělení celá čísla do 100 II.":              { sk: "Delenie – celé čísla do 100 II.",                  cs: "Dělení – celá čísla do 100 II.",                    en: "Division – Integers up to 100 II." },
    "Dělení zlomky I.":                          { sk: "Delenie – zlomky I.",                              cs: "Dělení – zlomky I.",                                en: "Division – Fractions I." },
    "Delenie zlomky I.":                         { sk: "Delenie – zlomky I.",                              cs: "Dělení – zlomky I.",                                en: "Division – Fractions I." },
    "Doplňovanie čísla do 10 a 20":              { sk: "Doplňovanie čísel do 10 a 20",                    cs: "Doplňování čísel do 10 a 20",                       en: "Completing Numbers to 10 and 20" },
    "Druhá mocnina do 20":                       { sk: "Druhá mocnina do 20",                              cs: "Druhá mocnina do 20",                               en: "Squares up to 20" },
    "G2 Drill: Doplňovanie do 10/100":           { sk: "2. ročník – Doplňovanie do 10/100",                cs: "2. ročník – Doplňování do 10/100",                  en: "Grade 2 – Completing to 10/100" },
    "G2 Drill: Doplňovanie do 100":              { sk: "2. ročník – Doplňovanie do 100",                  cs: "2. ročník – Doplňování do 100",                     en: "Grade 2 – Completing to 100" },
    "G2 Drill: Násobenie ako opakované sčítanie": { sk: "2. ročník – Násobenie ako opakované sčítanie",   cs: "2. ročník – Násobení jako opakované sčítání",        en: "Grade 2 – Multiplication as Repeated Addition" },
    "G2 Drill: Odčítanie do 100":                { sk: "2. ročník – Odčítanie do 100",                    cs: "2. ročník – Odčítání do 100",                       en: "Grade 2 – Subtraction up to 100" },
    "G2 Drill: Rozklad na desiatky a jednotky":  { sk: "2. ročník – Rozklad na desiatky a jednotky",       cs: "2. ročník – Rozklad na desítky a jednotky",         en: "Grade 2 – Decomposing into Tens and Ones" },
    "G2 Drill: Sčítanie bez prechodu":           { sk: "2. ročník – Sčítanie bez prechodu",               cs: "2. ročník – Sčítání bez přechodu",                  en: "Grade 2 – Addition without Carrying" },
    "G2 Drill: Sčítanie s prechodom":            { sk: "2. ročník – Sčítanie s prechodom",                cs: "2. ročník – Sčítání s přechodem",                   en: "Grade 2 – Addition with Carrying" },
    "G3 Drill: Doplňovanie v násobení/delení":   { sk: "3. ročník – Doplňovanie v násobení/delení",       cs: "3. ročník – Doplňování v násobení/dělení",          en: "Grade 3 – Missing Factors in ×/÷" },
    "G3 Drill: Malá násobilka I":                { sk: "3. ročník – Malá násobilka I",                     cs: "3. ročník – Malá násobilka I",                      en: "Grade 3 – Times Tables I" },
    "G3 Drill: Malá násobilka II":               { sk: "3. ročník – Malá násobilka II",                    cs: "3. ročník – Malá násobilka II",                     en: "Grade 3 – Times Tables II" },
    "G3 Drill: Malé delenie I":                  { sk: "3. ročník – Malé delenie I",                       cs: "3. ročník – Malé dělení I",                         en: "Grade 3 – Basic Division I" },
    "G3 Drill: Malé delenie II":                 { sk: "3. ročník – Malé delenie II",                      cs: "3. ročník – Malé dělení II",                        en: "Grade 3 – Basic Division II" },
    "G3 Drill: Odčítanie do 1000":               { sk: "3. ročník – Odčítanie do 1000",                   cs: "3. ročník – Odčítání do 1000",                      en: "Grade 3 – Subtraction up to 1000" },
    "G3 Drill: Prevody dlzky I":                 { sk: "3. ročník – Prevody dĺžky I",                     cs: "3. ročník – Převody délky I",                       en: "Grade 3 – Length Conversions I" },
    "G3 Drill: Sčítanie do 1000":                { sk: "3. ročník – Sčítanie do 1000",                    cs: "3. ročník – Sčítání do 1000",                       en: "Grade 3 – Addition up to 1000" },
    "G4 Drill: Delenie jednociferným":           { sk: "4. ročník – Delenie jednociferným",                cs: "4. ročník – Dělení jednociferným",                  en: "Grade 4 – Division by Single Digit" },
    "G4 Drill: Delenie so zvyškom":              { sk: "4. ročník – Delenie so zvyškom",                   cs: "4. ročník – Dělení se zbytkem",                     en: "Grade 4 – Division with Remainder" },
    "G4 Drill: Násobenie dvojciferným":          { sk: "4. ročník – Násobenie dvojciferným",               cs: "4. ročník – Násobení dvojciferným",                 en: "Grade 4 – Multiplication by Two Digits" },
    "G4 Drill: Násobilka do 10x10":              { sk: "4. ročník – Násobilka do 10×10",                   cs: "4. ročník – Násobilka do 10×10",                    en: "Grade 4 – Times Tables up to 10×10" },
    "G4 Drill: Odčítanie do 10000":              { sk: "4. ročník – Odčítanie do 10 000",                  cs: "4. ročník – Odčítání do 10 000",                    en: "Grade 4 – Subtraction up to 10,000" },
    "G4 Drill: Prevody dlzky II":                { sk: "4. ročník – Prevody dĺžky II",                     cs: "4. ročník – Převody délky II",                      en: "Grade 4 – Length Conversions II" },
    "G4 Drill: Sčítanie do 10000":               { sk: "4. ročník – Sčítanie do 10 000",                   cs: "4. ročník – Sčítání do 10 000",                     en: "Grade 4 – Addition up to 10,000" },
    "G5 Drill: Delenie viacmiestnych":           { sk: "5. ročník – Delenie viacmiestnych čísel",           cs: "5. ročník – Dělení víceciferných čísel",            en: "Grade 5 – Division of Multi-digit Numbers" },
    "G5 Drill: Nasobenie viacmiestnych":         { sk: "5. ročník – Násobenie viacmiestnych čísel",         cs: "5. ročník – Násobení víceciferných čísel",          en: "Grade 5 – Multiplication of Multi-digit Numbers" },
    "G5 Drill: Poradie operacii":                { sk: "5. ročník – Poradie operácií",                     cs: "5. ročník – Pořadí operací",                        en: "Grade 5 – Order of Operations" },
    "G5 Drill: Prevody casu":                    { sk: "5. ročník – Prevody času",                         cs: "5. ročník – Převody času",                          en: "Grade 5 – Time Conversions" },
    "G5 Drill: Zaokruhlovanie":                  { sk: "5. ročník – Zaokrúhľovanie",                       cs: "5. ročník – Zaokrouhlování",                        en: "Grade 5 – Rounding" },
    "G6 Drill: Delitelnost NSD NSN":             { sk: "6. ročník – Deliteľnosť, NSD, NSN",                cs: "6. ročník – Dělitelnost, NSD, NSN",                 en: "Grade 6 – Divisibility, GCD, LCM" },
    "G6 Drill: Delitelnost a prvocisla":         { sk: "6. ročník – Deliteľnosť a prvočísla",              cs: "6. ročník – Dělitelnost a prvočísla",               en: "Grade 6 – Divisibility and Prime Numbers" },
    "G6 Drill: Desatinne cisla":                 { sk: "6. ročník – Desatinné čísla",                      cs: "6. ročník – Desetinná čísla",                       en: "Grade 6 – Decimal Numbers" },
    "G6 Drill: NSD":                             { sk: "6. ročník – NSD",                                  cs: "6. ročník – NSD",                                   en: "Grade 6 – GCD" },
    "G6 Drill: NSN":                             { sk: "6. ročník – NSN",                                  cs: "6. ročník – NSN",                                   en: "Grade 6 – LCM" },
    "G6 Drill: Prirodzene cisla":                { sk: "6. ročník – Prirodzené čísla",                     cs: "6. ročník – Přirozená čísla",                       en: "Grade 6 – Natural Numbers" },
    "G6 Drill: Rozklad na prvocinitele":         { sk: "6. ročník – Rozklad na prvočínitele",               cs: "6. ročník – Rozklad na prvočinitele",               en: "Grade 6 – Prime Factorization" },
    "G6 Drill: Zlomky krat deleno":              { sk: "6. ročník – Zlomky – krát, deleno",                 cs: "6. ročník – Zlomky – krát, děleno",                 en: "Grade 6 – Fractions – Multiply/Divide" },
    "G6 Drill: Zlomky plus minus":               { sk: "6. ročník – Zlomky – plus/mínus",                  cs: "6. ročník – Zlomky – plus/mínus",                   en: "Grade 6 – Fractions – Add/Subtract" },
    "G6 Drill: Zlomky rovnaky menovatel":        { sk: "6. ročník – Zlomky – rovnaký menovateľ",            cs: "6. ročník – Zlomky – stejný jmenovatel",            en: "Grade 6 – Fractions – Same Denominator" },
    "G7 Drill: Nepriama umernost":               { sk: "7. ročník – Nepriama úmernosť",                    cs: "7. ročník – Nepřímá úměra",                         en: "Grade 7 – Inverse Proportion" },
    "G7 Drill: Neznama":                         { sk: "7. ročník – Neznáma",                              cs: "7. ročník – Neznámá",                               en: "Grade 7 – Unknown Variable" },
    "G7 Drill: Plosne kubicke litre":            { sk: "7. ročník – Plošné, kubické, litre",                cs: "7. ročník – Plošné, kubické, litry",                en: "Grade 7 – Area, Volume, Litres" },
    "G7 Drill: Pomery":                          { sk: "7. ročník – Pomery",                               cs: "7. ročník – Poměry",                                en: "Grade 7 – Ratios" },
    "G7 Drill: Priama umernost":                 { sk: "7. ročník – Priama úmernosť",                      cs: "7. ročník – Přímá úměra",                           en: "Grade 7 – Direct Proportion" },
    "G7 Drill: Zlomky pokrocile":                { sk: "7. ročník – Zlomky pokročilé",                     cs: "7. ročník – Zlomky pokročilé",                      en: "Grade 7 – Fractions Advanced" },
    "G8 Drill: Mocniny odmocniny":               { sk: "8. ročník – Mocniny a odmocniny",                  cs: "8. ročník – Mocniny a odmocniny",                   en: "Grade 8 – Powers and Roots" },
    "G8 Drill: Percenta":                        { sk: "8. ročník – Percentá",                              cs: "8. ročník – Procenta",                              en: "Grade 8 – Percentages" },
    "G8 Drill: Pytagorova veta":                 { sk: "8. ročník – Pytagorova veta",                      cs: "8. ročník – Pythagorova věta",                      en: "Grade 8 – Pythagorean Theorem" },
    "G8 Drill: Rovnice":                         { sk: "8. ročník – Rovnice",                              cs: "8. ročník – Rovnice",                               en: "Grade 8 – Equations" },
    "G9 Testovanie 9: Priklady":                 { sk: "9. ročník – Príklady",                              cs: "9. ročník – Příklady",                              en: "Grade 9 – Examples" },
    "G9 Testovanie 9: Slovne ulohy":             { sk: "9. ročník – Slovné úlohy",                         cs: "9. ročník – Slovní úlohy",                          en: "Grade 9 – Word Problems" },
    "Hospodárske slovné úlohy":                  { sk: "Hospodárske slovné úlohy",                         cs: "Hospodářské slovní úlohy",                          en: "Economics Word Problems" },
    "Hudobné nástroje slovné úlohy":             { sk: "Hudobné nástroje – slovné úlohy",                  cs: "Hudební nástroje – slovní úlohy",                   en: "Musical Instruments – Word Problems" },
    "Hudobné slovné úlohy":                      { sk: "Hudobné slovné úlohy",                             cs: "Hudební slovní úlohy",                              en: "Music Word Problems" },
    "Jednoduché zlomky":                         { sk: "Jednoduché zlomky",                                cs: "Jednoduché zlomky",                                 en: "Simple Fractions" },
    "Krácení zlomků":                            { sk: "Krátenie zlomkov",                                 cs: "Krácení zlomků",                                    en: "Simplifying Fractions" },
    "Matematika 3. ročník":                      { sk: "Matematika – 3. ročník",                           cs: "Matematika – 3. ročník",                            en: "Math – Grade 3" },
    "Násobenie a delenie veľkých čísel":          { sk: "Násobenie a delenie veľkých čísel",                cs: "Násobení a dělení velkých čísel",                   en: "Multiplication and Division of Large Numbers" },
    "Násobenie zlomky I.":                       { sk: "Násobenie – zlomky I.",                            cs: "Násobení – zlomky I.",                              en: "Multiplication – Fractions I." },
    "Násobení zlomky I.":                        { sk: "Násobenie – zlomky I.",                            cs: "Násobení – zlomky I.",                              en: "Multiplication – Fractions I." },
    "Násobilka 1-9":                             { sk: "Násobilka 1–9",                                    cs: "Násobilka 1–9",                                     en: "Times Tables 1–9" },
    "Násobilka do 10":                           { sk: "Násobilka do 10",                                  cs: "Násobilka do 10",                                   en: "Times Tables up to 10" },
    "Násobilka od 10 do 20":                     { sk: "Násobilka od 10 do 20",                            cs: "Násobilka od 10 do 20",                             en: "Times Tables from 10 to 20" },
    "Odčítání celá čísla do 1 milionu":          { sk: "Odčítanie – celé čísla do 1 milióna",             cs: "Odčítání – celá čísla do 1 milionu",                en: "Subtraction – Integers up to 1 Million" },
    "Odčítání celá čísla do 10 tisíc":           { sk: "Odčítanie – celé čísla do 10 tisíc",              cs: "Odčítání – celá čísla do 10 tisíc",                 en: "Subtraction – Integers up to 10,000" },
    "Odčítání celá čísla do 100":                { sk: "Odčítanie – celé čísla do 100",                    cs: "Odčítání – celá čísla do 100",                      en: "Subtraction – Integers up to 100" },
    "Odčítání celá čísla do 50":                 { sk: "Odčítanie – celé čísla do 50",                     cs: "Odčítání – celá čísla do 50",                       en: "Subtraction – Integers up to 50" },
    "Odčítání celá čísla přes 10":               { sk: "Odčítanie – celé čísla cez 10",                    cs: "Odčítání – celá čísla přes 10",                     en: "Subtraction – Integers over 10" },
    "Odčítání celá čísla přes 20":               { sk: "Odčítanie – celé čísla cez 20",                    cs: "Odčítání – celá čísla přes 20",                     en: "Subtraction – Integers over 20" },
    "Odčítání desetinná čísla do 10 po 0.1":     { sk: "Odčítanie – desatinné čísla do 10 (po 0,1)",      cs: "Odčítání – desetinná čísla do 10 (po 0,1)",         en: "Subtraction – Decimals up to 10 (by 0.1)" },
    "Odčítání do 10":                            { sk: "Odčítanie do 10",                                  cs: "Odčítání do 10",                                    en: "Subtraction up to 10" },
    "Odčítání nad 100":                          { sk: "Odčítanie – nad 100",                              cs: "Odčítání – nad 100",                                en: "Subtraction – over 100" },
    "Odčítání zlomky I.":                        { sk: "Odčítanie – zlomky I.",                            cs: "Odčítání – zlomky I.",                              en: "Subtraction – Fractions I." },
    "Odčítanie celé čísla cez 10":               { sk: "Odčítanie – celé čísla cez 10",                    cs: "Odčítání – celá čísla přes 10",                     en: "Subtraction – Integers over 10" },
    "Odčítanie celé čísla cez 20":               { sk: "Odčítanie – celé čísla cez 20",                    cs: "Odčítání – celá čísla přes 20",                     en: "Subtraction – Integers over 20" },
    "Odčítanie celé čísla do 100":               { sk: "Odčítanie – celé čísla do 100",                    cs: "Odčítání – celá čísla do 100",                      en: "Subtraction – Integers up to 100" },
    "Odčítanie celé čísla do 50":                { sk: "Odčítanie – celé čísla do 50",                     cs: "Odčítání – celá čísla do 50",                       en: "Subtraction – Integers up to 50" },
    "Odčítanie do 10":                           { sk: "Odčítanie do 10",                                  cs: "Odčítání do 10",                                    en: "Subtraction up to 10" },
    "Odčítanie zlomky I.":                       { sk: "Odčítanie – zlomky I.",                            cs: "Odčítání – zlomky I.",                              en: "Subtraction – Fractions I." },
    "Odmocnina celá čísla do 20":                { sk: "Odmocnina – celé čísla do 20",                     cs: "Odmocnina – celá čísla do 20",                      en: "Square Root – Integers up to 20" },
    "Percentá":                                  { sk: "Percentá",                                         cs: "Procenta",                                          en: "Percentages" },
    "Pokročilé operácie so zlomkami":             { sk: "Pokročilé operácie so zlomkami",                   cs: "Pokročilé operace se zlomky",                       en: "Advanced Fraction Operations" },
    "Poměry":                                    { sk: "Pomery",                                           cs: "Poměry",                                            en: "Ratios" },
    "Porovnávanie čísel do 20":                  { sk: "Porovnávanie čísel do 20",                         cs: "Porovnávání čísel do 20",                           en: "Comparing Numbers up to 20" },
    "Prevod jednotiek času":                     { sk: "Prevody jednotiek času",                           cs: "Převody jednotek času",                             en: "Time Unit Conversions" },
    "Prevody jednotiek dĺžky":                   { sk: "Prevody jednotiek dĺžky",                          cs: "Převody jednotek délky",                            en: "Length Unit Conversions" },
    "Převody délkových jednotek":                { sk: "Prevody dĺžkových jednotiek",                      cs: "Převody délkových jednotek",                        en: "Length Unit Conversions" },
    "Převody plošných jednotek":                 { sk: "Prevody plošných jednotiek",                       cs: "Převody plošných jednotek",                         en: "Area Unit Conversions" },
    "Pythagorejské trojce do 20":                { sk: "Pytagorejské trojice do 20",                       cs: "Pythagorejské trojice do 20",                       en: "Pythagorean Triples up to 20" },
    "Sčítání celá čísla do 1 milionu":           { sk: "Sčítanie – celé čísla do 1 milióna",              cs: "Sčítání – celá čísla do 1 milionu",                 en: "Addition – Integers up to 1 Million" },
    "Sčítání celá čísla do 10 tisíc":            { sk: "Sčítanie – celé čísla do 10 tisíc",               cs: "Sčítání – celá čísla do 10 tisíc",                  en: "Addition – Integers up to 10,000" },
    "Sčítání celá čísla do 100":                 { sk: "Sčítanie – celé čísla do 100",                     cs: "Sčítání – celá čísla do 100",                       en: "Addition – Integers up to 100" },
    "Sčítání celá čísla do 50":                  { sk: "Sčítanie – celé čísla do 50",                      cs: "Sčítání – celá čísla do 50",                        en: "Addition – Integers up to 50" },
    "Sčítání celá čísla přes 10":                { sk: "Sčítanie – celé čísla cez 10",                     cs: "Sčítání – celá čísla přes 10",                      en: "Addition – Integers over 10" },
    "Sčítání celá čísla přes 20":                { sk: "Sčítanie – celé čísla cez 20",                     cs: "Sčítání – celá čísla přes 20",                      en: "Addition – Integers over 20" },
    "Sčítání desetinna čísla do 10 po 0.1":      { sk: "Sčítanie – desatinné čísla do 10 (po 0,1)",       cs: "Sčítání – desetinná čísla do 10 (po 0,1)",          en: "Addition – Decimals up to 10 (by 0.1)" },
    "Sčítání do 10":                             { sk: "Sčítanie do 10",                                   cs: "Sčítání do 10",                                     en: "Addition up to 10" },
    "Sčítání nad 100":                           { sk: "Sčítanie – nad 100",                               cs: "Sčítání – nad 100",                                 en: "Addition – over 100" },
    "Sčítání zlomky I.":                         { sk: "Sčítanie – zlomky I.",                             cs: "Sčítání – zlomky I.",                               en: "Addition – Fractions I." },
    "Sčítání zlomky II.":                        { sk: "Sčítanie – zlomky II.",                            cs: "Sčítání – zlomky II.",                              en: "Addition – Fractions II." },
    "Sčítánie celé čísla cez 10":                { sk: "Sčítanie – celé čísla cez 10",                     cs: "Sčítání – celá čísla přes 10",                      en: "Addition – Integers over 10" },
    "Sčítanie celé čísla cez 20":                { sk: "Sčítanie – celé čísla cez 20",                     cs: "Sčítání – celá čísla přes 20",                      en: "Addition – Integers over 20" },
    "Sčítanie celé čísla do 100":                { sk: "Sčítanie – celé čísla do 100",                     cs: "Sčítání – celá čísla do 100",                       en: "Addition – Integers up to 100" },
    "Sčítanie celé čísla do 50":                 { sk: "Sčítanie – celé čísla do 50",                      cs: "Sčítání – celá čísla do 50",                        en: "Addition – Integers up to 50" },
    "Sčítanie čísel do 10 000":                  { sk: "Sčítanie čísel do 10 000",                         cs: "Sčítání čísel do 10 000",                           en: "Addition of Numbers up to 10,000" },
    "Sčítanie do 10":                            { sk: "Sčítanie do 10",                                   cs: "Sčítání do 10",                                     en: "Addition up to 10" },
    "Sčítanie zlomky I.":                        { sk: "Sčítanie – zlomky I.",                             cs: "Sčítání – zlomky I.",                               en: "Addition – Fractions I." },
    "Sčítanie zlomky II.":                       { sk: "Sčítanie – zlomky II.",                            cs: "Sčítání – zlomky II.",                              en: "Addition – Fractions II." },
    "Slovné úlohy (7. ročník)":                  { sk: "Slovné úlohy – 7. ročník",                         cs: "Slovní úlohy – 7. ročník",                          en: "Word Problems – Grade 7" },
    "Slovné úlohy 7. ročník":                    { sk: "Slovné úlohy – 7. ročník",                         cs: "Slovní úlohy – 7. ročník",                          en: "Word Problems – Grade 7" },
    "Slovné úlohy o hadoch":                     { sk: "Slovné úlohy o hadoch",                            cs: "Slovní úlohy o hadech",                             en: "Word Problems about Snakes" },
    "Slovné úlohy o národnostiach":              { sk: "Slovné úlohy o národnostiach",                     cs: "Slovní úlohy o národnostech",                       en: "Word Problems about Nationalities" },
    "Slovné úlohy o slonoch":                    { sk: "Slovné úlohy o slonoch",                           cs: "Slovní úlohy o slonech",                            en: "Word Problems about Elephants" },
    "Slovné úlohy o zebrách":                    { sk: "Slovné úlohy o zebrách",                           cs: "Slovní úlohy o zebrách",                            en: "Word Problems about Zebras" },
    "Slovné úlohy o zvieratkách":                { sk: "Slovné úlohy o zvieratkách",                       cs: "Slovní úlohy o zvířátkách",                         en: "Word Problems about Animals" },
    "Slovné úlohy o zvieratách":                 { sk: "Slovné úlohy o zvieratách",                        cs: "Slovní úlohy o zvířatech",                          en: "Word Problems about Animals" },
    "Slovné úlohy pre 4. ročník":                { sk: "Slovné úlohy pre 4. ročník",                       cs: "Slovní úlohy pro 4. ročník",                        en: "Word Problems – Grade 4" },
    "Slovné úlohy pre 7. ročník":                { sk: "Slovné úlohy pre 7. ročník",                       cs: "Slovní úlohy pro 7. ročník",                        en: "Word Problems – Grade 7" },
    "Slovné úlohy s násobením":                  { sk: "Slovné úlohy s násobením",                         cs: "Slovní úlohy s násobením",                          en: "Word Problems with Multiplication" },
    "Slovné úlohy: Pomery, úmernosť a zlomky":   { sk: "Slovné úlohy: Pomery, úmernosť a zlomky",          cs: "Slovní úlohy: Poměry, úměra a zlomky",              en: "Word Problems: Ratios, Proportion and Fractions" },
    "Transformerské slovné úlohy":               { sk: "Transformerské slovné úlohy",                      cs: "Transformerské slovní úlohy",                       en: "Transformers Word Problems" },
    "Úlohy na zlomky":                           { sk: "Úlohy na zlomky",                                  cs: "Úlohy na zlomky",                                   en: "Fraction Exercises" },
    "Zlomky krat deleno":                        { sk: "Zlomky – krát, deleno",                            cs: "Zlomky – krát, děleno",                             en: "Fractions – Multiplication and Division" },
};

export const getTaskName = (dbName, lang) => {
    const entry = _taskNameMap[dbName];
    if (!entry) return dbName;
    return entry[lang] || entry['sk'] || dbName;
};

/**
 * Walks an API response (object/array, any depth) and translates every
 * "name" / "task_name" string value found via getTaskName. Keys that don't
 * match a known DB task name are returned unchanged, so this is safe to run
 * over responses that also carry unrelated "name" fields (classrooms,
 * students, teacher-authored set names, ...).
 *
 * @param {*} data - response payload, mutated in place and returned
 * @param {string} lang - 'sk' | 'cs' | 'en'
 * @returns {*} the same `data`, with matching name fields translated
 */
const _TRANSLATABLE_NAME_KEYS = new Set(['name', 'task_name']);

export const translateTaskNamesDeep = (data, lang) => {
    if (Array.isArray(data)) {
        data.forEach((item) => translateTaskNamesDeep(item, lang));
        return data;
    }
    if (data && typeof data === 'object') {
        for (const key of Object.keys(data)) {
            const value = data[key];
            if (_TRANSLATABLE_NAME_KEYS.has(key) && typeof value === 'string') {
                data[key] = getTaskName(value, lang);
            } else if (value && typeof value === 'object') {
                translateTaskNamesDeep(value, lang);
            }
        }
    }
    return data;
};
