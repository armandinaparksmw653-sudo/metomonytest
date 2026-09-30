-- | The Haskell-module half of the curated 124-example database (the
-- other half, 72 scale-tier scenarios, lives in
-- tower/data/contextual-scenarios.tsv and is loaded at runtime via
-- Metonymy.ContextSpec.loadContextScenarios -- see
-- Metonymy.Report.exampleReports, which merges both halves).
--
-- Every entry here mirrors a (name, relations, maxDepth, context)
-- combination that is independently exercised and asserted against in
-- tower/engine/test/Main.hs. This module is deliberately NOT imported by
-- that test file, and this list is NOT auto-derived from it: the two are
-- independent, hand-kept-in-sync sources. That duplication is an
-- accepted, low-risk trade-off (see tower/README.md) -- this module
-- drives only the report tool's printing, never a pass/fail assertion,
-- so if it ever drifts from test/Main.hs the worst outcome is a stale
-- report, not a false sense of correctness: `make test` alone still
-- carries the actual verification guarantee.
--
-- Deliberately excluded: the five Metonymy.SyntheticTowers fixtures
-- (fully fictional entities used only to test multi-constraint
-- narrowing mechanics -- not part of the corpus-attested 124-example
-- publication database); "Amherst" (lives only in
-- auxiliary/evaluation/pilot-decode-wimcor/pilot-scenarios.tsv, a
-- manual-only pilot workflow fixture, never asserted in
-- tower/engine/test/Main.hs -- found and dropped from the flagship
-- count during this reorganization); and the Rijeka+glass composition
-- example (built in test/Main.hs as a local, unexported `let`-bound
-- Context using a raw "AndS"-rooted LexicalTree, not a named function
-- any other module can import -- re-deriving it here risked a silent
-- transcription drift from the one true, CI-checked copy, for a
-- demonstration Rijeka and glass already cover individually).
module Metonymy.ExampleDatabase
  ( ExampleEntry (..)
  , SnapshotChoice (..)
  , exampleDatabase
  , exampleSnapshotOf
  ) where

import Metonymy.AuthorWork
import Metonymy.Busan
import Metonymy.Cathedrals
import Metonymy.CauseEffect
import Metonymy.ContainerContent
import Metonymy.Contextual
import Metonymy.Eswatini
import Metonymy.FleetStreet
import Metonymy.MaterialObject
import Metonymy.MoldeFK
import Metonymy.PartWhole
import Metonymy.Rijeka
import Metonymy.Types
import Metonymy.Waterloo

-- | One printable example. 'exampleContractionTarget', when present, is
-- additionally attempted via contextualContractionChecked (not just the
-- bare fiber) -- used for the two reject-test entries, where the fiber
-- alone would look identical to the accepting case and the interesting
-- result is specifically the contraction being refused.
data ExampleEntry = ExampleEntry
  { exampleName :: String
  , exampleTier :: String
  , exampleSnapshot :: SnapshotChoice
  , exampleRelations :: [Relation]
  , exampleMaxDepth :: Int
  , exampleContextOf :: Snapshot -> Context
  , exampleContractionTarget :: Maybe EntityId
  }

data SnapshotChoice = WikidataQid | ContainerContentSnapshot

exampleDatabase :: [ExampleEntry]
exampleDatabase =
  -- Flagship (15 Haskell-module entries; the 16th, Aberystwyth/Offer,
  -- is TSV-driven and comes from Metonymy.ContextSpec instead).
  [ entry "waterloo" "flagship" WikidataQid [InstitutionOf] 1 waterlooContextFor Nothing
  , entry "waterloo-depth-2" "flagship" WikidataQid [InstitutionOf] 2 waterlooContextFor Nothing
  , entry "molde" "flagship" WikidataQid [InstitutionOf] 1 moldeContextFor Nothing
  , entry "molde-rejects-bjorset-fk" "flagship" WikidataQid [InstitutionOf] 1 moldeContextFor (Just bjorsetFK)
  , entry "waterloo-rejects-city-council" "flagship" WikidataQid [InstitutionOf] 1 waterlooContextFor (Just (EntityId "Q7974219"))
  , entry "gloucester" "flagship" WikidataQid [InstitutionOf] 1 gloucesterContext Nothing
  , entry "eswatini" "flagship" WikidataQid [GovernedBy] 1 eswatiniContext Nothing
  , entry "busan" "flagship" WikidataQid [InstitutionOf] 1 busanContext Nothing
  , entry "novalis" "flagship" WikidataQid [Authored] 1 novalisContext Nothing
  , entry "fleet-street" "flagship" WikidataQid [InstitutionOf] 1 fleetStreetContext Nothing
  , entry "artillery" "flagship" ContainerContentSnapshot [AffiliatedWith] 1 artilleryContext Nothing
  , entry "trumpet" "flagship" ContainerContentSnapshot [Causes] 1 trumpetContext Nothing
  , entry "brass" "flagship" ContainerContentSnapshot [Represents] 1 brassContext Nothing
  , entry "glass" "flagship" ContainerContentSnapshot [Contains] 1 glassContext Nothing
  , entry "orchestra" "flagship" ContainerContentSnapshot [Produces] 1 orchestraContext Nothing
  , -- Scale-tier: demoted from flagship (real, unchanged from earlier
    -- in the session, just narratively recategorized -- see the
    -- "Перебалансировка" section of the example-database report).
    entry "rijeka" "scale" WikidataQid [InstitutionOf] 1 rijekaContext Nothing
  , entry "ely" "scale" WikidataQid [InstitutionOf] 1 elyContext Nothing
  , entry "carton" "scale" ContainerContentSnapshot [Contains] 1 cartonContext Nothing
  , entry "pack" "scale" ContainerContentSnapshot [Contains] 1 packContext Nothing
  , -- Scale-tier: Container-for-content (21 more real ConMeC sentences).
    entry "kettle" "scale" ContainerContentSnapshot [Contains] 1 kettleContext Nothing
  , entry "tank" "scale" ContainerContentSnapshot [Contains] 1 tankContext Nothing
  , entry "canister" "scale" ContainerContentSnapshot [Contains] 1 canisterContext Nothing
  , entry "barrel" "scale" ContainerContentSnapshot [Contains] 1 barrelContext Nothing
  , entry "extinguisher" "scale" ContainerContentSnapshot [Contains] 1 extinguisherContext Nothing
  , entry "syringe" "scale" ContainerContentSnapshot [Contains] 1 syringeContext Nothing
  , entry "reservoir" "scale" ContainerContentSnapshot [Contains] 1 reservoirContext Nothing
  , entry "platter" "scale" ContainerContentSnapshot [Contains] 1 platterContext Nothing
  , entry "pool" "scale" ContainerContentSnapshot [Contains] 1 poolContext Nothing
  , entry "cup" "scale" ContainerContentSnapshot [Contains] 1 cupContext Nothing
  , entry "flask" "scale" ContainerContentSnapshot [Contains] 1 flaskContext Nothing
  , entry "pitcher" "scale" ContainerContentSnapshot [Contains] 1 pitcherContext Nothing
  , entry "jar" "scale" ContainerContentSnapshot [Contains] 1 jarContext Nothing
  , entry "mug" "scale" ContainerContentSnapshot [Contains] 1 mugContext Nothing
  , entry "bowl" "scale" ContainerContentSnapshot [Contains] 1 bowlContext Nothing
  , entry "hose" "scale" ContainerContentSnapshot [Contains] 1 hoseContext Nothing
  , entry "bucket" "scale" ContainerContentSnapshot [Contains] 1 bucketContext Nothing
  , entry "casserole" "scale" ContainerContentSnapshot [Contains] 1 casseroleContext Nothing
  , entry "bottle" "scale" ContainerContentSnapshot [Contains] 1 bottleContext Nothing
  , entry "cask" "scale" ContainerContentSnapshot [Contains] 1 caskContext Nothing
  , entry "container2" "scale" ContainerContentSnapshot [Contains] 1 containerContext2 Nothing
  , entry "pot" "scale" ContainerContentSnapshot [Contains] 1 potContext Nothing
  , -- Scale-tier: Producer-for-product (6).
    entry "pianist" "scale" ContainerContentSnapshot [Produces] 1 pianistContext Nothing
  , entry "band" "scale" ContainerContentSnapshot [Produces] 1 bandContext Nothing
  , entry "poet" "scale" ContainerContentSnapshot [Produces] 1 poetContext Nothing
  , entry "playwright" "scale" ContainerContentSnapshot [Produces] 1 playwrightContext Nothing
  , entry "journalist" "scale" ContainerContentSnapshot [Produces] 1 journalistContext Nothing
  , entry "philosopher" "scale" ContainerContentSnapshot [Produces] 1 philosopherContext Nothing
  , -- Scale-tier: Part-for-whole (2 more, same mechanism as artillery).
    entry "north-korean-artillery" "scale" ContainerContentSnapshot [AffiliatedWith] 1 northKoreanArtilleryContext Nothing
  , entry "confederate-artillery" "scale" ContainerContentSnapshot [AffiliatedWith] 1 confederateArtilleryContext Nothing
  , -- Scale-tier: Cause-for-effect (3 more, same mechanism as trumpet).
    entry "siren" "scale" ContainerContentSnapshot [Causes] 1 sirenContext Nothing
  , entry "organ" "scale" ContainerContentSnapshot [Causes] 1 organContext Nothing
  , entry "horn" "scale" ContainerContentSnapshot [Causes] 1 hornContext Nothing
  ]
  where
    entry name tier snapshotChoice relations depth contextOf contractionTarget =
      ExampleEntry name tier snapshotChoice relations depth contextOf contractionTarget

-- | Resolves the two named snapshots a caller (Metonymy.Report) has
-- already loaded down to the one this entry actually needs.
exampleSnapshotOf :: Snapshot -> Snapshot -> ExampleEntry -> Snapshot
exampleSnapshotOf qidSnapshot containerSnapshot entryValue =
  case exampleSnapshot entryValue of
    WikidataQid -> qidSnapshot
    ContainerContentSnapshot -> containerSnapshot
