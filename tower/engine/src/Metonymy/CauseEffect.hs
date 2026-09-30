-- | Real, corpus-attested Cause-for-effect examples (ConMeC METONYMIC/
-- CAUSER category): an instrument/device standing for the sound it
-- causes. Flagship: "A trumpet is also heard in the song right after
-- this line is sung", simplified to "he hears a trumpet". Scale-tier
-- (same mechanism, three more real sentences, same "hear" verb):
-- "A two-minute siren is heard at 11:00, which marks the opening of the
-- official military memorial ceremonies..."; "Only the organ can be
-- heard throughout; the other instruments are not playing simultaneously
-- the whole time."; "Once they have left, the workers hear a horn, and
-- celebrate that their work is finished for the day."
--
-- A fourth distinct transfer mechanism, structurally different from
-- location-for-institution (InstitutionOf/GovernedBy),
-- container-for-content/producer-for-product (Contains/Produces,
-- Metonymy.ContainerContent), and part-for-whole (AffiliatedWith,
-- Metonymy.PartWhole): here the source (the cause) is not contained by,
-- produced by, nor affiliated with the target, it *causes* it -- reuses
-- the already-defined but previously unused Causes relation. Like the
-- other ContainerContent-family sources, none of these devices and
-- their sounds are independently Wikidata-linkable as the specific
-- referents of their one sentence, so this is a small, hand-built local
-- graph in data/container-content-snapshot, the same honesty tier as
-- the existing examples there. Each has exactly one real causal edge (no
-- decoys), so each tower narrows to a unique candidate through the graph
-- walk alone, with no extra Requires signal needed.
module Metonymy.CauseEffect
  ( trumpetContext
  , trumpetSource
  , trumpetSound
  , sirenContext
  , sirenSource
  , sirenSound
  , organContext
  , organSource
  , organSound
  , hornContext
  , hornSource
  , hornSound
  ) where

import Metonymy.Contextual
import Metonymy.Types

anchor :: String -> String -> String -> Int -> Int -> LexicalAnchor
anchor constructor lemma surface start end =
  LexicalAnchor constructor lemma surface start end

causeContext :: Snapshot -> EntityId -> String -> Context
causeContext snapshot source noun =
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
              , LexicalLeaf (anchor "Noun" noun noun 11 (11 + length noun)) []
              ]
          ]
    , contextSnapshotHash = snapshotHash snapshot
    , contextSource = source
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

trumpetContext, sirenContext, organContext, hornContext :: Snapshot -> Context
trumpetContext snapshot = causeContext snapshot trumpetSource "trumpet"
sirenContext snapshot = causeContext snapshot sirenSource "siren"
organContext snapshot = causeContext snapshot organSource "organ"
hornContext snapshot = causeContext snapshot hornSource "horn"

trumpetSource, trumpetSound, sirenSource, sirenSound, organSource, organSound, hornSource, hornSound :: EntityId
trumpetSource = EntityId "LOCAL_TRUMPET"
trumpetSound = EntityId "LOCAL_TRUMPET_SOUND"
sirenSource = EntityId "LOCAL_SIREN"
sirenSound = EntityId "LOCAL_SIREN_SOUND"
organSource = EntityId "LOCAL_ORGAN"
organSound = EntityId "LOCAL_ORGAN_SOUND"
hornSource = EntityId "LOCAL_HORN"
hornSound = EntityId "LOCAL_HORN_SOUND"
