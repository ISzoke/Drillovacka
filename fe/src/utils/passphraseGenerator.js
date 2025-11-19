/**
 * ================================================================================
 * File: passphraseGenerator.js
 * Description:
 *       Utility for generating Slovak, Czech and English passphrases.
 * Author: Dominik Horut (xhorut01)
 * ================================================================================
 */

import seedrandom from "seedrandom";

// ============================================================================
// CZECH - České vlastnosti, barvy a zvířata
// ============================================================================
const abilitiesMasculineCZ = [
    "vesely", "hravy", "mily", "zabavny", "radostny", "usmevavy", 
    "pratelsky", "stastny", "energicky", "rozverny", "vynalezavy", 
    "kouzelny", "hodny", "kouzelnicky", "sikovny", "bystry", "chytry", 
    "zvedavy", "roztomily", "blaznivy", "neposedny", "pohodovy", 
    "rozesmaty", "rozkosny", "hrdinsky", "napadity", "laskavy", 
    "nezkazeny", "kamaradsky", "dobrosrdecny", "nadherny", 
    "dobrodruzny", "hrdy", "odvazny", "skotacivy", "vtipny", 
    "jedinecny", "slunecny"
];

const abilitiesFeinineCZ = [
    "vesela", "hrava", "mila", "zabavna", "radostna", "usmevava", 
    "pratelska", "stastna", "energicka", "rozverna", "vynalezava", 
    "kouzelna", "hodna", "kouzelnicka", "sikovna", "bystra", "chytra", 
    "zvedava", "roztomila", "blazniva", "neposedna", "pohodova", 
    "rozesmata", "rozkosna", "hrdinska", "napadita", "laskava", 
    "nezkazena", "kamaradska", "dobrosrdecna", "nadherna", 
    "dobrodruzna", "nevinna", "hrda", "odvazna", "skotaciva", 
    "vtipna", "jedinecna", "slunecna"
];

const colorsMasculineCZ = [
    "cerny", "modry", "zeleny", "zluty", "fialovy", "oranzovy", 
    "ruzovy", "bily", "hnedy", "sedy", "stribrny", "bezovy", 
    "mentolovy", "tyrkysovy", "neonovy", "olivovy", "safirovy", 
    "kremovy", "medeny", "perletovy", "zlatavy"
];

const colorsFeinineCZ = [
    "cerna", "modra", "zelena", "zluta", "fialova", "oranzova", 
    "ruzova", "bila", "hneda", "seda", "zlata", "stribrna", 
    "bezova", "mentolova", "tyrkysova", "neonova", "olivova", 
    "safirova", "kremova", "medena", "perletova", "zlatava"
];

const animalsMasculineCZ = [
    "tygr", "slon", "lev", "krab", "pes", "vlk", "medved", 
    "krokodyl", "pstros", "labrador", "plamenak", "srnec", 
    "delfin", "kockodan", "hroch", "byk", "krecek", "los", 
    "jelen", "bizon", "kocour", "kolibrik", "pav", "albatros", 
    "holub", "netopyr", "mroz", "papousek", "klokan"
];

const animalsFeinineCZ = [
    "zirafa", "orlice", "kukacka", "koala", "panda", "sova", 
    "liska", "vcela", "vydra", "antilopa", "opice", "koza", 
    "slepice", "lama", "zebra", "mys", "velryba"
];

// ============================================================================
// SLOVAK - Slovenské vlastnosti, farby a zvieratá
// ============================================================================
const abilitiesMasculineSK = [
    "vesely",      // veselý - cheerful
    "hravy",       // hravý - playful
    "mily",        // milý - kind
    "zabavny",     // zábavný - fun
    "radostny",    // radostný - joyful
    "usmiaty",     // usmievavý - smiling
    "pratelsky",   // priateľský - friendly
    "stastny",     // šťastný - happy
    "energicky",   // energický - energetic
    "rozverny",    // rozverný - mischievous
    "vynaliezavy", // vynaliezavý - inventive
    "kouzelny",    // čarovný - magical
    "hodny",       // hodný - good
    "sikovny",     // šikovný - skillful
    "bystry",      // bystrý - sharp
    "chytry",      // chytrý - clever
    "zvedavy",     // zvedavý - curious
    "roztomily",   // roztomilý - cute
    "neposedny",   // neposedný - restless
    "pohodovy",    // pohodový - easygoing
    "rozesmaty",   // rozosmiaty - laughing
    "rozkosny",    // rozkošný - adorable
    "hrdinsky",    // hrdinský - heroic
    "napadity",    // nápaditý - creative
    "laskavy",     // laskavý - loving
    "kamaratsky",  // kamarátsky - friendly
    "dobrosrdecny",// dobrosrdečný - kind-hearted
    "nadherny",    // nádherný - gorgeous
    "dobrodruzny", // dobrodružný - adventurous
    "hrdy",        // hrdý - proud
    "odvazny",     // odvážny - brave
    "vtipny",      // vtipný - funny
    "jedinecny",   // jedinečný - unique
    "slnecny"      // slnečný - sunny
];

const abilitiesFeinineSK = [
    "vesela",      // veselá - cheerful
    "hrava",       // hravá - playful
    "mila",        // milá - kind
    "zabavna",     // zábavná - fun
    "radostna",    // radostná - joyful
    "usmiata",     // usmievavá - smiling
    "pratelska",   // priateľská - friendly
    "stastna",     // šťastná - happy
    "energicka",   // energická - energetic
    "rozverna",    // rozverná - mischievous
    "vynaliezava", // vynaliezavá - inventive
    "kouzelna",    // čarovná - magical
    "hodna",       // hodná - good
    "sikovna",     // šikovná - skillful
    "bystra",      // bystrá - sharp
    "chytra",      // chytrá - clever
    "zvedava",     // zvedavá - curious
    "roztomila",   // roztomilá - cute
    "neposedna",   // neposedná - restless
    "pohodova",    // pohodová - easygoing
    "rozesmata",   // rozosmiata - laughing
    "rozkosna",    // rozkošná - adorable
    "hrdinska",    // hrdinská - heroic
    "napadita",    // nápaditá - creative
    "laskava",     // laskavá - loving
    "kamaratska",  // kamarátska - friendly
    "dobrosrdecna",// dobrosrdečná - kind-hearted
    "nadherna",    // nádherná - gorgeous
    "dobrodruzna", // dobrodružná - adventurous
    "nevinna",     // nevinná - innocent
    "hrda",        // hrdá - proud
    "odvazna",     // odvážna - brave
    "vtipna",      // vtipná - funny
    "jedinecna",   // jedinečná - unique
    "slnecna"      // slnečná - sunny
];

const colorsMasculineSK = [
    "cierny",      // čierny - black
    "modry",       // modrý - blue
    "zeleny",      // zelený - green
    "zluty",       // žltý - yellow
    "fialovy",     // fialový - purple
    "oranzovy",    // oranžový - orange
    "ruzovy",      // ružový - pink
    "biely",       // biely - white
    "hnedy",       // hnedý - brown
    "sedy",        // šedý - gray
    "striebomy",   // strieborný - silver
    "bezovy",      // béžový - beige
    "miatovy",     // mätový - mint
    "tyrkysovy",   // tyrkysový - turquoise
    "neonovy",     // neónový - neon
    "olivovy",     // olivový - olive
    "safirovy",    // zafírový - sapphire
    "kremovy",     // krémový - cream
    "medeny",      // medený - copper
    "perletovy",   // perleťový - pearly
    "zlatavy"      // zlatavý - golden
];

const colorsFeinineSK = [
    "cierna",      // čierna - black
    "modra",       // modrá - blue
    "zelena",      // zelená - green
    "zlta",        // žltá - yellow
    "fialova",     // fialová - purple
    "oranzova",    // oranžová - orange
    "ruzova",      // ružová - pink
    "biela",       // biela - white
    "hneda",       // hnedá - brown
    "seda",        // šedá - gray
    "zlata",       // zlatá - gold
    "strieborna",  // strieborná - silver
    "bezova",      // béžová - beige
    "miatova",     // mätová - mint
    "tyrkysova",   // tyrkysová - turquoise
    "neonova",     // neónová - neon
    "olivova",     // olivová - olive
    "safirova",    // zafírová - sapphire
    "kremova",     // krémová - cream
    "medena",      // medená - copper
    "perletova",   // perleťová - pearly
    "zlatava"      // zlatavá - golden
];

const animalsMasculineSK = [
    "tiger",       // tiger - tiger
    "slon",        // slon - elephant
    "lev",         // lev - lion
    "pes",         // pes - dog
    "vlk",         // vlk - wolf
    "medved",      // medveď - bear
    "krokodil",    // krokodíl - crocodile
    "labrador",    // labrador - labrador
    "plameniak",   // plameniak - flamingo
    "jelen",       // jeleň - deer
    "delfin",      // delfín - dolphin
    "hroch",       // hroch - hippopotamus
    "byk",         // byk - bull
    "chrcek",      // škrečok - hamster
    "los",         // los - moose
    "bizon",       // bizón - bison
    "kocur",       // kocúr - tomcat
    "kolibrik",    // kolibrik - hummingbird
    "pav",         // páv - peacock
    "holub",       // holub - pigeon
    "netopier",    // netopier - bat
    "mroz",        // mrož - walrus
    "papagaj",     // papagáj - parrot
    "klokan"       // klokan - kangaroo
];

const animalsFeinineSK = [
    "zirafa",      // žirafa - giraffe
    "panda",       // panda - panda
    "sova",        // sova - owl
    "liska",       // líška - fox
    "vcela",       // včela - bee
    "vydra",       // vydra - otter
    "antilopa",    // antilopa - antelope
    "opica",       // opica - monkey
    "koza",        // koza - goat
    "sliepka",     // sliepka - hen
    "lama",        // lama - llama
    "zebra",       // zebra - zebra
    "mys",         // myš - mouse
    "velryba"      // veľryba - whale
]

// ============================================================================
// ENGLISH - English abilities, colors and animals
// ============================================================================
const abilitiesEn = [
    "cheerful", "playful", "kind", "fun", "joyful", "smiling", "friendly", "happy", "energetic",
    "mischievous", "inventive", "magical", "good-hearted", "wizardly", "skillful", "sharp", "clever",
    "curious", "cute", "crazy", "restless", "easygoing", "laughing", "adorable", "heroic",
    "creative", "loving", "innocent", "friendly", "kind-hearted", "gorgeous", "adventurous",
    "proud", "brave", "lively", "funny", "unique", "sunny"
];  

const colorsEn = [
    "black", "blue", "green", "yellow", "purple", "orange", "pink", "white", "brown", "gray", 
    "silver", "beige", "mint", "turquoise", "neon", "olive", "sapphire", "cream", "copper", 
    "pearly", "golden"
];

const animalsEn = [
    "tiger", "elephant", "lion", "crab", "dog", "wolf", "bear", "crocodile", "ostrich", "labrador",
    "flamingo", "deer", "dolphin", "monkey", "hippopotamus", "bull", "hamster", "moose",
    "bison", "tomcat", "hummingbird", "peacock", "albatross", "pigeon", "bat", "walrus",
    "parrot", "kangaroo", "giraffe", "eagle", "cuckoo", "koala", "panda", "owl", "fox", "bee", "otter",
    "antelope", "goat", "hen", "llama", "zebra", "mouse", "whale"
];

const getRandomItem = (arr, rng) => arr[Math.floor(rng() * arr.length)];

const generatePassphrase = (language) => {
    // Time-based seed for randomness
    let seed = Date.now().toString(); 

    const rng = seedrandom(seed);

    // Randomly select grammatical gender for Czech/Slovak
    const gender = Math.random() < 0.5 ? "masculine" : "feminine";

    let ability, color, animal;

    // Czech language
    if (language === "cs") {
        if (gender === "masculine") {
            ability = getRandomItem(abilitiesMasculineCZ, rng);
            color = getRandomItem(colorsMasculineCZ, rng);
            animal = getRandomItem(animalsMasculineCZ, rng);
        } else {
            ability = getRandomItem(abilitiesFeinineCZ, rng);
            color = getRandomItem(colorsFeinineCZ, rng);
            animal = getRandomItem(animalsFeinineCZ, rng);
        }
    }
    // Slovak language
    else if (language === "sk") {
        if (gender === "masculine") {
            ability = getRandomItem(abilitiesMasculineSK, rng);
            color = getRandomItem(colorsMasculineSK, rng);
            animal = getRandomItem(animalsMasculineSK, rng);
        } else {
            ability = getRandomItem(abilitiesFeinineSK, rng);
            color = getRandomItem(colorsFeinineSK, rng);
            animal = getRandomItem(animalsFeinineSK, rng);
        }
    } 
    // English language
    else {
        ability = getRandomItem(abilitiesEn, rng);
        color = getRandomItem(colorsEn, rng);
        animal = getRandomItem(animalsEn, rng);
    }
    return `${ability}-${color}-${animal}`;
};

export default generatePassphrase;
