-- | A real, honest two-candidate tower: "Rijeka announced that Bezjak
-- had signed a three-year contract, tying him with the club until June
-- 2018" (real WiMCor sentence, TEAM medium), simplified to "Rijeka
-- announces a season".
--
-- Unlike Molde, a live SPARQL check found no lexical signal in this
-- sentence (no "on loan") that could distinguish the two real football
-- clubs both headquartered in Rijeka with a live P118 league claim:
-- HNK Rijeka (Q318969, the sentence's real referent) and NK Orijent
-- (Q1447572, dissolved 2014 -- a third, U.S. Fiumana Q1328077, was
-- dissolved in 1945 under Italian rule and is not included here as an
-- anachronistic decoy). Requires (HasSort SportsOrganization) -- via
-- "season", the same signal that (together with "on loan") gave Molde
-- FK a unique result -- only gets as far as these two real candidates
-- here, the same honest non-uniqueness as Waterloo and Eswatini.
module Metonymy.Rijeka
  ( rijekaContext
  , rijekaSource
  , hnkRijeka
  , nkOrijent
  ) where

import Metonymy.Contextual
import Metonymy.Types

anchor :: String -> String -> String -> Int -> Int -> LexicalAnchor
anchor constructor lemma surface start end =
  LexicalAnchor constructor lemma surface start end

rijekaContext :: Snapshot -> Context
rijekaContext snapshot =
  Context
    { contextTree =
        LexicalApply
          "Pred"
          [ LexicalLeaf (anchor "OpenPN" "rijeka" "Rijeka" 0 6) []
          , LexicalApply
              "Compl"
              [ LexicalLeaf
                  (anchor "Verb" "announce" "announces" 7 16)
                  [Requires (AnyOf [HasSort Animate, HasSort Organization])]
              , LexicalLeaf
                  (anchor "Noun" "season" "season" 19 25)
                  [Requires (HasSort SportsOrganization)]
              ]
          ]
    , contextSnapshotHash = snapshotHash snapshot
    , contextSource = rijekaSource
    , contextAction = "announce"
    , contextRole = SubjectHole
    , contextConstraints =
        [ ContextConstraint
            (anchor "Verb" "announce" "announces" 7 16)
            (Requires (AnyOf [HasSort Animate, HasSort Organization]))
            "VerbNet:say-37.7"
        , ContextConstraint
            (anchor "Noun" "season" "season" 19 25)
            (Requires (HasSort SportsOrganization))
            "wimcor:real:rijeka-season"
        ]
    , contextRuleProvenance = ["VerbNet:say-37.7", "wimcor:real:rijeka-season"]
    }

rijekaSource, hnkRijeka, nkOrijent :: EntityId
rijekaSource = EntityId "Q1647"
hnkRijeka = EntityId "Q318969"
nkOrijent = EntityId "Q1447572"
