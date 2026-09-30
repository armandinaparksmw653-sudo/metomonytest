-- | The first real, corpus-attested Material-for-object example: "Near
-- the LP version's fade-out, the brass play a citation of the Jazz tune
-- Topsy" (real ConMeC METONYMIC/CAUSER-category sentence, target word
-- "brass" -- the material standing for the instrument section made of
-- it), simplified to "the brass plays a citation".
--
-- A fifth distinct transfer mechanism: the source (a material) neither
-- causes, contains, produces, nor is affiliated with the target -- it
-- *represents* it (the target is made of, or characterized by, that
-- material). Reuses the already-defined but previously unused Represents
-- relation. ConMeC itself files this sentence under the same CAUSER
-- category as Metonymy.CauseEffect's trumpet example (a brass instrument
-- causing a sound would be the more literal reading of "the brass play"),
-- but the target word here is the *material* the instrument section is
-- made of, not the instrument or its sound -- a genuinely different
-- transfer (material stands for the object made of it), hence the
-- separate relation rather than reusing Causes. Like the other
-- ContainerContent-family sources, "the brass" and "the brass section"
-- are not independently Wikidata-linkable as the specific referents of
-- this one sentence, so this is a small, hand-built local graph in
-- data/container-content-snapshot, the same honesty tier as the existing
-- examples there. Exactly one real edge (no decoys), so the tower
-- narrows to a unique candidate through the graph walk alone, with no
-- extra Requires signal needed.
module Metonymy.MaterialObject
  ( brassContext
  , brassSource
  , brassSection
  ) where

import Metonymy.Contextual
import Metonymy.Types

anchor :: String -> String -> String -> Int -> Int -> LexicalAnchor
anchor constructor lemma surface start end =
  LexicalAnchor constructor lemma surface start end

brassContext :: Snapshot -> Context
brassContext snapshot =
  Context
    { contextTree =
        LexicalApply
          "Pred"
          [ LexicalLeaf (anchor "Noun" "brass" "brass" 0 5) []
          , LexicalApply
              "Compl"
              [ LexicalLeaf
                  (anchor "Verb" "play" "plays" 6 11)
                  [Prefers (HasSort Entity)]
              , LexicalLeaf (anchor "Noun" "citation" "citation" 15 23) []
              ]
          ]
    , contextSnapshotHash = snapshotHash snapshot
    , contextSource = brassSource
    , contextAction = "play"
    , contextRole = SubjectHole
    , contextConstraints =
        [ ContextConstraint
            (anchor "Verb" "play" "plays" 6 11)
            (Prefers (HasSort Entity))
            "local:selectional-lexicon"
        ]
    , contextRuleProvenance = ["local:selectional-lexicon"]
    }

brassSource, brassSection :: EntityId
brassSource = EntityId "LOCAL_BRASS"
brassSection = EntityId "LOCAL_BRASS_SECTION"
