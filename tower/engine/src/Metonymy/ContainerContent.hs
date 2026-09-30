-- | Four real, corpus-attested examples of two different transfer
-- mechanisms -- container-for-content (ConMeC CONTAINER category) and
-- producer-for-product (ConMeC PRODUCER category), METONYMIC label in
-- both -- neither of which is the location-for-institution family
-- (Waterloo/Molde/Cupertino): the source is not a real-world,
-- independently identifiable entity (a glass/carton/six-pack/orchestra
-- in one narrative has no Wikidata QID), so each is a small, hand-built
-- local graph (same honesty tier as Metonymy.SyntheticTowers), just
-- grounded in real sentences rather than invented ones. Each source has
-- exactly one real target edge (no decoys), so the tower narrows to a
-- unique candidate through the graph walk alone, with no extra Requires
-- signal needed -- the same "zero extra constraints, the graph topology
-- alone already disambiguates" shape as the base WiMCor pilot-decode
-- examples (Pomona/Leicester).
--
-- Real source sentences, simplified to the same representative-tree
-- style already used for Molde/Waterloo:
--   "He says 'I've never tasted rum', downs the glass..." -> "he drinks
--   the glass" (glass -> Contains -> rum)
--   "He lands next to some milk... drinks the entire carton." -> "he
--   drinks the carton" (carton -> Contains -> milk)
--   "Detective Rust Cohle... drinks a six pack..." -> "he drinks a pack"
--   (pack -> Contains -> beer)
--   "Duke Ellington made a 1935 visit to hear Wheatley's orchestra." ->
--   "he hears the orchestra" (orchestra -> Produces -> symphony; "Hear"
--   is a real V2, generated from data/predicates.tsv into
--   grammar/GeneratedMetonymyEng.gf, verified there against the local
--   gf.exe/pinned gf-rgl build -- the base grammar/MetonymyEng.gf this
--   module's other three contexts use does not itself declare it)
module Metonymy.ContainerContent
  ( glassContext
  , cartonContext
  , packContext
  , orchestraContext
  , kettleContext
  , tankContext
  , canisterContext
  , barrelContext
  , extinguisherContext
  , syringeContext
  , reservoirContext
  , platterContext
  , poolContext
  , cupContext
  , flaskContext
  , pitcherContext
  , jarContext
  , mugContext
  , bowlContext
  , hoseContext
  , bucketContext
  , casseroleContext
  , bottleContext
  , caskContext
  , containerContext2
  , potContext
  , pianistContext
  , bandContext
  , poetContext
  , playwrightContext
  , journalistContext
  , philosopherContext
  , glassEntity
  , rumEntity
  , cartonEntity
  , milkEntity
  , packEntity
  , beerEntity
  , orchestraEntity
  , symphonyEntity
  , kettleEntity
  , waterEntity
  , tankEntity
  , oxygenEntity
  , canisterEntity
  , shotEntity
  , barrelEntity
  , wineEntity
  , extinguisherEntity
  , foamEntity
  , syringeEntity
  , drugEntity
  , reservoirEntity
  , platterEntity
  , foodEntity
  , poolEntity
  , workersEntity
  , cupEntity
  , flaskEntity
  , liquorEntity
  , pitcherEntity
  , jarEntity
  , mugEntity
  , coffeeEntity
  , bowlEntity
  , soupEntity
  , hoseEntity
  , bucketEntity
  , casseroleEntity
  , lentilsEntity
  , bottleEntity
  , caskEntity
  , aleEntity
  , container2Entity
  , liquidEntity
  , potEntity
  , stewEntity
  , pianistEntity
  , performanceEntity
  , bandEntity
  , musicEntity
  , poetEntity
  , poemsEntity
  , playwrightEntity
  , playEntity
  , journalistEntity
  , articlesEntity
  , philosopherEntity
  , theoryEntity
  ) where

import Metonymy.Contextual
import Metonymy.Types

anchor :: String -> String -> String -> Int -> Int -> LexicalAnchor
anchor constructor lemma surface start end =
  LexicalAnchor constructor lemma surface start end

containerContext ::
  Snapshot -> EntityId -> String -> Int -> Int -> Context
containerContext snapshot source noun start end =
  Context
    { contextTree =
        LexicalApply
          "Pred"
          [ LexicalLeaf (anchor "HePN" "he" "he" 0 2) []
          , LexicalApply
              "Compl"
              [ LexicalLeaf
                  (anchor "Verb" "drink" "drinks" 3 9)
                  [Prefers (HasSort Entity)]
              , LexicalLeaf (anchor "Noun" noun noun start end) []
              ]
          ]
    , contextSnapshotHash = snapshotHash snapshot
    , contextSource = source
    , contextAction = "drink"
    , contextRole = ObjectHole
    , contextConstraints =
        [ ContextConstraint
            (anchor "Verb" "drink" "drinks" 3 9)
            (Prefers (HasSort Entity))
            "local:selectional-lexicon"
        ]
    , contextRuleProvenance = ["local:selectional-lexicon"]
    }

glassContext, cartonContext, packContext :: Snapshot -> Context
glassContext snapshot = containerContext snapshot glassEntity "glass" 14 19
cartonContext snapshot = containerContext snapshot cartonEntity "carton" 14 20
packContext snapshot = containerContext snapshot packEntity "pack" 12 16

-- "he hears the orchestra": orchestra -> Produces -> symphony
orchestraContext :: Snapshot -> Context
orchestraContext snapshot =
  Context
    { contextTree =
        LexicalApply
          "Pred"
          [ LexicalLeaf (anchor "HePN" "he" "he" 0 2) []
          , LexicalApply
              "Compl"
              [ LexicalLeaf
                  (anchor "Verb" "hear" "hears" 3 8)
                  [Prefers (HasSort Entity)]
              , LexicalLeaf (anchor "Noun" "orchestra" "orchestra" 13 22) []
              ]
          ]
    , contextSnapshotHash = snapshotHash snapshot
    , contextSource = orchestraEntity
    , contextAction = "hear"
    , contextRole = ObjectHole
    , contextConstraints =
        [ ContextConstraint
            (anchor "Verb" "hear" "hears" 3 8)
            (Prefers (HasSort Entity))
            "local:selectional-lexicon"
        ]
    , contextRuleProvenance = ["local:selectional-lexicon"]
    }

glassEntity, rumEntity, cartonEntity, milkEntity, packEntity, beerEntity :: EntityId
glassEntity = EntityId "LOCAL_GLASS"
rumEntity = EntityId "LOCAL_RUM"
cartonEntity = EntityId "LOCAL_CARTON"
milkEntity = EntityId "LOCAL_MILK"
packEntity = EntityId "LOCAL_PACK"
beerEntity = EntityId "LOCAL_BEER"

orchestraEntity, symphonyEntity :: EntityId
orchestraEntity = EntityId "LOCAL_ORCHESTRA"
symphonyEntity = EntityId "LOCAL_SYMPHONY"

-- Scale batch 4: four more real ConMeC CONTAINER-category sentences,
-- simplified to "he empties the X" (a new Empty V2, since "drink" only
-- fits liquid content -- oxygen and shot are not drinkable), plus one
-- more real CONTAINER sentence ("Gutiérrez's in-car fire extinguisher
-- activated...", already surfaced but not built earlier this session):
--   "her grandmother's need to recharge her oxygen tank every two days"
--   -> tank -> Contains -> oxygen
--   "the American gunners switched from firing roundshot to firing
--   canister" -> canister -> Contains -> shot
--   "a single grape, chardonnay... barrel fermented" -> barrel ->
--   Contains -> wine
--   "He invites Stevie to stay for coffee, saying Gerri is just boiling
--   the kettle" -> kettle -> Contains -> water
--   "Gutiérrez's in-car fire extinguisher activated..." -> extinguisher
--   -> Contains -> foam
emptyContext :: Snapshot -> EntityId -> String -> Context
emptyContext snapshot source noun =
  Context
    { contextTree =
        LexicalApply
          "Pred"
          [ LexicalLeaf (anchor "HePN" "he" "he" 0 2) []
          , LexicalApply
              "Compl"
              [ LexicalLeaf
                  (anchor "Verb" "empty" "empties" 3 10)
                  [Prefers (HasSort Entity)]
              , LexicalLeaf (anchor "Noun" noun noun 15 (15 + length noun)) []
              ]
          ]
    , contextSnapshotHash = snapshotHash snapshot
    , contextSource = source
    , contextAction = "empty"
    , contextRole = ObjectHole
    , contextConstraints =
        [ ContextConstraint
            (anchor "Verb" "empty" "empties" 3 10)
            (Prefers (HasSort Entity))
            "local:selectional-lexicon"
        ]
    , contextRuleProvenance = ["local:selectional-lexicon"]
    }

kettleContext, tankContext, canisterContext, barrelContext, extinguisherContext :: Snapshot -> Context
kettleContext snapshot = emptyContext snapshot kettleEntity "kettle"
tankContext snapshot = emptyContext snapshot tankEntity "tank"
canisterContext snapshot = emptyContext snapshot canisterEntity "canister"
barrelContext snapshot = emptyContext snapshot barrelEntity "barrel"
extinguisherContext snapshot = emptyContext snapshot extinguisherEntity "extinguisher"

kettleEntity, waterEntity, tankEntity, oxygenEntity, canisterEntity, shotEntity, barrelEntity, wineEntity, extinguisherEntity, foamEntity :: EntityId
kettleEntity = EntityId "LOCAL_KETTLE"
waterEntity = EntityId "LOCAL_WATER"
tankEntity = EntityId "LOCAL_TANK"
oxygenEntity = EntityId "LOCAL_OXYGEN"
canisterEntity = EntityId "LOCAL_CANISTER"
shotEntity = EntityId "LOCAL_SHOT"
barrelEntity = EntityId "LOCAL_BARREL"
wineEntity = EntityId "LOCAL_WINE"
extinguisherEntity = EntityId "LOCAL_EXTINGUISHER"
foamEntity = EntityId "LOCAL_FOAM"

-- Scale batch 7: five more real ConMeC CONTAINER examples:
--   "she decides to administer a syringe of drugs to end his life" ->
--   syringe -> Contains -> drug
--   "Jonesy... steps on the final alien larva before it can contaminate
--   the reservoir" -> reservoir -> Contains -> water
--   "Janella cooked... an antipasto platter for starters" -> platter ->
--   Contains -> food
--   "the labor pool dried up" -> pool -> Contains -> workers (the one
--   example in this module where the content is a HumanGroup, not a
--   substance)
--   ceremonial "this cup was sipped by the leader" (Thanksgiving/Seder
--   sentences) -> cup -> Contains -> wine
syringeContext, reservoirContext, platterContext, poolContext, cupContext :: Snapshot -> Context
syringeContext snapshot = emptyContext snapshot syringeEntity "syringe"
reservoirContext snapshot = emptyContext snapshot reservoirEntity "reservoir"
platterContext snapshot = emptyContext snapshot platterEntity "platter"
poolContext snapshot = emptyContext snapshot poolEntity "pool"
cupContext snapshot = emptyContext snapshot cupEntity "cup"

syringeEntity, drugEntity, reservoirEntity, platterEntity, foodEntity, poolEntity, workersEntity, cupEntity :: EntityId
syringeEntity = EntityId "LOCAL_SYRINGE"
drugEntity = EntityId "LOCAL_DRUG"
reservoirEntity = EntityId "LOCAL_RESERVOIR"
platterEntity = EntityId "LOCAL_PLATTER"
foodEntity = EntityId "LOCAL_FOOD"
poolEntity = EntityId "LOCAL_POOL"
workersEntity = EntityId "LOCAL_WORKERS"
cupEntity = EntityId "LOCAL_CUP"

-- Scale batch 11: six more real ConMeC CONTAINER examples:
--   "Roman complies and drinks the flask" -> flask -> Contains -> liquor
--   "He was challenged... to drink the pitcher" -> pitcher -> Contains
--   -> water
--   "he drinks the occasional jar in pubs" -> jar -> Contains -> beer
--   (Irish/British informal usage: "a jar" = a pint of beer)
--   "tap the keg and properly pour a mug" -> mug -> Contains -> coffee
--   "Singari cooks a bowl and serves it" -> bowl -> Contains -> soup
--   "direct a hose on to the roof" -> hose -> Contains -> water
flaskContext, pitcherContext, jarContext, mugContext, bowlContext, hoseContext :: Snapshot -> Context
flaskContext snapshot = emptyContext snapshot flaskEntity "flask"
pitcherContext snapshot = emptyContext snapshot pitcherEntity "pitcher"
jarContext snapshot = emptyContext snapshot jarEntity "jar"
mugContext snapshot = emptyContext snapshot mugEntity "mug"
bowlContext snapshot = emptyContext snapshot bowlEntity "bowl"
hoseContext snapshot = emptyContext snapshot hoseEntity "hose"

flaskEntity, liquorEntity, pitcherEntity, jarEntity, mugEntity, coffeeEntity, bowlEntity, soupEntity, hoseEntity :: EntityId
flaskEntity = EntityId "LOCAL_FLASK"
liquorEntity = EntityId "LOCAL_LIQUOR"
pitcherEntity = EntityId "LOCAL_PITCHER"
jarEntity = EntityId "LOCAL_JAR"
mugEntity = EntityId "LOCAL_MUG"
coffeeEntity = EntityId "LOCAL_COFFEE"
bowlEntity = EntityId "LOCAL_BOWL"
soupEntity = EntityId "LOCAL_SOUP"
hoseEntity = EntityId "LOCAL_HOSE"

-- Scale batch 13: six more real ConMeC CONTAINER examples:
--   "they must pour their bucket into their container" -> bucket ->
--   Contains -> water
--   "Neil cooks a lentil casserole" -> casserole -> Contains -> lentils
--   "an opened bottle will survive unharmed" (Madeira) -> bottle ->
--   Contains -> wine
--   "cask conditioned beers"/"cask and keg ales" -> cask -> Contains ->
--   ale
--   "disposed of the remains by pouring out the container" ->
--   container -> Contains -> liquid
--   "A pot is boiling there" -> pot -> Contains -> stew
bucketContext, casseroleContext, bottleContext, caskContext, containerContext2, potContext :: Snapshot -> Context
bucketContext snapshot = emptyContext snapshot bucketEntity "bucket"
casseroleContext snapshot = emptyContext snapshot casseroleEntity "casserole"
bottleContext snapshot = emptyContext snapshot bottleEntity "bottle"
caskContext snapshot = emptyContext snapshot caskEntity "cask"
containerContext2 snapshot = emptyContext snapshot container2Entity "container"
potContext snapshot = emptyContext snapshot potEntity "pot"

bucketEntity, casseroleEntity, lentilsEntity, bottleEntity, caskEntity, aleEntity, container2Entity, liquidEntity, potEntity, stewEntity :: EntityId
bucketEntity = EntityId "LOCAL_BUCKET"
casseroleEntity = EntityId "LOCAL_CASSEROLE"
lentilsEntity = EntityId "LOCAL_LENTILS"
bottleEntity = EntityId "LOCAL_BOTTLE"
caskEntity = EntityId "LOCAL_CASK"
aleEntity = EntityId "LOCAL_ALE"
container2Entity = EntityId "LOCAL_CONTAINER"
liquidEntity = EntityId "LOCAL_LIQUID"
potEntity = EntityId "LOCAL_POT"
stewEntity = EntityId "LOCAL_STEW"

-- Scale-tier diversity pass 3: four more real ConMeC PRODUCER examples
-- (the same mechanism as orchestra -> symphony, not container-for-
-- content), splitting between the two verbs the real sentences actually
-- use: "hear" for performers ("I have never heard such a pianist
-- before...", "the great Earl Hines band") and the base grammar's own
-- "Read" V2 for writers ("he studied the Romantic poet Novalis",
-- "cited the playwright Trevor Griffiths") -- the same Producer graph
-- shape (Contains a real P176 producer->product edge), reached through
-- two different real verbs rather than always "hear".
producerContext :: Snapshot -> EntityId -> String -> String -> String -> Context
producerContext snapshot source verbLemma verbSurface noun =
  Context
    { contextTree =
        LexicalApply
          "Pred"
          [ LexicalLeaf (anchor "HePN" "he" "he" 0 2) []
          , LexicalApply
              "Compl"
              [ LexicalLeaf
                  (anchor "Verb" verbLemma verbSurface 3 8)
                  [Prefers (HasSort Entity)]
              , LexicalLeaf (anchor "Noun" noun noun 13 (13 + length noun)) []
              ]
          ]
    , contextSnapshotHash = snapshotHash snapshot
    , contextSource = source
    , contextAction = verbLemma
    , contextRole = ObjectHole
    , contextConstraints =
        [ ContextConstraint
            (anchor "Verb" verbLemma verbSurface 3 8)
            (Prefers (HasSort Entity))
            "local:selectional-lexicon"
        ]
    , contextRuleProvenance = ["local:selectional-lexicon"]
    }

-- Scale-tier diversity: two more real ConMeC PRODUCER-category
-- sentences, each a different verb/family from the four above --
-- "As the forerunner of today's popular advice columnists, Dix was
-- America's highest paid and most widely read female journalist at the
-- time of her death" (reading a journalist -> reading her columns, not
-- literally the person) and "Avicenna's commentaries on Aristotle often
-- criticized the philosopher, encouraging a lively debate in the spirit
-- of ijtihad" (criticizing a philosopher -> criticizing his theory, not
-- literally the long-dead person).
pianistContext, bandContext, poetContext, playwrightContext, journalistContext, philosopherContext :: Snapshot -> Context
pianistContext snapshot = producerContext snapshot pianistEntity "hear" "hears" "pianist"
bandContext snapshot = producerContext snapshot bandEntity "hear" "hears" "band"
poetContext snapshot = producerContext snapshot poetEntity "read" "reads" "poet"
playwrightContext snapshot = producerContext snapshot playwrightEntity "read" "reads" "playwright"
journalistContext snapshot = producerContext snapshot journalistEntity "read" "reads" "journalist"
philosopherContext snapshot = producerContext snapshot philosopherEntity "criticize" "criticizes" "philosopher"

pianistEntity, performanceEntity, bandEntity, musicEntity, poetEntity, poemsEntity, playwrightEntity, playEntity, journalistEntity, articlesEntity, philosopherEntity, theoryEntity :: EntityId
pianistEntity = EntityId "LOCAL_PIANIST"
performanceEntity = EntityId "LOCAL_PERFORMANCE"
bandEntity = EntityId "LOCAL_BAND"
musicEntity = EntityId "LOCAL_MUSIC"
poetEntity = EntityId "LOCAL_POET"
poemsEntity = EntityId "LOCAL_POEMS"
playwrightEntity = EntityId "LOCAL_PLAYWRIGHT"
playEntity = EntityId "LOCAL_PLAY"
journalistEntity = EntityId "LOCAL_JOURNALIST"
articlesEntity = EntityId "LOCAL_ARTICLES"
philosopherEntity = EntityId "LOCAL_PHILOSOPHER"
theoryEntity = EntityId "LOCAL_THEORY"
