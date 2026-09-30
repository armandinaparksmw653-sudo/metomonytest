-- | Real, corpus-attested Part-for-whole (synecdoche) examples (ConMeC
-- METONYMIC/POSSESSED category): a weapon type standing for the
-- military branch/unit that operates it. Flagship: "Egyptian artillery
-- shelled the Israeli bridge over the canal on the morning of October
-- 17, scoring several hits", simplified to "artillery shelled a
-- bridge". Scale-tier (same mechanism, two more real, historically
-- distinct sentences): "On November 23, 2010, North Korean artillery
-- shelled Yeonpyeong with dozens of rounds..." (the real Bombardment of
-- Yeonpyeong); "Confederate artillery gained an early advantage."
--
-- A third distinct transfer mechanism, structurally different from
-- location-for-institution (InstitutionOf/GovernedBy),
-- container-for-content/producer-for-product (Contains/Produces,
-- Metonymy.ContainerContent), and cause-for-effect (Causes,
-- Metonymy.CauseEffect): here the source (the part/weapon) is not
-- contained by, produced by, nor a cause of the target, it is
-- affiliated with it -- reuses the already-defined but previously
-- unused AffiliatedWith relation. Like the other ContainerContent-
-- family sources, none of these three "artillery" mentions are
-- independently Wikidata-linkable as the specific referents of their
-- one sentence (there is no distinct QID for "the artillery corps that
-- did the shelling in this one sentence"), so this is a small,
-- hand-built local graph in data/container-content-snapshot, the same
-- honesty tier as the existing examples there. Each has exactly one
-- real affiliation edge (no decoys), so each tower narrows to a unique
-- candidate through the graph walk alone, with no extra Requires signal
-- needed.
module Metonymy.PartWhole
  ( artilleryContext
  , artillerySource
  , egyptianMilitary
  , northKoreanArtilleryContext
  , northKoreanArtillerySource
  , northKoreanMilitary
  , confederateArtilleryContext
  , confederateArtillerySource
  , confederateArmy
  ) where

import Metonymy.Contextual
import Metonymy.Types

anchor :: String -> String -> String -> Int -> Int -> LexicalAnchor
anchor constructor lemma surface start end =
  LexicalAnchor constructor lemma surface start end

partWholeContext :: Snapshot -> EntityId -> Context
partWholeContext snapshot source =
  Context
    { contextTree =
        LexicalApply
          "Pred"
          [ LexicalLeaf (anchor "Noun" "artillery" "artillery" 0 9) []
          , LexicalApply
              "Compl"
              [ LexicalLeaf
                  (anchor "Verb" "shell" "shelled" 10 17)
                  [Prefers (HasSort Entity)]
              , LexicalLeaf (anchor "Noun" "bridge" "bridge" 22 28) []
              ]
          ]
    , contextSnapshotHash = snapshotHash snapshot
    , contextSource = source
    , contextAction = "shell"
    , contextRole = SubjectHole
    , contextConstraints =
        [ ContextConstraint
            (anchor "Verb" "shell" "shelled" 10 17)
            (Prefers (HasSort Entity))
            "local:selectional-lexicon"
        ]
    , contextRuleProvenance = ["local:selectional-lexicon"]
    }

artilleryContext, northKoreanArtilleryContext, confederateArtilleryContext :: Snapshot -> Context
artilleryContext snapshot = partWholeContext snapshot artillerySource
northKoreanArtilleryContext snapshot = partWholeContext snapshot northKoreanArtillerySource
confederateArtilleryContext snapshot = partWholeContext snapshot confederateArtillerySource

artillerySource, egyptianMilitary, northKoreanArtillerySource, northKoreanMilitary, confederateArtillerySource, confederateArmy :: EntityId
artillerySource = EntityId "LOCAL_ARTILLERY"
egyptianMilitary = EntityId "LOCAL_EGYPTIAN_MILITARY"
northKoreanArtillerySource = EntityId "LOCAL_NORTH_KOREAN_ARTILLERY"
northKoreanMilitary = EntityId "LOCAL_NORTH_KOREAN_MILITARY"
confederateArtillerySource = EntityId "LOCAL_CONFEDERATE_ARTILLERY"
confederateArmy = EntityId "LOCAL_CONFEDERATE_ARMY"
